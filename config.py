from dotenv import load_dotenv
from os import environ

load_dotenv()  # Load .env into environment


class Config:
    API_ID = int(environ.get("API_ID", "0"))
    API_HASH = environ.get("API_HASH", "")
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    BOT_SESSION = environ.get("BOT_SESSION", "Bot")
    DATABASE_URI = environ.get("DATABASE_URI", "mongodb://localhost:27017")
    DATABASE_NAME = environ.get("DATABASE_NAME", "tamilmv_bot")
    BOT_OWNER = int(environ.get("BOT_OWNER", "0"))
    CHANNEL_ID = int(environ.get("CHANNEL_ID", "0"))  # main channel/group to post documents
    CHAT_ID = int(environ.get("CHAT_ID", "0"))        # secondary chat for /qbleech commands
    TOPIC_LIMIT = int(environ.get("TOPIC_LIMIT", "0"))
