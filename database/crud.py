import json
from database.connection import get_connection


def article_exists(url):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM news WHERE url = ?",
            (url,),
        )
        exists = cursor.fetchone() is not None
        return exists
    finally:
        conn.close()


def insert_article(article):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO news
            (
                source,
                title,
                summary,
                url,
                published,
                category,
                keywords,
                importance,
                virality_score,
                growth_score,
                freshness_score,
                confidence,
                sentiment,
                region,
                people,
                organizations,
                countries,
                topics,
                image_url,
                final_score,
                posted,
                posted_time,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article["source"],
                article["title"],
                article["summary"],
                article["url"],
                article["published"],
                article.get("category", "Uncategorized"),
                article.get("keywords", ""),
                article.get("importance", 5),
                article.get("virality_score", 50),
                article.get("growth_score", 50),
                article.get("freshness_score", 50),
                article.get("confidence", 50),
                article.get("sentiment", "Neutral"),
                article.get("region", "Global"),
                article.get("people", ""),
                article.get("organizations", ""),
                article.get("countries", ""),
                article.get("topics", ""),
                article.get("image_url", ""),
                article.get("final_score", 0),
                0,
                None,
                article.get("status", "new"),
            )
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def save_articles(articles):
    count = 0
    for article in articles:
        if not article.get("summary"):
            continue

        if insert_article(article):
            count += 1
    return count


def update_article_status(article_id, new_status):
    """
    Updates status of an article ('new', 'generated', 'approved', 'rejected', 'posted').
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE news SET status = ? WHERE id = ?",
            (new_status, article_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_article_timestamp(article_id, column_name, timestamp_val):
    """
    Updates specific timestamp column (e.g. 'approved_time', 'rejected_time', 'posted_time').
    """
    if column_name not in ["generated_time", "approved_time", "rejected_time", "posted_time"]:
        return

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE news SET {column_name} = ? WHERE id = ?",
            (timestamp_val, article_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_article_generated_post(article_id, rendered_image_path, caption, hashtags, new_title=None, new_summary=None, generated_time=None):
    """
    Updates generated post assets (rendered image path, caption, hashtags, generated_time, and status='generated').
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            UPDATE news
            SET rendered_image_path = ?,
                caption = ?,
                hashtags = ?,
                status = 'post_ready'
        """
        params = [rendered_image_path, caption, hashtags]

        if generated_time:
            query += ", generated_time = ?"
            params.append(generated_time)

        if new_title:
            query += ", title = ?"
            params.append(new_title)
        if new_summary:
            query += ", summary = ?"
            params.append(new_summary)

        query += " WHERE id = ?"
        params.append(article_id)

        cursor.execute(query, tuple(params))
        conn.commit()
    finally:
        conn.close()


def get_articles_sorted_by_score(limit=50, status_filter=None):
    """
    Retrieves news articles sorted by final_score descending.
    Optionally filters by status.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if status_filter:
            cursor.execute(
                "SELECT * FROM news WHERE status = ? ORDER BY final_score DESC LIMIT ?",
                (status_filter, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM news ORDER BY final_score DESC LIMIT ?",
                (limit,),
            )

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results
    finally:
        conn.close()


def insert_or_update_story(story_obj):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        s_dict = story_obj.to_dict() if hasattr(story_obj, "to_dict") else story_obj
        story_id = s_dict.get("story_id")

        articles_json = json.dumps(s_dict.get("articles", []), default=str)
        entities_json = json.dumps(s_dict.get("entities", {}), default=str)
        supporting_str = ", ".join(s_dict.get("supporting_sources", []))

        cursor.execute(
            """
            INSERT INTO stories
            (
                story_id,
                story_title,
                category,
                primary_source,
                primary_article_id,
                supporting_sources,
                num_sources,
                first_published,
                latest_update,
                overall_story_score,
                articles_json,
                entities_json,
                rendered_image_path,
                caption,
                hashtags,
                status,
                generated_time,
                instagram_media_id,
                reel_video_path,
                publish_attempts,
                queued_time,
                publishing_time,
                published_time,
                publish_error,
                last_publish_attempt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(story_id) DO UPDATE SET
                story_title=excluded.story_title,
                category=excluded.category,
                primary_source=excluded.primary_source,
                primary_article_id=excluded.primary_article_id,
                supporting_sources=excluded.supporting_sources,
                num_sources=excluded.num_sources,
                first_published=excluded.first_published,
                latest_update=excluded.latest_update,
                overall_story_score=excluded.overall_story_score,
                articles_json=excluded.articles_json,
                entities_json=excluded.entities_json,
                rendered_image_path=excluded.rendered_image_path,
                caption=excluded.caption,
                hashtags=excluded.hashtags,
                status=excluded.status,
                generated_time=excluded.generated_time,
                instagram_media_id=excluded.instagram_media_id,
                reel_video_path=excluded.reel_video_path,
                publish_attempts=excluded.publish_attempts,
                queued_time=excluded.queued_time,
                publishing_time=excluded.publishing_time,
                published_time=excluded.published_time,
                publish_error=excluded.publish_error,
                last_publish_attempt=excluded.last_publish_attempt
            """,
            (
                story_id,
                s_dict.get("story_title"),
                s_dict.get("category", "World"),
                s_dict.get("primary_source", ""),
                s_dict.get("primary_article_id"),
                supporting_str,
                s_dict.get("num_sources", 1),
                s_dict.get("first_published"),
                s_dict.get("latest_update"),
                s_dict.get("overall_story_score", 0),
                articles_json,
                entities_json,
                s_dict.get("rendered_image_path"),
                s_dict.get("caption"),
                s_dict.get("hashtags"),
                s_dict.get("status", "new"),
                s_dict.get("generated_time"),
                s_dict.get("instagram_media_id"),
                s_dict.get("reel_video_path"),
                s_dict.get("publish_attempts", 0),
                s_dict.get("queued_time"),
                s_dict.get("publishing_time"),
                s_dict.get("published_time"),
                s_dict.get("publish_error"),
                s_dict.get("last_publish_attempt"),
            )
        )
        conn.commit()
    finally:
        conn.close()


def save_stories(stories):
    count = 0
    for s in stories:
        insert_or_update_story(s)
        count += 1
    return count


def get_all_stories(status_filter=None, limit=50):
    from story_engine.story import Story

    conn = get_connection()
    try:
        cursor = conn.cursor()

        if status_filter and status_filter != "All":
            cursor.execute(
                "SELECT * FROM stories WHERE status = ? ORDER BY overall_story_score DESC LIMIT ?",
                (status_filter, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM stories ORDER BY overall_story_score DESC LIMIT ?",
                (limit,),
            )

        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

    stories = []
    for r in rows:
        articles = json.loads(r["articles_json"]) if r.get("articles_json") else []
        entities = json.loads(r["entities_json"]) if r.get("entities_json") else {}
        supporting = [s.strip() for s in r["supporting_sources"].split(",")] if r.get("supporting_sources") else []

        s_obj = Story(
            story_id=r["story_id"],
            story_title=r["story_title"],
            category=r["category"],
            primary_source=r["primary_source"],
            primary_article_id=r["primary_article_id"],
            articles=articles,
            supporting_sources=supporting,
            first_published=r["first_published"],
            latest_update=r["latest_update"],
            overall_story_score=r["overall_story_score"],
            entities=entities,
            status=r["status"],

        )
        s_obj.rendered_image_path = r.get("rendered_image_path")
        s_obj.caption = r.get("caption")
        s_obj.hashtags = r.get("hashtags")
        s_obj.generated_time = r.get("generated_time")
        stories.append(s_obj)

    return stories