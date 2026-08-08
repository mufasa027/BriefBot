import re
from datetime import timezone
from email.utils import parsedate_to_datetime


def _extract_tokens(text):
    """
    Normalizes text into lowercase alphanumeric word tokens, removing common stop words.
    """
    if not text:
        return set()
    stopwords = {"a", "an", "the", "in", "on", "at", "of", "and", "or", "to", "for", "with", "by", "is", "are", "was", "were", "be", "has", "have", "had", "as", "after", "over", "about"}
    tokens = set(re.findall(r"\b[a-z0-9]{3,}\b", text.lower()))
    return tokens - stopwords


def jaccard_similarity(set1, set2):
    """
    Calculates Jaccard similarity coefficient between two sets (0.0 to 1.0).
    """
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return float(intersection / union) if union > 0 else 0.0


def calculate_entity_match_score(art1, art2):
    """
    Calculates named entity match score across countries, people, organizations, and topics.
    """
    score = 0.0
    weight_total = 0.0

    entity_keys = ["countries", "people", "organizations", "topics", "keywords"]
    for key in entity_keys:
        val1 = str(art1.get(key, ""))
        val2 = str(art2.get(key, ""))
        set1 = _extract_tokens(val1)
        set2 = _extract_tokens(val2)
        if set1 and set2:
            match = jaccard_similarity(set1, set2)
            score += match
            weight_total += 1.0

    return (score / weight_total) if weight_total > 0 else 0.0


def calculate_time_proximity_factor(pub1_str, pub2_str):
    """
    Calculates time proximity multiplier (1.0 for close events, decaying over 48 hours).
    """
    if not pub1_str or not pub2_str:
        return 0.8
    try:
        t1 = parsedate_to_datetime(pub1_str)
        t2 = parsedate_to_datetime(pub2_str)
        if t1.tzinfo is None:
            t1 = t1.replace(tzinfo=timezone.utc)
        if t2.tzinfo is None:
            t2 = t2.replace(tzinfo=timezone.utc)

        hours_diff = abs((t1 - t2).total_seconds()) / 3600.0
        if hours_diff <= 6:
            return 1.0
        elif hours_diff <= 12:
            return 0.85
        elif hours_diff <= 24:
            return 0.70
        elif hours_diff <= 48:
            return 0.40
        else:
            return 0.10
    except Exception:
        return 0.80


def compute_article_similarity(art1, art2):
    """
    Computes overall multi-signal similarity score (0.0 to 1.0) between two articles.
    Combines:
    - Title Jaccard similarity (weight: 0.40)
    - Summary token overlap (weight: 0.25)
    - Named entities match (weight: 0.25)
    - Category match boost (weight: 0.10)
    Multiplied by time proximity decay factor.
    """
    title1_tokens = _extract_tokens(art1.get("title", ""))
    title2_tokens = _extract_tokens(art2.get("title", ""))
    title_sim = jaccard_similarity(title1_tokens, title2_tokens)

    summary1_tokens = _extract_tokens(art1.get("summary", ""))
    summary2_tokens = _extract_tokens(art2.get("summary", ""))
    summary_sim = jaccard_similarity(summary1_tokens, summary2_tokens)

    entity_sim = calculate_entity_match_score(art1, art2)

    cat1 = str(art1.get("category", "")).lower()
    cat2 = str(art2.get("category", "")).lower()
    cat_sim = 1.0 if (cat1 and cat2 and cat1 == cat2) else 0.0

    raw_similarity = (title_sim * 0.40) + (summary_sim * 0.25) + (entity_sim * 0.25) + (cat_sim * 0.10)
    time_factor = calculate_time_proximity_factor(art1.get("published"), art2.get("published"))

    final_score = raw_similarity * time_factor
    return round(float(final_score), 4)
