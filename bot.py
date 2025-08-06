import asyncio
import logging
import threading
import io
import re

from flask import Flask
from bs4 import BeautifulSoup
import cloudscraper

from pyrogram import Client, errors, utils as pyroutils
from config import BOT, API, OWNER, CHANNEL
import start

# Ensure proper chat/channel ID handling
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -10099999999999

# Logging configuration
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# Flask health check
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Run Flask in a separate thread
def run_flask():
    app.run(host='0.0.0.0', port=8000)

# Utility to extract size from text
def extract_size(text):
    match = re.search(r"(\d+(?:\.\d+)?\s*(?:GB|MB|KB))", text, re.IGNORECASE)
    return match.group(1) if match else "Unknown"

# Global variable to track broken URLs
broken_urls = set()

# Crawl 1TamilMV for torrent files, returning topic URL + its files
def crawl_tbl():
    base_url = "https://www.yts.mx"
    torrents = []
    scraper = cloudscraper.create_scraper()

    try:
        resp = scraper.get(base_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        topic_links = [
            a["href"] for a in soup.find_all("a", href=re.compile(r'/forums/topic/'))
            if a.get("href")
        ]
        
        # If no topic links found, try alternative patterns
        if not topic_links:
            topic_links = [
                a["href"] for a in soup.find_all("a", href=re.compile(r'/topic/'))
                if a.get("href")
            ]
        # dedupe and limit to first 15 topics
        for rel_url in list(dict.fromkeys(topic_links))[:15]:
            try:
                full_url = rel_url if rel_url.startswith("http") else base_url + rel_url
                
                # Skip if this URL is known to be broken
                if full_url in broken_urls:
                    continue
                dresp = scraper.get(full_url, timeout=10)
                
                # Check if the page exists (not 404)
                if dresp.status_code == 404:
                    logging.info(f"Skipping 404 topic: {full_url}")
                    broken_urls.add(full_url)  # Remember this broken URL
                    continue
                    
                dresp.raise_for_status()
                post_soup = BeautifulSoup(dresp.text, "html.parser")

                torrent_tags = post_soup.find_all("a", attrs={"data-fileext": "torrent"})
                file_links = []
                for tag in torrent_tags:
                    href = tag.get("href")
                    if not href:
                        continue
                    link = href.strip()
                    raw_text = tag.get_text(strip=True)
                    # Clean title by removing domain prefixes - more comprehensive cleaning
                    title = raw_text
                    
                    # Use regex to remove any domain pattern
                    # Remove any domain pattern like "www.1tamilmv.com - " or "1tamilmv.com - "
                    title = re.sub(r'www\.1tamilmv\.[a-z]+ - ', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'1tamilmv\.[a-z]+ - ', '', title, flags=re.IGNORECASE)
                    
                    # Remove .torrent extension and clean up
                    title = title.rstrip(".torrent").strip()
                    
                    # Debug: Log the original and cleaned title
                    if raw_text != title:
                        logging.info(f"Title cleaned: '{raw_text}' -> '{title}'")
                    
                    size = extract_size(raw_text)

                    file_links.append({
                        "type": "torrent",
                        "title": title,
                        "link": link,
                        "size": size
                    })

                if file_links:
                    torrents.append({
                        "topic_url": full_url,
                        "title": file_links[0]["title"],
                        "size": file_links[0]["size"],
                        "links": file_links
                    })

            except Exception as post_err:
                logging.error(f"Failed to parse TBL topic {rel_url}: {post_err}")
                continue  # Continue to next topic instead of stopping

    except Exception as e:
        logging.error(f"Failed to fetch TBL homepage: {e}")

    return torrents

class MN_Bot(Client):
    MAX_MSG_LENGTH = 4000
    THUMBNAIL_URL = "https://pbs.twimg.com/profile_images/1672203006232924161/B6aInkS9_400x400.jpg"

    def __init__(self):
        super().__init__(
            "MN-Bot",
            api_id=API.ID,
            api_hash=API.HASH,
            bot_token=BOT.TOKEN,
            workers=8
        )
        self.channel_id = CHANNEL.ID
        self.last_posted = set()   # tracks individual file links
        self.seen_topics = set()   # tracks which topic URLs have been processed
        self.thumbnail = None  # will store the thumbnail bytes

    async def safe_send_message(self, chat_id, text, **kwargs):
        # split overly-long messages
        for chunk in (text[i:i+self.MAX_MSG_LENGTH] for i in range(0, len(text), self.MAX_MSG_LENGTH)):
            await self.send_message(chat_id, chunk, **kwargs)
            await asyncio.sleep(1)

    async def prepare_thumbnail(self):
        """Download and prepare the thumbnail for file uploads"""
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(self.THUMBNAIL_URL, timeout=10)
            resp.raise_for_status()
            self.thumbnail = io.BytesIO(resp.content)
            logging.info("Thumbnail downloaded successfully")
        except Exception as e:
            logging.error(f"Failed to download thumbnail: {e}")
            self.thumbnail = None

    async def auto_post_torrents(self):
        while True:
            try:
                torrents = crawl_tbl()
                for t in torrents:
                    topic = t["topic_url"]
                    # find brand‑new files in this topic
                    new_files = [f for f in t["links"] if f["link"] not in self.last_posted]
                    # if we've seen this topic and there are no new files, skip
                    if topic in self.seen_topics and not new_files:
                        continue

                    # send each new file
                    for file in new_files:
                        try:
                            scraper = cloudscraper.create_scraper()
                            resp = scraper.get(file["link"], timeout=10)
                            resp.raise_for_status()
                            file_bytes = io.BytesIO(resp.content)
                            filename = file["title"].replace(" ", "_") + ".torrent"
                            caption = (
                                f"**{file['title']}**\n"
                                f"**📦 {file['size']}**\n"
                                f"**#1TamilMV | #TamilMV | #TMV**"
                            )
                            await self.send_document(
                                self.channel_id,
                                file_bytes,
                                file_name=filename,
                                caption=caption,
                                thumb=self.thumbnail
                            )
                            self.last_posted.add(file["link"])
                            logging.info(f"Posted TBL: {file['title']}")
                            await asyncio.sleep(3)
                        except Exception as e:
                            logging.error(f"Error sending TBL file {file['link']}: {e}")

                    # mark this topic as seen
                    self.seen_topics.add(topic)

            except Exception as e:
                logging.error(f"Error in auto_post_torrents: {e}")

            # wait 1 minute before next check
            await asyncio.sleep(60)

    async def start(self):
        await super().start()
        me = await self.get_me()
        BOT.USERNAME = f"@{me.username}"
        
        # Download thumbnail
        await self.prepare_thumbnail()
        
        await self.send_message(
            OWNER.ID,
            text=f"{me.first_name} ✅ BOT started with only TMVsupport (1‑min checks)"
        )
        logging.info("Bot started with only TMV support")
        asyncio.create_task(self.auto_post_torrents())

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot stopped")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    MN_Bot().run()
