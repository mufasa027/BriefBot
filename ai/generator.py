import re
import json
from services.image_fetcher import fetch_image
from designer.renderer import render
from database.crud import update_article_generated_post

from ai.client import get_ai_client
from services.logging_service import log_event


GENERATE_PROMPT = """
You are an expert newsroom social media editor for CipherBrief.
Given an article, generate an optimized Instagram post payload.

Return ONLY valid JSON in this exact structure:
{
    "improved_headline": "Punchy 6-10 word editorial headline",
    "summary": "Clear, informative 2-3 sentence summary (max 110 words)",
    "caption": "Engaging Instagram post caption with context and call-to-action",
    "hashtags": "#News #CipherBrief #StayInformed #Breaking #WorldNews"
}
"""


def generate_post_assets(article: dict, render_image: bool = True) -> dict:
    """
    Generates improved headline, summary, Instagram caption, and hashtags using AI,
    fetches the article photo, renders the post PNG, and updates DB status to 'generated'.
    """
    article_id = article.get("id")
    title = article.get("title", "")
    orig_summary = article.get("summary", "")
    category = article.get("category", "News")

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
                    {"role": "system", "content": GENERATE_PROMPT},
                    {"role": "user", "content": f"Source: {article.get('source')}\nTitle: {title}\nSummary: {orig_summary}"}
                ],
            )
            raw = response.choices[0].message.content.strip()
            clean_json = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(clean_json)

            improved_headline = data.get("improved_headline", title)
            summary = data.get("summary", orig_summary)
            caption = data.get("caption", caption)
            hashtags = data.get("hashtags", hashtags)

        except Exception as e:
            log_event("AI_GENERATION", f"Notice: AI post generation fallback ({e})", level="WARNING")

    # Update article dict
    article["title"] = improved_headline
    article["summary"] = summary
    article["caption"] = caption
    article["hashtags"] = hashtags

    rendered_path = None
    if render_image:
        image_path = fetch_image(article)
        out_filename = f"output/post_{article_id or 'preview'}.png"
        rendered_path = render(
            article=article,
            image_path=image_path,
            template_path="assets/template.png",
            output_path=out_filename
        )
        article["rendered_image_path"] = rendered_path

    if article_id:
        update_article_generated_post(
            article_id=article_id,
            rendered_image_path=rendered_path,
            caption=caption,
            hashtags=hashtags,
            new_title=improved_headline,
            new_summary=summary
        )

    return article
