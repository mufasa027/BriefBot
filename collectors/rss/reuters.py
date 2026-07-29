import feedparser


RSS_URL = "https://feeds.reuters.com/reuters/topNews"


def fetch_reuters_news():
    feed = feedparser.parse(RSS_URL)

    articles = []

    for entry in feed.entries:
        articles.append(
            {
                "source": "Reuters",
                "title": entry.title,
                "url": entry.link,
                "summary": getattr(entry, "summary", ""),
                "published": getattr(entry, "published", ""),
            }
        )

    return articles