import re
import time
import json
from services.logging_service import log_event

GROWTH_HASHTAGS_POOL = [
    "#CipherBrief",
    "#WorldNews",
    "#GlobalNews",
    "#NewsUpdate",
    "#Breaking",
    "#DailyNews",
    "#CurrentAffairs",
    "#TrendingNews",
]

from ai.client import get_ai_client

def calculate_coverage_score(num_sources: int, sources_list: list) -> int:
    if num_sources <= 1:
        return 40
    elif num_sources == 2:
        return 70
    elif num_sources == 3:
        return 88
    else:
        return 100


def evaluate_editorial_recommendation(story: any) -> dict:
    num_sources = story.num_sources
    score = story.overall_story_score
    coverage_score = calculate_coverage_score(num_sources, story.supporting_sources)
    all_sources = [story.primary_source] + story.supporting_sources

    if num_sources >= 2 and score >= 75:
        recommendation = "APPROVE"
        reason = f"Verified by {num_sources} top sources ({', '.join(all_sources[:3])}). High overall score ({score}/100)."
    elif num_sources >= 1 and score >= 85:
        recommendation = "APPROVE"
        reason = f"High-impact breaking news lead from {story.primary_source}. Score: {score}/100."
    elif num_sources >= 2 and score >= 50:
        recommendation = "HOLD"
        reason = f"Multi-source coverage ({num_sources} sources), but moderate score ({score}/100). Needs editor review."
    elif score < 40:
        recommendation = "REJECT"
        reason = f"Low importance score ({score}/100) and single source coverage."
    else:
        recommendation = "HOLD"
        reason = f"Single-source report from {story.primary_source}. Awaiting cross-verification."

    return {
        "coverage_score": coverage_score,
        "recommendation": recommendation,
        "reason": reason,
    }


def format_exact_10_hashtags(hashtags_raw: str, category: str = "News", entities: list = None) -> str:
    """
    Enforces EXACTLY 10 hashtags:
    - 6 article-specific hashtags
    - 4 CipherBrief growth hashtags (from pool)
    """
    found_tags = re.findall(r"#\w+", str(hashtags_raw))
    cleaned = []
    seen = set()

    for tag in found_tags:
        clean = f"#{tag.lstrip('#')}"
        if clean.lower() not in seen:
            seen.add(clean.lower())
            cleaned.append(clean)

    # Separate article vs growth
    growth_selected = []
    article_tags = []

    for tag in cleaned:
        if tag in GROWTH_HASHTAGS_POOL and len(growth_selected) < 4:
            growth_selected.append(tag)
        elif tag not in GROWTH_HASHTAGS_POOL:
            article_tags.append(tag)

    # Ensure 6 article-specific tags
    default_article_pool = [
        f"#{category.replace(' ', '')}",
        "#NewsAlert",
        "#Report",
        "#DailyBrief",
        "#Update",
    ]

    for fallback in default_article_pool:
        if len(article_tags) >= 6:
            break
        if fallback.lower() not in seen:
            seen.add(fallback.lower())
            article_tags.append(fallback)

    article_tags = article_tags[:6]

    # Ensure 4 growth tags
    for g_tag in GROWTH_HASHTAGS_POOL:
        if len(growth_selected) >= 4:
            break
        if g_tag.lower() not in seen:
            seen.add(g_tag.lower())
            growth_selected.append(g_tag)

    growth_selected = growth_selected[:4]

    final_10 = article_tags + growth_selected
    return " ".join(final_10)


STORY_SYNTHESIS_PROMPT = """
You are the Executive Editor of CipherBrief.
Synthesize coverage of a news event into an authoritative Instagram post payload.

Requirements:
- improved_headline: Punchy 6-10 word authoritative headline.
- summary: Synthesized 2-3 sentence summary (max 110 words).
- caption: Comprehensive Instagram post caption summarizing key facts. 
  CAPTION RULES:
  - 2-4 short paragraphs
  - clear news-focused hook/context
  - concise explanation of why the story matters
  - optional key detail
  - professional CTA
  - use exactly @cipherbrief when referring to the account
  - never invent another account handle
  - do not make the caption simply repeat the headline
- hashtags: Generate 10-12 HIGHLY-SPECIFIC hashtags. 
  HASHTAG RULES:
  - You MUST include at least 6 ultra-specific tags based on the core entities of the story (e.g. specific people, cities, companies, or exact event names).
  - DO NOT generate generic tags like #WorldNews or #BreakingNews for these 6.
  - Then add 4 general/growth hashtags.

Return ONLY valid JSON:
{
    "improved_headline": "...",
    "summary": "...",
    "caption": "...",
    "hashtags": "#SpecificPerson #SpecificCity #SpecificEvent #Entity #Company #Context #CipherBrief #WorldNews #GlobalNews #Breaking"
}
"""


def synthesize_story_post_copy(story: any, max_retries: int = 3) -> dict:
    """
    Synthesizes multi-source story copy with AI retries (3 retries).
    Guarantees non-empty caption and EXACTLY 10 hashtags.
    """
    story_dict = story.to_dict() if hasattr(story, "to_dict") else story
    articles = story_dict.get("articles", [])

    sources_text = []
    for a in articles:
        src = a.get("source", "Source")
        t = a.get("title", "")
        s = a.get("summary", "")
        sources_text.append(f"[{src}] Title: {t}\nSummary: {s}")

    combined_input = "\n\n".join(sources_text)
    primary_title = articles[0].get("title", "") if articles else story_dict.get("story_title", "")
    primary_summary = articles[0].get("summary", "") if articles else ""

    fallback_caption = f"📰 {primary_title}\n\n{primary_summary}\n\nMulti-source reporting synthesized by @cipherbrief."
    fallback_hashtags_raw = f"#CipherBrief #{story_dict.get('category', 'News').replace(' ', '')} #WorldNews #BreakingNews #GlobalNews #DailyNews #NewsUpdate #Headlines #CurrentAffairs #TrendingNews"

    improved_headline = primary_title
    summary = primary_summary
    caption = fallback_caption
    hashtags_raw = fallback_hashtags_raw

    client = get_ai_client()
    if client:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model="deepseek/deepseek-chat",
                    temperature=0.25,
                    max_tokens=500,
                    messages=[
                        {"role": "system", "content": STORY_SYNTHESIS_PROMPT},
                        {"role": "user", "content": f"Multi-Source Coverage:\n\n{combined_input}"}
                    ],
                )
                raw = response.choices[0].message.content.strip()
                clean_json = re.sub(r"```json|```", "", raw).strip()
                data = json.loads(clean_json)

                improved_headline = data.get("improved_headline")
                if not improved_headline or len(improved_headline.strip()) < 5:
                    improved_headline = primary_title

                summary = data.get("summary")
                if not summary or len(summary.strip()) < 10:
                    summary = primary_summary

                caption = data.get("caption")
                if not caption or len(caption.strip()) < 10:
                    caption = fallback_caption

                hashtags_raw = data.get("hashtags") or fallback_hashtags_raw
                
                log_event("AI_SYNTHESIS_SUCCESS", f"AI synthesis attempt #{attempt} succeeded", article_uuid=story_dict.get("story_id"))
                break
            except Exception as e:
                log_event("AI_SYNTHESIS_RETRY", f"AI synthesis attempt #{attempt} failed ({e}). Retrying...", article_uuid=story_dict.get("story_id"), level="WARNING")
                time.sleep(1.5 * attempt)

    final_hashtags = format_exact_10_hashtags(hashtags_raw, category=story_dict.get("category", "News"))

    return {
        "improved_headline": str(improved_headline).strip(),
        "summary": str(summary).strip(),
        "caption": str(caption).strip(),
        "hashtags": final_hashtags,
    }
