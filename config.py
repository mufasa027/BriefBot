import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME", "briefbot.db")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

RSS_FEEDS = {
    "BBC": "https://feeds.bbci.co.uk/news/rss.xml",
    "Reuters": "https://feeds.reuters.com/reuters/topNews",
    "AP": "https://apnews.com/hub/ap-top-news/rss",
    "AlJazeera": "https://www.aljazeera.com/xml/rss/all.xml",
}