import re
import json
from services.image_fetcher import fetch_image
from services.logging_service import log_event
from services.storage_service import get_or_create_article_uuid, save_caption_file, save_hashtags_file

from ai.client import get_ai_client

AI_PROMPT = """
You are an expert newsroom social media editor for CipherBrief.
Given an article title and summary, generate an optimized Instagram post payload.

Return ONLY valid JSON in this exact structure:
{
    "improved_headline": "Punchy 6-10 word editorial headline",
    "summary": "Clear, informative 2-3 sentence summary (max 110 words)",
    "caption": "Engaging Instagram post caption with context and call-to-action",
    "hashtags": "#News #CipherBrief #StayInformed #Breaking #WorldNews"
}
"""


def process_and_generate_article(article: dict) -> dict:
    """
    Downloads article image, generates rewritten headline, summary, caption, and hashtags.
    Saves caption and hashtag files, and returns updated article dictionary.
    """
    art_uuid = get_or_create_article_uuid(article)
    title = article.get("title", "")
    orig_summary = article.get("summary", "")
    category = article.get("category", "World")

    log_event("ARTICLE_PROCESS", f"Processing article: '{title[:40]}...'", article_uuid=art_uuid)

    # 1. Download/Fetch Image
    try:
        img_path = fetch_image(article)
        article["image_local_path"] = img_path
        log_event("IMAGE_FETCH", f"Fetched image: {img_path}", article_uuid=art_uuid)
    except Exception as e:
        log_event("IMAGE_FETCH_ERROR", f"Image fetch warning ({e})", article_uuid=art_uuid, level="WARNING")

    # 2. AI Post Generation
    client = get_ai_client()
    improved_headline = title
    summary = orig_summary
    caption = f"📰 {title}\n\n{orig_summary}\n\nStay informed with @cipherbrief."
    hashtags = f"#CipherBrief #{category.replace(' ', '')} #News #StayInformed #Breaking"

    if client:
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-chat-v3.1",
                temperature=0.3,
                max_tokens=450,
                messages=[
                    {"role": "system", "content": AI_PROMPT},
                    {"role": "user", "content": f"Source: {article.get('source')}\nTitle: {title}\nSummary: {orig_summary}"}
                ],
            )
            raw = response.choices[0].message.content.strip()
            clean_json = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(clean_json)

            improved_headline = re.sub(r'<[^>]+>', '', data.get("improved_headline", title))
            summary = re.sub(r'<[^>]+>', '', data.get("summary", orig_summary))
            caption = data.get("caption", caption)
            hashtags = data.get("hashtags", hashtags)
            log_event("AI_GENERATE", "Successfully generated AI headline, summary, caption & hashtags", article_uuid=art_uuid)
        except Exception as e:
            log_event("AI_GENERATE_FALLBACK", f"Used rule fallback ({e})", article_uuid=art_uuid, level="WARNING")

    # Update article dict
    article["title"] = improved_headline
    article["summary"] = summary
    article["caption"] = caption
    article["hashtags"] = hashtags

    # Save caption & hashtags files
    save_caption_file(art_uuid, caption)
    save_hashtags_file(art_uuid, hashtags)

    return article
