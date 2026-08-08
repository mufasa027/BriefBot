from datetime import datetime
import os
from services.logging_service import log_event
from services.storage_service import get_or_create_article_uuid
from services.queue_service import transition_article_status
from services.video_service import generate_static_reel
from publisher.github_storage import sync_approved_post_to_github
from publisher.instagram import publish_reel_to_instagram
from database.crud import get_connection


def publish_approved_story_as_reel(article):
    """
    Executes the Instagram Reel publishing pipeline for an approved article.
    State progression: 'approved' -> 'queued' -> 'publishing' -> 'published' (or 'failed').
    """
    art_id = article.get("id")
    art_uuid = get_or_create_article_uuid(article)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_event("PUBLISH_START", f"Started Reel publishing for article #{art_id or art_uuid}", article_uuid=art_uuid)

    # 1. Duplicate Protection
    if article.get("status") == "published" or article.get("instagram_media_id"):
        err_msg = "Already published \u2014 duplicate publishing prevented."
        log_event("PUBLISH_BLOCKED", err_msg, article_uuid=art_uuid, level="WARNING")
        return False, err_msg

    # 2. Status Validation
    if article.get("status") != "approved":
        err_msg = f"Story must be 'approved' to publish. Current status: {article.get('status')}"
        log_event("PUBLISH_BLOCKED", err_msg, article_uuid=art_uuid, level="ERROR")
        return False, err_msg

    # 3. Asset Validation
    png_path = article.get("rendered_image_path")
    caption = article.get("caption")
    hashtags = article.get("hashtags")
    
    if not png_path or not os.path.exists(png_path):
        return _fail_publish(article, "Missing PNG image file.")
    if not caption:
        return _fail_publish(article, "Missing caption text.")
    if not hashtags:
        return _fail_publish(article, "Missing hashtags.")

    # Proceed to Queued -> Publishing
    transition_article_status(article, "queued")
    transition_article_status(article, "publishing")

    # Update DB for attempts
    attempts = article.get("publish_attempts", 0) + 1
    _update_db_publishing_state(art_id, attempts, now_str)

    try:
        # 4. Generate MP4
        mp4_path = generate_static_reel(png_path, art_uuid)
        if not mp4_path:
            return _fail_publish(article, "Failed to generate MP4 via FFmpeg.")

        # 5. Sync to GitHub to get Public URL
        public_mp4_url = sync_approved_post_to_github(article)
        if not public_mp4_url:
            return _fail_publish(article, "Failed to sync MP4 to GitHub Storage (no public URL).")

        # 6. Publish to Instagram
        caption_full = f"{caption}\n\n{hashtags}"
        ig_post_id = publish_reel_to_instagram(public_mp4_url, caption_full)

        if not ig_post_id:
            return _fail_publish(article, "Failed to publish Reel to Instagram Graph API.")

        # 7. Success!
        article["posted"] = 1
        article["posted_time"] = now_str
        article["instagram_media_id"] = ig_post_id
        article["reel_video_path"] = mp4_path

        if art_id:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE news SET posted = 1, posted_time = ?, instagram_media_id = ?, reel_video_path = ?, published_time = ? WHERE id = ?",
                    (now_str, ig_post_id, mp4_path, now_str, art_id)
                )
                conn.commit()
            finally:
                conn.close()

        transition_article_status(article, "published")
        log_event("PUBLISH_SUCCESS", f"Published Reel successfully! IG ID: {ig_post_id}", article_uuid=art_uuid)
        return True, ig_post_id

    except Exception as e:
        return _fail_publish(article, f"Publishing exception: {str(e)}")


def _fail_publish(article, err_msg):
    art_id = article.get("id")
    art_uuid = article.get("uuid")
    transition_article_status(article, "failed")
    log_event("PUBLISH_FAILED", err_msg, article_uuid=art_uuid, level="ERROR")
    
    if art_id:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE news SET publish_error = ? WHERE id = ?", (err_msg, art_id))
            conn.commit()
        finally:
            conn.close()
            
    return False, err_msg


def _update_db_publishing_state(art_id, attempts, now_str):
    if not art_id:
        return
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE news SET publish_attempts = ?, queued_time = ?, publishing_time = ?, last_publish_attempt = ? WHERE id = ?",
            (attempts, now_str, now_str, now_str, art_id)
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

