import feedparser

RSS_URL = "https://www.aljazeera.com/xml/rss/all.xml"


def fetch_aljazeera_news():
    feed = feedparser.parse(RSS_URL)

    articles = []

    for entry in feed.entries:
        articles.append(
            {
                "source": "Al Jazeera",
                "title": entry.title,
                "url": entry.link,
                "summary": getattr(entry, "summary", ""),
                "published": getattr(entry, "published", ""),
            }
        )

    return articles