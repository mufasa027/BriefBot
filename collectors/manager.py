from collectors.rss.bbc import fetch_bbc_news
from collectors.rss.reuters import fetch_reuters_news
from collectors.rss.ap import fetch_ap_news
from collectors.rss.aljazeera import fetch_aljazeera_news
from collectors.rss.dw import fetch_dw_news
from collectors.rss.cnn import fetch_cnn_news
from collectors.rss.npr import fetch_npr_news
from collectors.rss.guardian import fetch_guardian_news
from collectors.rss.thehindu import fetch_thehindu_news
from collectors.rss.timesofindia import fetch_timesofindia_news
from collectors.rss.moscowtimes import fetch_moscowtimes_news

import re
from bs4 import BeautifulSoup

def _clean_text(text, source_name):
    if not text:
        return ""
    # Remove HTML tags
    soup = BeautifulSoup(str(text), "html.parser")
    text = soup.get_text(separator=" ").strip()
    
    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove raw http links
    text = re.sub(r'https?://\S+', '', text)

    
    # Strip common publisher suffixes from titles (e.g. " | Hindustan Times" or " - NDTV")
    text = re.sub(r'\s*[|\-]\s*' + re.escape(source_name) + r'.*?$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[|\-]\s*India News.*?$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[|\-]\s*World News.*?$', '', text, flags=re.IGNORECASE)
    return text.strip()


def fetch_all_news():
    """
    Orchestrates ingestion across all trusted news sources:
    BBC, Reuters, AP, DW, Al Jazeera, CNN, NPR, Guardian, The Hindu, Times of India, The Moscow Times.
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
        ("The Hindu", fetch_thehindu_news),
        ("Times of India", fetch_timesofindia_news),
        ("The Moscow Times", fetch_moscowtimes_news),
    ]

    for source_name, collector_fn in collectors:
        try:
            news_items = collector_fn()
            if news_items:
                # Limit to 15 articles per source to prevent LLM/API timeouts
                news_items = news_items[:15]
                
                # Clean up HTML and title suffixes before adding to main list
                for item in news_items:
                    item["title"] = _clean_text(item.get("title", ""), source_name)
                    item["summary"] = _clean_text(item.get("summary", ""), source_name)
                    
                articles.extend(news_items)
                print(f"[OK] Ingested {len(news_items)} articles from {source_name}")
        except Exception as e:
            print(f"[NOTICE] [{source_name}] Ingestion notice: {e}")

    return articles
