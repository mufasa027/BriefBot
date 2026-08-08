import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME", os.path.join("data", "briefbot.db"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Trusted News Sources RSS Feeds
RSS_FEEDS = {
    "BBC": "https://feeds.bbci.co.uk/news/rss.xml",
    "Reuters": "https://news.google.com/rss/search?q=site:reuters.com",
    "AP": "https://news.google.com/rss/search?q=site:apnews.com",
    "DW": "https://rss.dw.com/rdf/rss-en-all",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "CNN": "http://rss.cnn.com/rss/edition.rss",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "Guardian": "https://www.theguardian.com/international/rss",
}

POSTS_PER_DAY = 6