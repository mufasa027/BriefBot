from database.connection import get_connection


def article_exists(url):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM news WHERE url = ?",
        (url,),
    )

    exists = cursor.fetchone() is not None

    conn.close()

    return exists


def insert_article(article):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO news
        (
            source,
            title,
            summary,
            url,
            published,
            category,
            keywords,
            importance,
            confidence,
            sentiment,
            region,
            people,
            organizations,
            countries,
            topics,
            image_url,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            article.get("confidence", 50),
            article.get("sentiment", "Neutral"),
            article.get("region", "Global"),
            article.get("people", ""),
            article.get("organizations", ""),
            article.get("countries", ""),
            article.get("topics", ""),
            article.get("image_url", ""),
            "new",
        ),
    )

    conn.commit()
    conn.close()


def save_articles(articles):
    count = 0

    for article in articles:

        if article_exists(article["url"]):
            continue

        if not article.get("summary"):
            continue

        insert_article(article)
        count += 1

    return count