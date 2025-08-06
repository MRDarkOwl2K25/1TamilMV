from pyrogram import Client as MN_Bot
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from mntg import TEXT, INLINE
import asyncio


@MN_Bot.on_message(filters.command("start"))
async def start(client: MN_Bot, msg: Message):
    await msg.reply_text(
        TEXT.START.format(msg.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=INLINE.START_BTN,
    )


@MN_Bot.on_message(filters.command("help"))
async def help_command(client: MN_Bot, msg: Message):
    help_text = """
🤖 **TamilMV RSS Bot Commands:**

**/start** - Start the bot and see main menu
**/view** - View the last 5 entries from 1TamilMV
**/help** - Show this help message

📋 **Features:**
• Auto-posts new torrents to channel every 1 minute
• Manual viewing of recent entries
• Real-time scraping from 1TamilMV.blue

🔄 **Bot Status:** Running with 1-minute check intervals
"""
    await msg.reply_text(help_text, parse_mode="Markdown")

