import sqlite3
from config import DATABASE_NAME
from collectors.manager import fetch_all_news
from database.crud import save_articles

def run_diagnostics():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    print("==========================================================")
    print("TEMPORARY DEBUG REPORT: DATA INTEGRITY & DUPLICATES")
    print("==========================================================")

    # 1. Total Articles
    cursor.execute("SELECT COUNT(*) FROM news")
    total_articles = cursor.fetchone()[0]
    print(f"Total Articles: {total_articles}")

    # 2. Unique Articles (by URL)
    cursor.execute("SELECT COUNT(DISTINCT url) FROM news")
    unique_articles = cursor.fetchone()[0]
    print(f"Unique Articles (by URL): {unique_articles}")

    # 3. Duplicate URLs
    cursor.execute("SELECT url, COUNT(*) FROM news GROUP BY url HAVING COUNT(*) > 1")
    dup_urls = cursor.fetchall()
    print(f"Duplicate URLs: {len(dup_urls)}")

    # 4. Duplicate Headlines
    cursor.execute("SELECT title, COUNT(*) FROM news GROUP BY title HAVING COUNT(*) > 1")
    dup_headlines = cursor.fetchall()
    print(f"Duplicate Headlines: {len(dup_headlines)}")

    # 5. Unique Story IDs
    cursor.execute("SELECT COUNT(DISTINCT story_id) FROM stories")
    unique_stories = cursor.fetchone()[0]
    print(f"Unique Story IDs: {unique_stories}")

    # 6. Duplicate Story IDs
    cursor.execute("SELECT story_id, COUNT(*) FROM stories GROUP BY story_id HAVING COUNT(*) > 1")
    dup_story_ids = cursor.fetchall()
    print(f"Duplicate Story IDs: {len(dup_story_ids)}")

    # 7. Articles per Story
    cursor.execute("SELECT story_id, num_sources FROM stories")
    stories = cursor.fetchall()
    if stories:
        avg_arts = sum([s[1] for s in stories]) / len(stories)
        print(f"Avg Articles per Story: {avg_arts:.2f}")
    else:
        print("Avg Articles per Story: 0")

    # 8. Test RSS Fetching and Insertion
    print("\n--- Testing RSS Ingestion Pipeline ---")
    articles = fetch_all_news()
    print(f"RSS items fetched: {len(articles)}")
    
    seen_urls = set()
    unique_fetched = []
    for a in articles:
        if a['url'] not in seen_urls:
            seen_urls.add(a['url'])
            unique_fetched.append(a)
            
    print(f"RSS items skipped (internal duplicates): {len(articles) - len(unique_fetched)}")
    
    # Try inserting them (insert_article uses INSERT OR IGNORE)
    saved = save_articles(unique_fetched)
    print(f"RSS items inserted into DB: {saved}")
    print(f"RSS items skipped by SQLite (already exist): {len(unique_fetched) - saved}")

    conn.close()

if __name__ == "__main__":
    run_diagnostics()
