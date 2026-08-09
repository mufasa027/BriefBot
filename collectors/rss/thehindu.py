from collectors.rss.utils import extract_image_url
import feedparser

RSS_URL = "https://www.thehindu.com/news/national/feeder/default.rss"

def fetch_thehindu_news():
    feed = feedparser.parse(RSS_URL)
    articles = []
    for entry in feed.entries:
        articles.append(
            {
                "image_url": extract_image_url(entry),
                "source": "The Hindu",
                "title": entry.title,
                "url": entry.link,
                "summary": getattr(entry, "summary", ""),
                "published": getattr(entry, "published", ""),
            }
        )
    return articles
