from collectors.rss.utils import extract_image_url
import feedparser

RSS_URL = "https://news.google.com/rss/search?q=site:hindustantimes.com"

def fetch_hindustantimes_news():
    feed = feedparser.parse(RSS_URL)
    articles = []
    for entry in feed.entries:
        articles.append(
            {
                "image_url": extract_image_url(entry),
                "source": "Hindustan Times",
                "title": entry.title,
                "url": entry.link,
                "summary": getattr(entry, "summary", ""),
                "published": getattr(entry, "published", ""),
            }
        )
    return articles
