from publisher.github_storage import sync_approved_post_to_github
from publisher.instagram import publish_to_instagram
from database.crud import update_article_status


def publish_approved_article(article, public_image_url=None):
    """
    Orchestrates multi-channel publishing for an approved article.
    1. Syncs assets to GitHub Cloud Storage.
    2. Publishes to Instagram via Graph API (if credentials set and image URL provided).
    3. Updates database status to 'posted'.
    """
    article_id = article.get("id")

    # 1. Sync to GitHub Storage
    sync_approved_post_to_github(article)

    # 2. Publish to Instagram
    caption_full = f"{article.get('caption', '')}\n\n{article.get('hashtags', '')}"
    if public_image_url:
        ig_post_id = publish_to_instagram(public_image_url, caption_full)
        if ig_post_id and article_id:
            update_article_status(article_id, "posted")
            return ig_post_id

    if article_id:
        update_article_status(article_id, "posted")

    return True
