from collectors.rss.utils import extract_image_url
import feedparser

from settings import RSS_FEEDS


def fetch_bbc_news():
    """
    Fetch the latest news from BBC RSS.
    Returns a list of article dictionaries.
    """

    feed = feedparser.parse(RSS_FEEDS["BBC"])

    articles = []

    for entry in feed.entries:
        articles.append({
            "title": entry.title,
            "url": entry.link,
            "published": entry.published if hasattr(entry, "published") else "",
            "summary": entry.summary if hasattr(entry, "summary") else "",
            "image_url": extract_image_url(entry),
            "source": "BBC"
        })

    return articles
