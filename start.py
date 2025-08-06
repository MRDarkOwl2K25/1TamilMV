from pyrogram import Client as MN_Bot
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait
import asyncio


class TEXT:
    START = """
<b>Hi {}, I'm TamilMV RSS Bot! 🤖</b>

<b>Commands:</b>
• /start - Show this menu
• /help - Show help message

<b>Features:</b>
• Auto-posts new torrents every 1 minute
• Real-time scraping from 1TamilMV.blue

[ <i> Made With Love By @E4Error </i> ]
"""
    DEVELOPER = "Developer 💀"
    UPDATES_CHANNEL = "Updates Channel ❣️"
    SOURCE_CODE = "🔗 Source Code"


class INLINE:
    START_BTN = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(TEXT.DEVELOPER, url="https://t.me/E4Error"),
            ],
            [
                InlineKeyboardButton(
                    TEXT.UPDATES_CHANNEL, url="https://t.me/E4Error"
                ),
            ],
            [
                InlineKeyboardButton(
                    TEXT.SOURCE_CODE,
                    url="https://t.me/E4Error",
                ),
            ],
        ]
    )


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
**/help** - Show this help message

📋 **Features:**
• Auto-posts new torrents to channel every 1 minute
• Real-time scraping from 1TamilMV.blue

🔄 **Bot Status:** Running with 1-minute check intervals
"""
    await msg.reply_text(help_text, parse_mode="Markdown") 