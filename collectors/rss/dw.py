from collectors.rss.utils import extract_image_url
import feedparser
from config import RSS_FEEDS


def fetch_dw_news():
    """
    Fetch latest news from DW (Deutsche Welle) RSS.
    """
    url = RSS_FEEDS.get("DW", "https://rss.dw.com/rdf/rss-en-all")
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries:
        articles.append({
            "title": getattr(entry, "title", "").strip(),
            "url": getattr(entry, "link", "").strip(),
            "published": getattr(entry, "published", getattr(entry, "updated", "")),
            "summary": getattr(entry, "summary", "").strip(),
            "image_url": extract_image_url(entry),
            "source": "DW"
        })

    return articles
