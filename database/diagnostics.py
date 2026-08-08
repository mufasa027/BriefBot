import os
from database.connection import get_connection
from services.storage_service import CAPTIONS_DIR, HASHTAGS_DIR, ARTICLES_DIR


def run_database_diagnostics():
    """
    Executes a thorough health check across SQLite database tables and file assets.
    Returns a diagnostic report dictionary.

    C-03 FIX: Uses try...finally to guarantee connection cleanup on any exception.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. Total Articles
        cursor.execute("SELECT COUNT(*) FROM news")
        total_articles = cursor.fetchone()[0]

        # 2. Total Stories
        cursor.execute("SELECT COUNT(*) FROM stories")
        total_stories = cursor.fetchone()[0]

        # 3. Duplicate URLs
        cursor.execute("SELECT url, COUNT(*) FROM news GROUP BY url HAVING COUNT(*) > 1")
        dup_urls = cursor.fetchall()

        # 4. Duplicate Headlines
        cursor.execute("SELECT title, COUNT(*) FROM news GROUP BY title HAVING COUNT(*) > 1")
        dup_headlines = cursor.fetchall()

        # 5. Duplicate Story IDs
        cursor.execute("SELECT story_id, COUNT(*) FROM stories GROUP BY story_id HAVING COUNT(*) > 1")
        dup_story_ids = cursor.fetchall()

        # 6. Generated Stories Checks
        cursor.execute("SELECT story_id, rendered_image_path, status FROM stories WHERE status = 'generated'")
        generated_stories = cursor.fetchall()

        missing_images = []
        missing_captions = []
        missing_hashtags = []
        missing_metadata = []
        broken_file_paths = []

        for sid, img_path, status in generated_stories:
            if not img_path or not os.path.exists(img_path):
                missing_images.append(sid)
                broken_file_paths.append(str(img_path))

            cap_p = os.path.join(CAPTIONS_DIR, f"caption_{sid}.txt")
            try:
                if not os.path.exists(cap_p) or os.path.getsize(cap_p) == 0:
                    missing_captions.append(sid)
            except OSError:
                missing_captions.append(sid)

            hash_p = os.path.join(HASHTAGS_DIR, f"hashtags_{sid}.txt")
            try:
                if not os.path.exists(hash_p) or os.path.getsize(hash_p) == 0:
                    missing_hashtags.append(sid)
            except OSError:
                missing_hashtags.append(sid)

            meta_p = os.path.join(ARTICLES_DIR, status, f"article_{sid}.json")
            try:
                if not os.path.exists(meta_p) or os.path.getsize(meta_p) == 0:
                    missing_metadata.append(sid)
            except OSError:
                missing_metadata.append(sid)

        report = {
            "total_articles": total_articles,
            "total_stories": total_stories,
            "duplicate_urls_count": len(dup_urls),
            "duplicate_headlines_count": len(dup_headlines),
            "duplicate_story_ids_count": len(dup_story_ids),
            "missing_images_count": len(missing_images),
            "missing_captions_count": len(missing_captions),
            "missing_hashtags_count": len(missing_hashtags),
            "missing_metadata_count": len(missing_metadata),
            "broken_file_paths_count": len(broken_file_paths),
            "is_healthy": (
                len(dup_story_ids) == 0
                and len(missing_images) == 0
                and len(missing_captions) == 0
                and len(missing_hashtags) == 0
                and len(missing_metadata) == 0
            ),
        }

        return report

    finally:
        conn.close()
