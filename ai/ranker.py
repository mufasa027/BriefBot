from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def calculate_score(article):
    score = 0

    # AI importance (max 60)
    score += article.get("importance", 5) * 6

    # AI confidence (max 20)
    score += article.get("confidence", 50) // 5

    # Freshness (max 20)
    try:
        published = parsedate_to_datetime(article["published"])

        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)

        hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600

        if hours <= 3:
            score += 20
        elif hours <= 6:
            score += 15
        elif hours <= 12:
            score += 10
        elif hours <= 24:
            score += 5

    except Exception:
        pass

    return int(score)