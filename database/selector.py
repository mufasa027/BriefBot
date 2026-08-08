from database.connection import get_connection
from config import POSTS_PER_DAY


def get_daily_posts():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM news
        WHERE posted = 0
        ORDER BY final_score DESC
        LIMIT ?
        """,
        (POSTS_PER_DAY,),
    )

    rows = cursor.fetchall()

    columns = [c[0] for c in cursor.description]

    articles = [
        dict(zip(columns, row))
        for row in rows
    ]

    conn.close()

    return articles


def get_breaking_news():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM news
        WHERE posted = 0
        AND importance >= 9
        ORDER BY final_score DESC
        """
    )

    rows = cursor.fetchall()

    columns = [c[0] for c in cursor.description]

    articles = [
        dict(zip(columns, row))
        for row in rows
    ]

    conn.close()

    return articles