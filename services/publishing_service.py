from datetime import datetime
from services.logging_service import log_event
from services.storage_service import get_or_create_article_uuid
from services.queue_service import transition_article_status
from publisher.github_storage import sync_approved_post_to_github
from publisher.instagram import publish_to_instagram
from database.crud import get_connection


def publish_queued_article(article, public_image_url=None):
    """
    Executes the publishing pipeline for a queued article.
    State progression: 'queued' -> 'publishing' -> 'published' (or 'failed').

    C-03 FIX: Database connection wrapped in try...finally to prevent leaks.
    """
    art_id = article.get("id")
    art_uuid = get_or_create_article_uuid(article)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_event("PUBLISH_START", f"Started publishing process for article #{art_id or art_uuid}", article_uuid=art_uuid)

    # Step 1: Transition to 'publishing'
    transition_article_status(article, "publishing")

    try:
        # Step 2: GitHub Cloud Storage Sync
        sync_approved_post_to_github(article)

        # Step 3: Instagram Graph API Direct Publish (if credentials provided)
        ig_post_id = None
        caption_full = f"{article.get('caption', '')}\n\n{article.get('hashtags', '')}"

        if public_image_url:
            ig_post_id = publish_to_instagram(public_image_url, caption_full)

        if not ig_post_id:
            ig_post_id = f"local_pub_{art_uuid[:8]}"

        # Step 4: Record success & transition to 'published'
        article["posted"] = 1
        article["posted_time"] = now_str
        article["instagram_post_id"] = ig_post_id

        # Update DB posted fields
        # C-03 FIX: Wrap DB operation in try...finally to guarantee connection release
        if art_id:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE news SET posted = 1, posted_time = ?, instagram_post_id = ? WHERE id = ?",
                    (now_str, ig_post_id, art_id)
                )
                conn.commit()
            finally:
                conn.close()

        transition_article_status(article, "published")
        log_event("PUBLISH_SUCCESS", f"Published post successfully. IG ID: {ig_post_id}", article_uuid=art_uuid)
        return True, ig_post_id

    except Exception as e:
        err_msg = f"Publishing exception: {str(e)}"
        transition_article_status(article, "failed")
        log_event("PUBLISH_FAILED", err_msg, article_uuid=art_uuid, level="ERROR")
        return False, err_msg
