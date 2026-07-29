import time

from database.migrations import create_database
from collectors.manager import fetch_all_news
from database.crud import save_articles
from ai.summarizer import summarize_article


def main():
    start = time.time()

    print("=" * 60)
    print("📰 BriefBot AI News Pipeline")
    print("=" * 60)

    print("\nCreating database...")
    create_database()
    print("✓ Database Ready\n")

    print("Collecting news...")
    articles = fetch_all_news()

    print(f"✓ Collected {len(articles)} articles.\n")

    successful = 0
    failed = 0

    for i, article in enumerate(articles, start=1):

        print(
            f"[{i}/{len(articles)}] {article['source']} | {article['title']}"
        )

        try:
            summarize_article(article)

            successful += 1

            print(
                f"   ✓ {article['category']} | "
                f"{article['importance']}/10 | "
                f"{article['confidence']}%"
            )

        except Exception as e:

            failed += 1

            print(f"   ✗ {e}")

    print("\nSaving articles...")

    saved = save_articles(articles)

    elapsed = round(time.time() - start, 2)

    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)

    print(f"Collected     : {len(articles)}")
    print(f"AI Successful : {successful}")
    print(f"AI Failed     : {failed}")
    print(f"Saved         : {saved}")
    print(f"Duplicates    : {len(articles) - saved}")
    print(f"Runtime       : {elapsed} sec")

    print("=" * 60)


if __name__ == "__main__":
    main()