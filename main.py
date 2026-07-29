from collectors.rss.bbc import fetch_bbc_news

articles = fetch_bbc_news()

print(f"Fetched {len(articles)} articles\n")

for article in articles[:5]:
    print("=" * 60)
    print(article["title"])
    print(article["published"])
    print(article["link"])