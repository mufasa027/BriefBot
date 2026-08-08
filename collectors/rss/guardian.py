from collectors.rss.utils import extract_image_url
import feedparser
from settings import RSS_FEEDS


def fetch_guardian_news():
    """
    Fetch latest news from The Guardian RSS.
    """
    url = RSS_FEEDS.get("Guardian", "https://www.theguardian.com/international/rss")
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries:
        articles.append({
            "title": getattr(entry, "title", "").strip(),
            "url": getattr(entry, "link", "").strip(),
            "published": getattr(entry, "published", getattr(entry, "updated", "")),
            "summary": getattr(entry, "summary", "").strip(),
            "image_url": extract_image_url(entry),
            "source": "Guardian"
        })

    return articles
