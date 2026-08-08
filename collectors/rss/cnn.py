from collectors.rss.utils import extract_image_url
import feedparser
from settings import RSS_FEEDS


def fetch_cnn_news():
    """
    Fetch latest news from CNN RSS.
    """
    url = RSS_FEEDS.get("CNN", "http://rss.cnn.com/rss/edition.rss")
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries:
        articles.append({
            "title": getattr(entry, "title", "").strip(),
            "url": getattr(entry, "link", "").strip(),
            "published": getattr(entry, "published", getattr(entry, "updated", "")),
            "summary": getattr(entry, "summary", "").strip(),
            "image_url": extract_image_url(entry),
            "source": "CNN"
        })

    return articles
