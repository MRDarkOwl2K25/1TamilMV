from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import FloodWait
import asyncio
import logging
import pytz
from datetime import datetime
from config import OWNER
from database import db

# State management for settings
user_states = {}

class TEXT:
    START = """
<b>Hi {}, I'm TamilMV RSS Bot! 🤖</b>

<b>Features:</b>
• Auto-posts new torrents every 1 minute
• Real-time scraping from 1TamilMV
• MongoDB database integration
• Dynamic configuration management

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


# Global bot instance (will be set by bot.py)
bot_instance = None

def set_bot_instance(bot):
    """Set the bot instance for command handlers"""
    global bot_instance
    bot_instance = bot


async def start_command(client: Client, msg: Message):
    await msg.reply_text(
        TEXT.START.format(msg.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=INLINE.START_BTN,
    )


async def help_command(client: Client, msg: Message):
    help_text = """
🤖 <b>TamilMV RSS Bot Commands:</b>

<b>General Commands:</b>
• /start - Start the bot and see main menu
• /help - Show this help message

<b>Admin Commands:</b>
• /settings - Bot configuration management
• /statistics - View bot performance statistics
• /retry_failed - Manage failed posts
• /restart - Restart the bot

📋 <b>Features:</b>
• Auto-posts new torrents to channel every 1 minute
• Real-time scraping from 1TamilMV
• MongoDB database integration
• Dynamic configuration management

🔄 <b>Bot Status:</b> Running with 1-minute check intervals
"""
    await msg.reply_text(help_text, parse_mode="html")


# Admin Commands
async def settings_command(client: Client, message: Message):
    """Handle /settings command"""
    if message.from_user.id != OWNER.ID:
        return
        
    config = await db.get_bot_config()
    if not config:
        await message.reply_text("❌ Failed to load configuration")
        return
        
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Edit Base URL", callback_data="edit_base_url")],
        [InlineKeyboardButton("🖼️ Change Thumbnail", callback_data="edit_thumbnail")],
        [InlineKeyboardButton("📋 Edit Caption", callback_data="edit_caption")],
        [InlineKeyboardButton("⚙️ Set Topic Limit", callback_data="edit_topic_limit")],
        [InlineKeyboardButton("❌ Close", callback_data="close_settings")]
    ])
    
    text = f"""🔧 **Bot Settings Panel**

**Current Configuration:**
• Base URL: `{config.get('base_url', 'Not set')}`
• Thumbnail: {'✅ Set' if config.get('thumbnail_url') else '❌ Not set'}
• Topic Limit: `{config.get('topic_limit', 0)}`
• Caption Template: {'✅ Set' if config.get('caption_template') else '❌ Not set'}

Select an option to modify:"""
    
    await message.reply_text(text, reply_markup=keyboard)


async def statistics_command(client: Client, message: Message):
    """Handle /statistics command"""
    if message.from_user.id != OWNER.ID:
        return
        
    try:
        # Get today's stats
        today_stats = await db.get_daily_stats()
        weekly_stats = await db.get_weekly_stats()
        
        # Calculate weekly totals
        weekly_total = sum(stat.get('posts_successful', 0) for stat in weekly_stats)
        weekly_failed = sum(stat.get('posts_failed', 0) for stat in weekly_stats)
        weekly_avg = weekly_total / 7 if weekly_stats else 0
        
        # Get best day
        best_day = max(weekly_stats, key=lambda x: x.get('posts_successful', 0)) if weekly_stats else None
        
        # Calculate success rate
        if today_stats:
            successful = today_stats.get('posts_successful', 0)
            failed = today_stats.get('posts_failed', 0)
            total = successful + failed
            success_rate = round((successful / max(total, 1)) * 100, 1) if total > 0 else 0
        else:
            success_rate = 0
            
        # Get config for display
        config = await db.get_bot_config()
            
        text = f"""📊 **Bot Statistics**

**Today's Performance:**
• Posts Successful: `{today_stats.get('posts_successful', 0) if today_stats else 0}`
• Posts Failed: `{today_stats.get('posts_failed', 0) if today_stats else 0}`
• Success Rate: `{success_rate}%`

**This Week:**
• Total Posts: `{weekly_total}`
• Average Daily: `{round(weekly_avg, 1)}`
• Best Day: `{best_day.get('posts_successful', 0) if best_day else 0} posts`

**Configuration:**
• Base URL: `{config.get('base_url', 'Not set') if config else 'Not loaded'}`
• Last Updated: `{config.get('last_updated', 'Unknown') if config else 'Unknown'}`
• Bot Status: ✅ Running"""
        
        await message.reply_text(text)
        
    except Exception as e:
        logging.error(f"Failed to get statistics: {e}")
        await message.reply_text("❌ Failed to load statistics")


async def retry_failed_command(client: Client, message: Message):
    """Handle /retry_failed command"""
    if message.from_user.id != OWNER.ID:
        return
        
    try:
        failed = await db.get_failed_posts()
        
        if not failed:
            await message.reply_text("✅ No failed posts to retry!")
            return
            
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Retry All Failed", callback_data="retry_all_failed")],
            [InlineKeyboardButton("🗑️ Clear All Failed", callback_data="clear_all_failed")],
            [InlineKeyboardButton("❌ Close", callback_data="close_retry")]
        ])
        
        text = f"""⚠️ **Failed Posts Management**

**Failed Posts Count:** `{len(failed)}`

Select an action:"""
        
        await message.reply_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Failed to get failed posts: {e}")
        await message.reply_text("❌ Failed to load failed posts")


async def restart_command(client: Client, message: Message):
    """Handle /restart command"""
    if message.from_user.id != OWNER.ID:
        return
        
    buttons = [
        [
            InlineKeyboardButton("Yes!", callback_data="confirm_restart_yes"),
            InlineKeyboardButton("No!", callback_data="confirm_restart_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        "Are you really sure you want to restart the bot?",
        reply_markup=reply_markup
    )


async def handle_settings_input(client: Client, message: Message):
    """Handle settings input from user"""
    if message.from_user.id != OWNER.ID:
        return
        
    user_id = message.from_user.id
    if user_id not in user_states:
        return
        
    state = user_states[user_id]
    text = message.text.strip()
    
    if text.lower() == "/cancel":
        del user_states[user_id]
        await message.reply_text("❌ Settings update cancelled")
        return
        
    try:
        if state == "waiting_base_url":
            # Validate URL
            if not text.startswith(("http://", "https://")):
                await message.reply_text("❌ Invalid URL! URL must start with http:// or https://")
                return
                
            success = await db.update_bot_config("base_url", text, user_id)
            if success:
                await message.reply_text(f"✅ Base URL updated successfully!\nNew URL: `{text}`")
            else:
                await message.reply_text("❌ Failed to update base URL")
                
        elif state == "waiting_thumbnail":
            # Validate URL
            if not text.startswith(("http://", "https://")):
                await message.reply_text("❌ Invalid URL! URL must start with http:// or https://")
                return
                
            success = await db.update_bot_config("thumbnail_url", text, user_id)
            if success:
                await message.reply_text(f"✅ Thumbnail URL updated successfully!\nNew URL: `{text}`")
            else:
                await message.reply_text("❌ Failed to update thumbnail URL")
                
        elif state == "waiting_caption":
            # Validate caption template
            if "{title}" not in text or "{size}" not in text:
                await message.reply_text("❌ Invalid caption template! Must include {title} and {size} variables")
                return
                
            success = await db.update_bot_config("caption_template", text, user_id)
            if success:
                await message.reply_text(f"✅ Caption template updated successfully!\nNew template:\n`{text}`")
            else:
                await message.reply_text("❌ Failed to update caption template")
                
        elif state == "waiting_topic_limit":
            try:
                limit = int(text)
                if limit < 0:
                    await message.reply_text("❌ Topic limit cannot be negative! Please enter 0 or a positive number.")
                    return
                    
                success = await db.update_bot_config("topic_limit", limit, user_id)
                if success:
                    if limit == 0:
                        await message.reply_text(f"✅ Topic limit updated successfully!\nNew limit: `{limit}` (Skip indexing)")
                    else:
                        await message.reply_text(f"✅ Topic limit updated successfully!\nNew limit: `{limit}`")
                else:
                    await message.reply_text("❌ Failed to update topic limit")
                    
            except ValueError:
                await message.reply_text("❌ Invalid number! Please enter 0 or a positive number.")
                return
                
        del user_states[user_id]
        
    except Exception as e:
        logging.error(f"Error handling settings input: {e}")
        await message.reply_text("❌ An error occurred while updating settings")


async def callback_query_handler(client: Client, callback_query: CallbackQuery):
    """Handle callback queries for settings"""
    if callback_query.from_user.id != OWNER.ID:
        await callback_query.answer("❌ You are not authorized to use this bot!")
        return
        
    data = callback_query.data
    
    if data == "close_settings":
        await callback_query.message.delete()
        await callback_query.answer("Settings closed")
        
    elif data == "close_retry":
        await callback_query.message.delete()
        await callback_query.answer("Retry panel closed")
        
    elif data == "edit_base_url":
        user_states[callback_query.from_user.id] = "waiting_base_url"
        config = await db.get_bot_config()
        current_url = config.get('base_url', 'Not set') if config else 'Not set'
        await callback_query.message.edit_text(
            "Send the new base URL (or /cancel to abort):\n\n"
            f"Current: `{current_url}`\n\n"
            "Example: `https://www.1tamilmv.com`"
        )
        
    elif data == "edit_thumbnail":
        user_states[callback_query.from_user.id] = "waiting_thumbnail"
        config = await db.get_bot_config()
        current_thumb = config.get('thumbnail_url', 'Not set') if config else 'Not set'
        await callback_query.message.edit_text(
            "Send the new thumbnail URL (or /cancel to abort):\n\n"
            f"Current: `{current_thumb}`\n\n"
            "Example: `https://example.com/image.jpg`"
        )
        
    elif data == "edit_caption":
        user_states[callback_query.from_user.id] = "waiting_caption"
        config = await db.get_bot_config()
        current_caption = config.get('caption_template', 'Not set') if config else 'Not set'
        await callback_query.message.edit_text(
            f"Send the new caption template (or /cancel to abort):\n\n"
            f"Current:\n`{current_caption}`\n\n"
            "Available variables: `{title}`, `{size}`\n\n"
            "Example:\n`**🎬 {title}**\n\n**📦 {size}**\n\n**🔥 Uploaded By ~ @E4Error**`"
        )
        
    elif data == "edit_topic_limit":
        user_states[callback_query.from_user.id] = "waiting_topic_limit"
        config = await db.get_bot_config()
        current_limit = config.get('topic_limit', 0) if config else 0
        await callback_query.message.edit_text(
            f"Send the new topic limit (0 to skip indexing, or any positive number) or /cancel to abort:\n\n"
            f"Current: `{current_limit}`"
        )
        
    elif data == "retry_all_failed":
        failed = await db.get_failed_posts()
        if failed:
            await callback_query.message.edit_text("🔄 Retrying all failed posts...")
            # Implement retry logic here
            await callback_query.answer("Retry started")
        else:
            await callback_query.answer("No failed posts to retry")
            
    elif data == "clear_all_failed":
        await db.clear_failed_posts()
        await callback_query.message.edit_text("✅ All failed posts cleared!")
        await callback_query.answer("Failed posts cleared")
        
    elif data.startswith("confirm_restart_"):
        action = data.split("_")[-1]
        if action == "yes":
            # Restart the bot
            import os
            import sys
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await callback_query.message.edit_text("❌ Restart cancelled.")
            await callback_query.answer("Restart cancelled") 