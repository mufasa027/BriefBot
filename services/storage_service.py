import os
import json
import uuid
from services.logging_service import log_event

from settings import BASE_DIR

BASE_DATA_DIR = os.path.join(BASE_DIR, "data")
ARTICLES_DIR = os.path.join(BASE_DATA_DIR, "articles")
RENDERS_DIR = os.path.join(BASE_DATA_DIR, "renders")
CAPTIONS_DIR = os.path.join(BASE_DATA_DIR, "captions")
HASHTAGS_DIR = os.path.join(BASE_DATA_DIR, "hashtags")
LOGS_DIR = os.path.join(BASE_DATA_DIR, "logs")

# C-08 FIX: Added "queued" and "publishing" to status directories.
# Without these, save_article_json() raises FileNotFoundError when
# transition_article_status() saves JSON with status="queued" or "publishing".
for status_folder in ["new", "post_ready", "approved", "rejected", "queued", "publishing", "published", "failed"]:
    os.makedirs(os.path.join(ARTICLES_DIR, status_folder), exist_ok=True)

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(CAPTIONS_DIR, exist_ok=True)
os.makedirs(HASHTAGS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)


def get_or_create_article_uuid(article):
    art_uuid = article.get("uuid") or article.get("story_id")
    if not art_uuid or str(art_uuid) == "nan" or str(art_uuid) == "None":
        art_uuid = str(uuid.uuid4())
        article["uuid"] = art_uuid
    return art_uuid


def save_article_json(article, status="new"):
    art_uuid = get_or_create_article_uuid(article)
    article["status"] = status
    target_path = os.path.join(ARTICLES_DIR, status, f"article_{art_uuid}.json")

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(article, f, indent=2, default=str)
        log_event("STORAGE", f"Saved article JSON to {target_path}", article_uuid=art_uuid)
        return os.path.abspath(target_path)
    except Exception as e:
        log_event("STORAGE_ERROR", f"Failed to save JSON ({e})", article_uuid=art_uuid, level="ERROR")
        return None


def save_caption_file(article_uuid, caption_text):
    target_path = os.path.join(CAPTIONS_DIR, f"caption_{article_uuid}.txt")
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(caption_text or "")
        log_event("STORAGE", f"Saved caption to {target_path}", article_uuid=article_uuid)
        return os.path.abspath(target_path)
    except Exception as e:
        log_event("STORAGE_ERROR", f"Failed to save caption ({e})", article_uuid=article_uuid, level="ERROR")
        return None


def save_hashtags_file(article_uuid, hashtags_text):
    target_path = os.path.join(HASHTAGS_DIR, f"hashtags_{article_uuid}.txt")
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(hashtags_text or "")
        log_event("STORAGE", f"Saved hashtags to {target_path}", article_uuid=article_uuid)
        return os.path.abspath(target_path)
    except Exception as e:
        log_event("STORAGE_ERROR", f"Failed to save hashtags ({e})", article_uuid=article_uuid, level="ERROR")
        return None


def get_render_path_for_uuid(article_uuid):
    return os.path.abspath(os.path.join(RENDERS_DIR, f"post_{article_uuid}.png"))


def validate_story_assets(story_id, render_path, status="post_ready"):
    """
    Strict Transactional Validation requiring ALL assets to exist:
    1. render.png (must be valid image)
    2. caption.txt (non-empty > 10 bytes)
    3. hashtags.txt (non-empty > 10 bytes)
    4. metadata.json / article.json
    Returns (is_valid_boolean, list_of_missing_assets).
    """
    missing = []

    # 1. Render PNG (Exists + Valid Image)
    if not render_path or not os.path.exists(render_path) or os.path.getsize(render_path) < 100:
        missing.append("render.png (missing or empty)")
    else:
        try:
            from PIL import Image
            img = Image.open(render_path)
            img.verify()
        except OSError:
            missing.append("render.png (corrupted, breaks Live Preview)")

    # 2. Caption TXT (> 10 bytes)
    cap_path = os.path.join(CAPTIONS_DIR, f"caption_{story_id}.txt")
    if not os.path.exists(cap_path) or os.path.getsize(cap_path) < 10:
        missing.append("caption.txt")

    # 3. Hashtags TXT (> 10 bytes)
    hash_path = os.path.join(HASHTAGS_DIR, f"hashtags_{story_id}.txt")
    if not os.path.exists(hash_path) or os.path.getsize(hash_path) < 10:
        missing.append("hashtags.txt")

    # 4. Metadata / Article JSON
    meta_path = os.path.join(ARTICLES_DIR, status, f"article_{story_id}.json")
    if not os.path.exists(meta_path) or os.path.getsize(meta_path) == 0:
        missing.append("article.json / metadata.json")

    is_valid = len(missing) == 0
    return is_valid, missing
