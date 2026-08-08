from story_engine.story import Story
from story_engine.similarity import compute_article_similarity

# Trusted source quality rankings
SOURCE_TRUST_RANK = {
    "Reuters": 10,
    "BBC": 9,
    "AP": 9,
    "Guardian": 8,
    "DW": 8,
    "Al Jazeera": 7,
    "CNN": 7,
    "NPR": 7,
}


def select_primary_source(articles):
    """
    Selects the Primary Source and primary article for a story cluster based on:
    1. Source trust ranking
    2. Completeness (summary & keyword length)
    3. AI confidence / importance score
    """
    if not articles:
        return None, None

    def article_quality_score(art):
        source = art.get("source", "")
        trust_weight = SOURCE_TRUST_RANK.get(source, 5) * 10
        importance = art.get("importance", 5) * 5
        confidence = art.get("confidence", 50) * 0.2
        summary_len = len(art.get("summary", "")) * 0.05
        return trust_weight + importance + confidence + summary_len

    best_article = max(articles, key=article_quality_score)
    primary_source = best_article.get("source", "Unknown")
    return primary_source, best_article


def cluster_articles_into_stories(articles, similarity_threshold=0.45):
    """
    Clustered multi-source news ingestion engine.
    Groups incoming news articles into unified Story clusters.
    Uses similarity_threshold=0.45 to prevent over-clustering unrelated stories.
    Returns a list of Story instances.
    """
    if not articles:
        return []

    # Deduplicate input articles by URL and title before clustering
    seen_urls = set()
    seen_titles = set()
    unique_articles = []
    for art in articles:
        url = str(art.get("url", "")).strip().lower()
        title = str(art.get("title", "")).strip().lower()
        if url and url in seen_urls:
            continue
        if title and title in seen_titles:
            continue
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)
        unique_articles.append(art)

    stories = []

    for art in unique_articles:
        matched_story = None
        best_sim = 0.0

        for story in stories:
            primary_art = story.articles[0] if story.articles else None
            if primary_art:
                sim = compute_article_similarity(art, primary_art)
                if sim >= similarity_threshold and sim > best_sim:
                    best_sim = sim
                    matched_story = story

        if matched_story:
            matched_story.add_article(art)
            primary_source, primary_art = select_primary_source(matched_story.articles)
            matched_story.primary_source = primary_source
            matched_story.primary_article_id = primary_art.get("id") if primary_art else None
        else:
            primary_source = art.get("source", "Unknown")
            art_id = art.get("id")
            new_story = Story(
                story_id=f"story_{art_id}" if art_id else None,
                story_title=art.get("title", ""),
                category=art.get("category", "World"),
                primary_source=primary_source,
                primary_article_id=art_id,
                articles=[art],
                first_published=art.get("published"),
                latest_update=art.get("published"),
                overall_story_score=art.get("final_score", 0),
                status=art.get("status", "new"),
            )
            stories.append(new_story)

    return stories
