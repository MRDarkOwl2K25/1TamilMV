import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE

IST = pytz.timezone('Asia/Kolkata')

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(DATABASE.URI)
            self.db = self.client[DATABASE.NAME]
            # Test connection
            await self.client.admin.command('ping')
            logging.info("✅ Connected to MongoDB successfully")
            
            # Initialize default config if not exists
            await self.initialize_default_config()
            
        except Exception as e:
            logging.error(f"❌ Failed to connect to MongoDB: {e}")
            raise e
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logging.info("MongoDB connection closed")
    
    async def initialize_default_config(self):
        """Initialize default bot configuration"""
        default_config = {
            "_id": "bot_config",
            "base_url": "https://www.1tamilmv.blue",
            "thumbnail_url": "https://pbs.twimg.com/profile_images/1672203006232924161/B6aInkS9_400x400.jpg",
            "caption_template": "**{title}**\n\n**📦 {size}**\n\n**#1TamilMV | #TamilMV | #TMV**\n\n**🚀 Uploaded By ~ @E4Error**",
            "topic_limit": 0,
            "last_updated": datetime.now(IST),
            "updated_by": None
        }
        
        try:
            await self.db.config.update_one(
                {"_id": "bot_config"},
                {"$setOnInsert": default_config},
                upsert=True
            )
            logging.info("Default configuration initialized")
        except Exception as e:
            logging.error(f"Failed to initialize default config: {e}")
    
    # Configuration Management
    async def get_bot_config(self):
        """Get bot configuration"""
        try:
            config = await self.db.config.find_one({"_id": "bot_config"})
            return config
        except Exception as e:
            logging.error(f"Failed to get bot config: {e}")
            return None
    
    async def update_bot_config(self, field, value, user_id=None):
        """Update specific configuration field"""
        try:
            update_data = {
                field: value,
                "last_updated": datetime.now(IST)
            }
            if user_id:
                update_data["updated_by"] = user_id
                
            await self.db.config.update_one(
                {"_id": "bot_config"},
                {"$set": update_data}
            )
            logging.info(f"Updated {field} to {value}")
            return True
        except Exception as e:
            logging.error(f"Failed to update config {field}: {e}")
            return False
    
    # Removed old posted torrents logic: save_last_posted, get_last_posted, and related code.
    # Only topic-centric logic remains.

    async def save_posted_file(self, file_link, title, size):
        """Save every posted file (not just the last one)"""
        try:
            await self.db.posted.insert_one({
                "file_link": file_link,
                "title": title,
                "size": size,
                "posted_at": datetime.now(IST)
            })
            logging.info(f"Saved posted file: {title}")
        except Exception as e:
            logging.error(f"Failed to save posted file: {e}")
    
    # Failed Posts Management
    async def save_failed_post(self, file_link, title, size, error_message):
        """Save failed post for retry"""
        try:
            await self.db.failed.insert_one({
                "file_link": file_link,
                "title": title,
                "size": size,
                "error_message": error_message,
                "failed_at": datetime.now(IST),
                "retry_count": 0
            })
            logging.info(f"Saved failed post: {title}")
        except Exception as e:
            logging.error(f"Failed to save failed post: {e}")
    
    async def get_failed_posts(self):
        """Get all failed posts"""
        try:
            cursor = self.db.failed.find({})
            return await cursor.to_list(length=None)
        except Exception as e:
            logging.error(f"Failed to get failed posts: {e}")
            return []
    
    async def remove_failed_post(self, file_link):
        """Remove failed post after successful retry"""
        try:
            await self.db.failed.delete_one({"file_link": file_link})
        except Exception as e:
            logging.error(f"Failed to remove failed post: {e}")
    
    async def clear_failed_posts(self):
        """Clear all failed posts"""
        try:
            await self.db.failed.delete_many({})
            logging.info("Cleared all failed posts")
        except Exception as e:
            logging.error(f"Failed to clear failed posts: {e}")
    
    # Statistics Management
    async def update_daily_stats(self, posts_successful=0, posts_failed=0, total_scraped=0):
        """Update daily statistics"""
        try:
            today = datetime.now(IST).strftime("%Y-%m-%d")
            
            await self.db.bot_stats.update_one(
                {"_id": today},
                {
                    "$inc": {
                        "posts_successful": posts_successful,
                        "posts_failed": posts_failed,
                        "total_scraped": total_scraped
                    },
                    "$set": {
                        "date": today,
                        "last_updated": datetime.now(IST)
                    }
                },
                upsert=True
            )
        except Exception as e:
            logging.error(f"Failed to update daily stats: {e}")
    
    async def get_daily_stats(self, date=None):
        """Get statistics for a specific date"""
        try:
            if not date:
                date = datetime.now(IST).strftime("%Y-%m-%d")
            
            stats = await self.db.bot_stats.find_one({"_id": date})
            return stats
        except Exception as e:
            logging.error(f"Failed to get daily stats: {e}")
            return None
    
    async def get_weekly_stats(self):
        """Get weekly statistics"""
        try:
            week_ago = datetime.now(IST) - timedelta(days=7)
            cursor = self.db.bot_stats.find({
                "date": {"$gte": week_ago.strftime("%Y-%m-%d")}
            })
            
            weekly_stats = await cursor.to_list(length=None)
            return weekly_stats
        except Exception as e:
            logging.error(f"Failed to get weekly stats: {e}")
            return []
    
    async def cleanup_old_data(self):
        """Clean up old data on bot restart"""
        try:
            # Clear old failed posts (older than 1 day)
            yesterday = datetime.now(IST) - timedelta(days=1)
            await self.db.failed.delete_many({
                "failed_at": {"$lt": yesterday}
            })
            
            # Clear old stats (older than 30 days)
            thirty_days_ago = datetime.now(IST) - timedelta(days=30)
            await self.db.bot_stats.delete_many({
                "date": {"$lt": thirty_days_ago.strftime("%Y-%m-%d")}
            })
            
            logging.info("Cleaned up old data")
        except Exception as e:
            logging.error(f"Failed to cleanup old data: {e}")
    
    async def save_topic_with_files(self, topic_url, topic_title, files):
        """Upsert a topic document with its files as an array"""
        from datetime import datetime
        try:
            file_dicts = []
            for f in files:
                file_link = f.get("file_link") or f.get("link")
                file_dict = {
                    "file_link": file_link,
                    "file_title": f.get("file_title") or f.get("title", ""),
                    "size": f.get("size", "Unknown"),
                    "posted_at": f.get("posted_at", datetime.now(IST))
                }
                file_dicts.append(file_dict)
            await self.db.topics.update_one(
                {"topic_url": topic_url},
                {
                    "$set": {"title": topic_title, "last_updated": datetime.now(IST)},
                    "$addToSet": {"files": {"$each": file_dicts}}
                },
                upsert=True
            )
            logging.info(f"Saved/updated topic: {topic_title} ({topic_url}) with {len(file_dicts)} files")
        except Exception as e:
            logging.error(f"Failed to save topic with files: {e}")


# Global database instance
db = Database() 