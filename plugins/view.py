from pyrogram import Client as MN_Bot
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
import asyncio
import io
from bs4 import BeautifulSoup
import cloudscraper
import re

# Utility to extract size from text
def extract_size(text):
    match = re.search(r"(\d+(?:\.\d+)?\s*(?:GB|MB|KB))", text, re.IGNORECASE)
    return match.group(1) if match else "Unknown"

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
        # dedupe and limit to first 15 topics
        for rel_url in list(dict.fromkeys(topic_links))[:15]:
            try:
                full_url = rel_url if rel_url.startswith("http") else base_url + rel_url
                dresp = scraper.get(full_url, timeout=10)
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
                    title = raw_text.replace("www.1TamilMV.blue - ", "")\
                                    .rstrip(".torrent").strip()
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
                print(f"Failed to parse TBL topic {rel_url}: {post_err}")

    except Exception as e:
        print(f"Failed to fetch TBL homepage: {e}")

    return torrents

@MN_Bot.on_message(filters.command("view"))
async def view_command(client: MN_Bot, msg: Message):
    try:
        # Send a processing message
        processing_msg = await msg.reply_text("🔄 Fetching latest entries...")
        
        # Get the latest torrents
        torrents = crawl_tbl()
        
        if not torrents:
            await processing_msg.edit_text("❌ No torrents found or error occurred while fetching.")
            return
        
        # Take only the last 5 entries
        recent_torrents = torrents[:5]
        
        # Create the message content in the same format as channel posts
        message_text = "📋 **Last 5 Entries from 1TamilMV:**\n\n"
        
        for i, torrent in enumerate(recent_torrents, 1):
            title = torrent["title"]
            size = torrent["size"]
            
            # Use the exact same format as channel posts
            message_text += f"**{i}.** {title}\n"
            message_text += f"📦 {size}\n"
            message_text += f"#tbl torrent file\n\n"
        
        # Add footer
        message_text += "---\n"
        message_text += "🔄 *Bot checks every 1 minute for new content*"
        
        # Update the processing message with the results
        await processing_msg.edit_text(
            message_text,
            disable_web_page_preview=True,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await msg.reply_text(f"❌ Error occurred: {str(e)}") 