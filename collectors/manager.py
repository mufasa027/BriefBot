from collectors.rss.bbc import fetch_bbc_news
from collectors.rss.reuters import fetch_reuters_news
from collectors.rss.ap import fetch_ap_news
from collectors.rss.aljazeera import fetch_aljazeera_news
from collectors.rss.dw import fetch_dw_news
from collectors.rss.cnn import fetch_cnn_news
from collectors.rss.npr import fetch_npr_news
from collectors.rss.guardian import fetch_guardian_news


def fetch_all_news():
    """
    Orchestrates ingestion across all 8 trusted news sources:
    BBC, Reuters, AP, DW, Al Jazeera, CNN, NPR, Guardian.
    Returns a unified list of article dicts.
    """
    articles = []

    collectors = [
        ("BBC", fetch_bbc_news),
        ("Reuters", fetch_reuters_news),
        ("AP", fetch_ap_news),
        ("Al Jazeera", fetch_aljazeera_news),
        ("DW", fetch_dw_news),
        ("CNN", fetch_cnn_news),
        ("NPR", fetch_npr_news),
        ("Guardian", fetch_guardian_news),
    ]

    for source_name, collector_fn in collectors:
        try:
            news_items = collector_fn()
            if news_items:
                articles.extend(news_items)
                print(f"[OK] Ingested {len(news_items)} articles from {source_name}")
        except Exception as e:
            print(f"[NOTICE] [{source_name}] Ingestion notice: {e}")

    return articles
