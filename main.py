import time
from ai.ranker import calculate_score
from database.migrations import create_database
from collectors.manager import fetch_all_news
from database.crud import save_articles
from ai.summarizer import summarize_article


def main():
    start = time.time()

    print("=" * 60)
    print("BriefBot AI News Pipeline")
    print("=" * 60)

    print("\nCreating database...")
    create_database()
    print("OK Database Ready\n")

    print("Collecting news...")
    articles = fetch_all_news()

    print(f"OK Collected {len(articles)} articles.\n")

    successful = 0
    failed = 0

    for i, article in enumerate(articles, start=1):

        title_safe = article['title'].encode('ascii', 'replace').decode('ascii')
        print(f"[{i}/{len(articles)}] {article['source']} | {title_safe}")

        try:
            summarize_article(article)

            article["final_score"] = calculate_score(article)

            successful += 1

            print(
                f"   OK {article['category']} | "
                f"{article['importance']}/10 | "
                f"{article['confidence']}%"
            )

        except Exception as e:

            failed += 1
            print(f"   ERROR {e}")

    print("\nSaving articles...")

    articles.sort(
        key=lambda x: x.get("final_score", 0),
        reverse=True,
    )

    saved = save_articles(articles)
    
    print("
Clustering stories...")
    from database.crud import get_articles_sorted_by_score, save_stories, get_story_by_id
    from story_engine.cluster import cluster_articles_into_stories
    from story_engine.editorial_v1_1 import evaluate_story_v1_1
    
    raw_arts = get_articles_sorted_by_score(limit=150)
    if raw_arts:
        clustered = cluster_articles_into_stories(raw_arts, similarity_threshold=0.45)
        
        print("
Evaluating V1.1 Editorial Scores...")
        for i, story in enumerate(clustered, start=1):
            existing = get_story_by_id(story.story_id)
            if existing and existing.editorial_score is not None:
                story.impact_score = existing.impact_score
                story.virality_score = existing.virality_score
                story.freshness_score = existing.freshness_score
                story.credibility_score = existing.credibility_score
                story.audience_relevance_score = existing.audience_relevance_score
                story.editorial_score = existing.editorial_score
                story.editorial_reason = existing.editorial_reason
                story.editorial_recommendation = existing.editorial_recommendation
                story.confidence_score = existing.confidence_score
                story.confidence_level = existing.confidence_level
                story.source_agreement = existing.source_agreement
            else:
                evaluate_story_v1_1(story)
                if story.editorial_score is not None:
                    print(f"   Scored {story.story_id}: {story.editorial_score}/100")
        
        saved_stories = save_stories(clustered)
        print(f"OK Clustered {len(clustered)} stories and saved {saved_stories} updates.")

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