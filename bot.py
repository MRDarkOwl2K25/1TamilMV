import asyncio
import logging
import threading
import io
import re
import os
import json
import pickle

from flask import Flask
from bs4 import BeautifulSoup
import cloudscraper

from pyrogram import Client, errors, utils as pyroutils
from config import BOT, API, OWNER, CHANNEL

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

# Data persistence functions
def save_bot_data(last_posted, seen_topics, broken_urls):
    """Save bot tracking data to file"""
    try:
        data = {
            'last_posted': list(last_posted),
            'seen_topics': list(seen_topics),
            'broken_urls': list(broken_urls)
        }
        with open('bot_data.pkl', 'wb') as f:
            pickle.dump(data, f)
        logging.info("Bot data saved successfully")
    except Exception as e:
        logging.error(f"Failed to save bot data: {e}")

def load_bot_data():
    """Load bot tracking data from file"""
    try:
        if os.path.exists('bot_data.pkl'):
            with open('bot_data.pkl', 'rb') as f:
                data = pickle.load(f)
            return set(data.get('last_posted', [])), set(data.get('seen_topics', [])), set(data.get('broken_urls', []))
        else:
            return set(), set(), set()
    except Exception as e:
        logging.error(f"Failed to load bot data: {e}")
        return set(), set(), set()

# Clean up only corrupted session files, not all session files
def cleanup_corrupted_sessions():
    """Clean up only corrupted session files, preserve working ones"""
    session_files = ["MN-Bot.session-journal", "MN-Bot.session.lock"]
    cleaned = []
    
    for file in session_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                cleaned.append(file)
                logging.info(f"Cleaned up corrupted session file: {file}")
            except Exception as e:
                logging.warning(f"Could not remove session file {file}: {e}")
    
    # Only remove main session file if it's corrupted (very small or empty)
    main_session = "MN-Bot.session"
    if os.path.exists(main_session):
        try:
            size = os.path.getsize(main_session)
            if size < 100:  # Very small session file is likely corrupted
                os.remove(main_session)
                cleaned.append(main_session)
                logging.info(f"Removed corrupted main session file (size: {size} bytes)")
            else:
                logging.info(f"Keeping main session file (size: {size} bytes)")
        except Exception as e:
            logging.warning(f"Could not check session file {main_session}: {e}")
    
    return cleaned

# Crawl 1TamilMV for torrent files, returning topic URL + its files
def crawl_tbl():
    base_url = "https://www.1tamilmv.blue"
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
        for rel_url in list(dict.fromkeys(topic_links))[:100]:
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
            plugins=dict(root="plugins"),
            workers=8
        )
        self.channel_id = CHANNEL.ID
        
        # Load persistent data
        self.last_posted, self.seen_topics, self.broken_urls = load_bot_data()
        logging.info(f"Loaded {len(self.last_posted)} posted files, {len(self.seen_topics)} seen topics, {len(self.broken_urls)} broken URLs")
        
        self.thumbnail = None  # will store the thumbnail bytes
        self.is_running = False

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

    async def safe_send_document(self, chat_id, document, **kwargs):
        """Safely send document with proper error handling"""
        try:
            if not self.is_running:
                logging.warning("Client not running, skipping document send")
                return False
                
            await self.send_document(chat_id, document, **kwargs)
            return True
        except errors.SessionClosed:
            logging.error("Session closed, attempting to restart...")
            await self.restart()
            return False
        except Exception as e:
            logging.error(f"Error sending document: {e}")
            return False

    async def auto_post_torrents(self):
        while self.is_running:
            try:
                torrents = crawl_tbl()
                for t in torrents:
                    if not self.is_running:
                        break
                        
                    topic = t["topic_url"]
                    # find brand‑new files in this topic
                    new_files = [f for f in t["links"] if f["link"] not in self.last_posted]
                    # if we've seen this topic and there are no new files, skip
                    if topic in self.seen_topics and not new_files:
                        continue

                    # send each new file
                    for file in new_files:
                        if not self.is_running:
                            break
                            
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
                            
                            success = await self.safe_send_document(
                                self.channel_id,
                                file_bytes,
                                file_name=filename,
                                caption=caption,
                                thumb=self.thumbnail
                            )
                            
                            if success:
                                self.last_posted.add(file["link"])
                                logging.info(f"Posted TBL: {file['title']}")
                            else:
                                logging.warning(f"Failed to post TBL: {file['title']}")
                                
                            await asyncio.sleep(3)
                        except Exception as e:
                            logging.error(f"Error sending TBL file {file['link']}: {e}")

                    # mark this topic as seen
                    self.seen_topics.add(topic)

                # Save data periodically (every 10 minutes or after processing)
                save_bot_data(self.last_posted, self.seen_topics, self.broken_urls)

            except Exception as e:
                logging.error(f"Error in auto_post_torrents: {e}")

            # wait 1 minute before next check
            await asyncio.sleep(60)

    async def start(self):
        # Clean up only corrupted sessions before starting
        cleanup_corrupted_sessions()
        
        await super().start()
        self.is_running = True
        
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
        self.is_running = False
        
        # Save data before stopping
        save_bot_data(self.last_posted, self.seen_topics, self.broken_urls)
        logging.info("Bot data saved before stopping")
        
        await super().stop()
        logging.info("Bot stopped")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    MN_Bot().run()
