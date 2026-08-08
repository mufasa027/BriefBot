from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def calculate_freshness_score(published_str):
    """
    Calculates freshness score (0-100) based on hours elapsed since publication.
    """
    if not published_str:
        return 50

    try:
        published = parsedate_to_datetime(published_str)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)

        hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600

        if hours <= 2:
            return 100
        elif hours <= 4:
            return 85
        elif hours <= 8:
            return 70
        elif hours <= 12:
            return 55
        elif hours <= 24:
            return 40
        else:
            return 20
    except Exception:
        return 50


def calculate_virality_score(article):
    """
    Calculates virality potential (0-100) based on category, keywords, and AI confidence.
    """
    score = 50
    category = article.get("category", "").lower()
    title = article.get("title", "").lower()

    # High virality topics
    viral_keywords = ["breaking", "surge", "exclusive", "crisis", "deal", "ai", "tech", "election", "shock"]
    for kw in viral_keywords:
        if kw in title:
            score += 8

    if category in ["technology", "politics", "finance", "world"]:
        score += 10

    confidence = article.get("confidence", 50)
    score += (confidence - 50) // 5

    return int(max(10, min(100, score)))


def calculate_growth_score(article):
    """
    Calculates growth score (0-100) reflecting potential impact and user engagement.
    """
    importance = article.get("importance", 5) * 10
    confidence = article.get("confidence", 50)
    return int(max(10, min(100, (importance * 0.6) + (confidence * 0.4))))


def calculate_score(article):
    """
    Calculates all multi-metric scores and returns the weighted Overall Score (0-100).
    """
    # 1. Importance (0-100 scale)
    raw_importance = article.get("importance", 5)
    importance_score = int(max(10, min(100, raw_importance * 10 if raw_importance <= 10 else raw_importance)))
    article["importance"] = raw_importance

    # 2. Virality (0-100)
    virality = calculate_virality_score(article)
    article["virality_score"] = virality

    # 3. Growth Potential (0-100)
    growth = calculate_growth_score(article)
    article["growth_score"] = growth

    # 4. Freshness (0-100)
    freshness = calculate_freshness_score(article.get("published", ""))
    article["freshness_score"] = freshness

    # 5. Overall Score (Weighted combination)
    overall = (importance_score * 0.35) + (virality * 0.25) + (freshness * 0.25) + (growth * 0.15)
    final_score = int(max(10, min(100, overall)))
    article["final_score"] = final_score

    return final_score


def generate_score_explanation(article, num_sources=1):
    """
    Deterministically generates bullet points explaining the AI score based on underlying metrics.
    """
    explanation = []
    
    importance = article.get("importance", 5)
    if importance >= 9:
        explanation.append("Critical global relevance")
    elif importance >= 7:
        explanation.append("High global relevance")
        
    virality = article.get("virality_score", 50)
    if virality >= 85:
        explanation.append("Extremely high engagement potential")
    elif virality >= 70:
        explanation.append("Strong engagement potential")
        
    freshness = article.get("freshness_score", 50)
    if freshness >= 90:
        explanation.append("Breaking within 2 hours")
    elif freshness >= 70:
        explanation.append("Breaking within 8 hours")
        
    growth = article.get("growth_score", 50)
    if growth >= 80:
        explanation.append("High expected reach")
        
    if num_sources >= 3:
        explanation.append(f"Covered by {num_sources} trusted sources")
    elif num_sources == 2:
        explanation.append("Covered by multiple trusted sources")
        
    if not explanation:
        explanation.append("Standard news coverage")
        
    return explanation