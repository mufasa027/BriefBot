import feedparser

RSS_URL = "https://apnews.com/hub/ap-top-news/rss"


def fetch_ap_news():
    feed = feedparser.parse(RSS_URL)

    articles = []

    for entry in feed.entries:
        articles.append(
            {
                "source": "AP",
                "title": entry.title,
                "url": entry.link,
                "summary": getattr(entry, "summary", ""),
                "published": getattr(entry, "published", ""),
            }
        )

    return articles