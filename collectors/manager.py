from collectors.rss.bbc import fetch_bbc_news
from collectors.rss.reuters import fetch_reuters_news
from collectors.rss.ap import fetch_ap_news
from collectors.rss.aljazeera import fetch_aljazeera_news


def fetch_all_news():
    articles = []

    collectors = [
        fetch_bbc_news,
        fetch_reuters_news,
        fetch_ap_news,
        fetch_aljazeera_news,
    ]

    for collector in collectors:
        try:
            news = collector()
            if news:
                articles.extend(news)
        except Exception as e:
            print(f"[ERROR] {collector.__name__}: {e}")

    return articles