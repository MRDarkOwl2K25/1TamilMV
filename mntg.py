from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import OWNER


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
