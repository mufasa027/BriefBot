from collectors.rss.utils import extract_image_url
import feedparser
from config import RSS_FEEDS


def fetch_npr_news():
    """
    Fetch latest news from NPR RSS.
    """
    url = RSS_FEEDS.get("NPR", "https://feeds.npr.org/1001/rss.xml")
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries:
        articles.append({
            "title": getattr(entry, "title", "").strip(),
            "url": getattr(entry, "link", "").strip(),
            "published": getattr(entry, "published", getattr(entry, "updated", "")),
            "summary": getattr(entry, "summary", "").strip(),
            "image_url": extract_image_url(entry),
            "source": "NPR"
        })

    return articles
