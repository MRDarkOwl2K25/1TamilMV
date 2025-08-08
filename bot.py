import asyncio
import logging
import threading
import io
import re
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask
from bs4 import BeautifulSoup
import cloudscraper

from pyrogram import Client, errors, utils as pyroutils, filters, enums
from config import Config
import start
from database import db

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
    # Match sizes like 1.2GB, 700 MB, 512KB but avoid bitrate tokens like 128kbps/mbps/gbps
    match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:GB|MB|KB))\b", text, re.IGNORECASE)
    return match.group(1) if match else "Unknown"

# Utility to clean title for display
def clean_title(raw_title):
    """Clean title by removing leading domain prefixes and trailing .torrent suffix"""
    title = (raw_title or "").strip()

    # Remove any leading domain pattern like:
    #   www.1tamilmv.blue - ...
    #   1tamilmv.se - ...
    #   www.tamilmv.boo - ...
    # Also tolerate http/https and various dash characters
    title = re.sub(
        r'^\s*(?:https?://)?(?:www\.)?(?:[a-z0-9-]+\.)+[a-z]{2,}\s*[-–—]\s*',
        '',
        title,
        flags=re.IGNORECASE,
    )

    # Remove a single trailing .torrent (case-insensitive) if present
    title = re.sub(r'\.torrent\s*$', '', title, flags=re.IGNORECASE)

    # Collapse duplicate spaces
    title = re.sub(r'\s{2,}', ' ', title).strip()

    return title

# Utility to normalize URLs by removing domain
def normalize_url(url):
    """Remove domain from URL to make it domain-independent"""
    try:
        parsed = urlparse(url)
        # Return path + query + fragment (everything except scheme and netloc)
        normalized = parsed.path
        if parsed.query:
            normalized += '?' + parsed.query
        if parsed.fragment:
            normalized += '#' + parsed.fragment
        return normalized
    except:
        # If parsing fails, return original URL
        return url

# Utility to normalize file URLs specifically for duplicate detection
def normalize_file_url(url):
    """Remove domain from URL to make it domain-independent"""
    try:
        parsed = urlparse(url)
        # Return path + query + fragment (everything except scheme and netloc)
        normalized = parsed.path
        if parsed.query:
            normalized += '?' + parsed.query
        if parsed.fragment:
            normalized += '#' + parsed.fragment
        return normalized
    except:
        # If parsing fails, return original URL
        return url

# Global variable to track broken URLs
broken_urls = set()

# Crawl 1TamilMV for torrent files, returning topic URL + its files
async def crawl_tbl(posted_files=None):
    # Get config from database
    config = await db.get_bot_config()
    base_url = config["base_url"] if config and "base_url" in config else None
    if not base_url:
        logging.error("Base URL not set in config!")
        return []
    topic_limit = config["topic_limit"] if config and "topic_limit" in config else 0
    
    # Use empty set if no posted_files provided
    if posted_files is None:
        posted_files = set()
    
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
        # dedupe and limit to configured number of topics
        for rel_url in list(dict.fromkeys(topic_links))[:topic_limit]:
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
                    
                    # Normalize file URL for domain-independent duplicate detection
                    normalized_link = normalize_file_url(link)
                    
                    # Log file URL patterns for debugging (only first few times)
                    if len(posted_files) < 5:  # Only log during initial startup
                        logging.info(f"File URL pattern: {link} -> {normalized_link}")
                    
                    # Check if this file is already posted using normalized URL
                    if normalized_link in posted_files:
                        # Skip already posted files
                        logging.info(f"Skipping duplicate: {raw_text} (normalized: {normalized_link})")
                        continue
                    
                    # Store raw title - will clean just before upload
                    title = raw_text
                    size = extract_size(raw_text)

                    file_links.append({
                        "type": "torrent",
                        "title": title,  # Raw title
                        "link": link,
                        "normalized_link": normalized_link,
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

    def __init__(self):
        super().__init__(
            "MN-Bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=8
        )
        self.channel_id = Config.CHANNEL_ID
        self.leech_chat_id = Config.CHAT_ID  # Optional secondary destination for /qbleech commands
        self.last_posted = set()   # tracks normalized file URLs (domain-independent)
        self.seen_topics = set()   # tracks which topic URLs have been processed
        self.thumbnail = None  # will store the thumbnail bytes
        self.config = None  # will store bot configuration
        self.stats = {"posts_successful": 0, "posts_failed": 0, "total_scraped": 0}

    async def safe_send_message(self, chat_id, text, **kwargs):
        # split overly-long messages
        for chunk in (text[i:i+self.MAX_MSG_LENGTH] for i in range(0, len(text), self.MAX_MSG_LENGTH)):
            await self.send_message(chat_id, chunk, **kwargs)
            await asyncio.sleep(1)

    async def prepare_thumbnail(self):
        """Download and prepare the thumbnail for file uploads"""
        try:
            # Get thumbnail URL from config
            if self.config:
                if "thumbnail_url" in self.config:
                    thumbnail_url = self.config["thumbnail_url"]
                else:
                    thumbnail_url = self.THUMBNAIL_URL
            else:
                thumbnail_url = self.THUMBNAIL_URL
                
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(thumbnail_url, timeout=10)
            resp.raise_for_status()
            self.thumbnail = io.BytesIO(resp.content)
            logging.info("Thumbnail downloaded successfully")
        except Exception as e:
            logging.error(f"Failed to download thumbnail: {e}")
            self.thumbnail = None

    async def load_config(self):
        """Load bot configuration from database"""
        try:
            self.config = await db.get_bot_config()
            if not self.config:
                logging.warning("No configuration found, using defaults")
        except Exception as e:
            logging.error(f"Failed to load config: {e}")

    async def get_caption_template(self):
        """Get caption template from config"""
        if self.config:
            if "caption_template" in self.config:
                return self.config["caption_template"]
            else:
                logging.error("Caption template not set in config!")
                return ""
        return "**{title}**\n\n**📦 {size}**\n\n**#1TamilMV | #TamilMV | #TMV**\n\n**🚀 Uploaded By ~ @E4Error**"

    async def format_caption(self, title, size):
        """Format caption using template, tolerating missing placeholders"""
        template = await self.get_caption_template()
        # Replace only known placeholders; leave any other braces intact
        try:
            caption = template.replace("{title}", title).replace("{size}", size)
        except Exception:
            # Fallback to a minimal caption if something goes wrong
            caption = f"{title}\n\n{size}"
        return caption

    async def auto_post_torrents(self):
        while True:
            try:
                torrents = await crawl_tbl(self.last_posted)
                for t in torrents:
                    topic = t["topic_url"]
                    # All files in torrents are already filtered to be new (not posted)
                    # if we've seen this topic and there are no new files, skip
                    if topic in self.seen_topics and not t["links"]:
                        continue

                    # send each new file
                    for file in t["links"]:
                        try:
                            scraper = cloudscraper.create_scraper()
                            resp = scraper.get(file["link"], timeout=10)
                            resp.raise_for_status()
                            file_bytes = io.BytesIO(resp.content)
                            
                            # Clean title just before upload
                            raw_title = file["title"]
                            cleaned_title = clean_title(raw_title)
                            
                            # Log title cleaning
                            if raw_title != cleaned_title:
                                logging.info(f"Title cleaned: '{raw_title}' -> '{cleaned_title}'")
                            
                            filename = cleaned_title.replace(" ", "_") + ".torrent"
                            
                            # Use caption template from config
                            caption = await self.format_caption(cleaned_title, file["size"])
                            
                            await self.send_document(
                                self.channel_id,
                                file_bytes,
                                file_name=filename,
                                caption=caption,
                                thumb=self.thumbnail
                            )
                            
                            # Also send the /qbleech command with the original link to secondary chat if configured
                            try:
                                if self.leech_chat_id:
                                    await self.send_message(self.leech_chat_id, f"/qbleech {file['link']}")
                            except Exception as leech_err:
                                logging.error(f"Failed to send /qbleech for {file['link']}: {leech_err}")
                            
                            # Save posted file to topics collection
                            await db.add_posted_file_to_topic(
                                t["topic_url"],
                                t.get("title", ""),
                                file["link"],
                                cleaned_title,  # Store cleaned title
                                file["size"],
                                file["normalized_link"]
                            )
                            self.last_posted.add(file["normalized_link"])
                            
                            # Update stats
                            self.stats["posts_successful"] += 1
                            
                            logging.info(f"Posted TBL: {cleaned_title}")
                            await asyncio.sleep(3)
                            
                        except Exception as e:
                            logging.error(f"Error sending TBL file {file['link']}: {e}")
                            
                            # Save failed post
                            await db.save_failed_post(
                                file["link"], 
                                file["title"],  # Raw title for failed posts
                                file["size"], 
                                str(e)
                            )
                            
                            # Update stats
                            self.stats["posts_failed"] += 1

                    # mark this topic as seen
                    self.seen_topics.add(topic)

                # Update daily stats
                await db.update_daily_stats(
                    posts_successful=self.stats["posts_successful"],
                    posts_failed=self.stats["posts_failed"],
                    total_scraped=len(torrents)
                )
                
                # Reset stats for next cycle
                self.stats = {"posts_successful": 0, "posts_failed": 0, "total_scraped": 0}

            except Exception as e:
                logging.error(f"Error in auto_post_torrents: {e}")

            # wait 1 minute before next check
            await asyncio.sleep(60)

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.bot_username = f"@{me.username}"
        
        # Connect to MongoDB
        await db.connect()
        
        from datetime import datetime
        import pytz

        msg_text = (
            "<b>⌬ Bot Started Successfully!</b>\n"
            f"<b>┟ Date:</b> {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d/%m/%y')}\n"
            f"<b>┠ Time:</b> {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%I:%M:%S %p')}\n"
            f"<b>┠ TimeZone:</b> Asia/Kolkata\n"
        )
        await self.send_message(
            Config.BOT_OWNER,
            text=msg_text,
            parse_mode=enums.ParseMode.HTML
        )
        logging.info("Bot started with MongoDB integration")
        
        # Load configuration
        await self.load_config()
        
        # Download thumbnail
        await self.prepare_thumbnail()
        
        # After connecting to MongoDB
        posted_files = set()
        seen_topics = set()
        # Load posted files from topics collection (only files that were actually posted)
        async for topic in db.db.topics.find({}, {"topic_url": 1, "files.file_link": 1, "files.normalized_link": 1}):
            seen_topics.add(topic["topic_url"])
            for f in topic.get("files", []):
                # Use normalized link if available, otherwise normalize the file_link
                if f.get("normalized_link"):
                    posted_files.add(f["normalized_link"])
                else:
                    # For backward compatibility, normalize old file_link
                    posted_files.add(normalize_file_url(f["file_link"]))
        self.last_posted = posted_files
        self.seen_topics = seen_topics
        
        # Cleanup old data
        # await db.cleanup_old_data()
        
        # Register command handlers using decorators
        @self.on_message(filters.command("start"))
        async def start_handler(client, message):
            await start.start_command(client, message)
            
        @self.on_message(filters.command("help"))
        async def help_handler(client, message):
            await start.help_command(client, message)
            
        @self.on_message(filters.command("settings") & filters.user(Config.BOT_OWNER))
        async def settings_handler(client, message):
            await start.settings_command(client, message)
            
        @self.on_message(filters.command("stats") & filters.user(Config.BOT_OWNER))
        async def stats_handler(client, message):
            await start.stats_command(client, message)
            
        @self.on_message(filters.command("retry_failed") & filters.user(Config.BOT_OWNER))
        async def retry_failed_handler(client, message):
            await start.retry_failed_command(client, message)
            
        @self.on_message(filters.command("restart") & filters.user(Config.BOT_OWNER))
        async def restart_handler(client, message):
            await start.restart_command(client, message)
            
        @self.on_message(filters.text & filters.user(Config.BOT_OWNER))
        async def text_handler(client, message):
            await start.handle_settings_input(client, message)
            
        @self.on_callback_query()
        async def callback_handler(client, callback_query):
            await start.callback_query_handler(client, callback_query)
        
        asyncio.create_task(self.auto_post_torrents())

    async def stop(self, *args):
        await super().stop()
        await db.close()
        logging.info("Bot stopped")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    MN_Bot().run()