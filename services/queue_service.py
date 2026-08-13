import time
from datetime import datetime
from database.crud import update_article_status, update_article_timestamp, insert_or_update_story
import sqlalchemy.exc
from services.logging_service import log_event
from services.storage_service import (
    save_article_json,
    get_or_create_article_uuid,
    save_caption_file,
    save_hashtags_file,
    validate_story_assets,
    get_render_path_for_uuid,
)


def transition_article_status(article, new_status):
    """
    Transitions article/story status across workflow stages ('new', 'generated', 'approved', 'rejected', 'queued', 'publishing', 'published', 'failed').
    Saves JSON state under data/articles/<new_status>/ and updates database.
    """
    from services.auth_service import require_admin
    require_admin()
    
    art_id = article.get("id")
    art_uuid = get_or_create_article_uuid(article)
    old_status = article.get("status", "new")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    article["status"] = new_status

    if new_status == "approved":
        article["approved_time"] = now_str
        save_caption_file(art_uuid, article.get("caption", ""))
        save_hashtags_file(art_uuid, article.get("hashtags", ""))
        if art_id:
            update_article_timestamp(art_id, "approved_time", now_str)
        log_event("APPROVE", f"Approved #{art_id or art_uuid}", article_uuid=art_uuid)

    elif new_status == "rejected":
        article["rejected_time"] = now_str
        if art_id:
            update_article_timestamp(art_id, "rejected_time", now_str)
        log_event("REJECT", f"Rejected #{art_id or art_uuid}", article_uuid=art_uuid)

    save_article_json(article, status=new_status)

    if art_id:
        try:
            update_article_status(art_id, new_status)
        except sqlalchemy.exc.SQLAlchemyError as e:
            log_event("DB_STATUS_ERROR", f"Failed updating DB status ({e})", article_uuid=art_uuid, level="ERROR")
    else:
        try:
            insert_or_update_story(article)
        except sqlalchemy.exc.SQLAlchemyError:
            pass

    log_event("STATUS_TRANSITION", f"Transitioned status: '{old_status}' -> '{new_status}'", article_uuid=art_uuid)
    return new_status


def handle_generate_story_action(story_obj, force=False):
    """
    Transactional & Atomic Story Post Generation:
    1. Pre-render Duplicate Check: Skips generation if story is already rendered (unless force=True).
    2. Synthesizes copy, fetches photo, renders post PNG, saves caption/hashtag/metadata files.
    3. Transactional Validation: Verifies all 5 required assets exist.
    4. Atomic Commit: Marks status as 'post_ready' if valid, or rolls back to 'new' if any asset is missing.
    """
    from services.auth_service import require_admin
    require_admin()
    
    start_time = time.time()
    from story_engine.editorial import synthesize_story_post_copy
    from services.renderer_service import render_post_for_article
    from services.image_fetcher import fetch_image
    from services.video_service import generate_static_reel

    s_dict = story_obj.to_dict() if hasattr(story_obj, "to_dict") else story_obj
    story_id = s_dict.get("story_id")
    existing_render = s_dict.get("rendered_image_path") or get_render_path_for_uuid(story_id)

    # 1. PRE-RENDER DUPLICATE CHECK (Bug #5)
    if not force and s_dict.get("status") in ["post_ready", "approved", "queued", "published"]:
        is_valid, _ = validate_story_assets(story_id, existing_render, status=s_dict.get("status"))
        if is_valid:
            log_event("DUPLICATE_RENDER_SKIPPED", f"Skipped duplicate rendering for Story #{story_id}. Existing assets valid.", article_uuid=story_id)
            return s_dict, None


    log_event("STORY_GEN_DIAGNOSTIC", f"=== STARTED GENERATION ATTEMPT FOR STORY #{story_id} ===", article_uuid=story_id)

    # 2. Synthesize multi-source copy & exact 10 hashtags
    synth = synthesize_story_post_copy(story_obj)
    caption_res = "OK" if synth.get("caption") else "FAILED"
    hashtag_res = "OK" if synth.get("hashtags") else "FAILED"

    articles = s_dict.get("articles", [])
    primary_art = articles[0] if articles else {
        "title": synth["improved_headline"],
        "summary": synth["summary"],
        "source": s_dict.get("primary_source", "News"),
    }

    img_url = primary_art.get("image_url", "N/A")
    diag = {}
    try:
        img_path, diag = fetch_image(primary_art, return_diagnostics=True)
        download_res = f"OK ({img_path})"
    except OSError as e:
        img_path = "assets/fallback.png"
        download_res = f"FAILED ({e})"

    primary_art["title"] = synth["improved_headline"]
    primary_art["summary"] = synth["summary"]
    primary_art["caption"] = synth["caption"]
    primary_art["hashtags"] = synth["hashtags"]
    primary_art["uuid"] = story_id
    primary_art["image_local_path"] = img_path

    rendered_path, err = render_post_for_article(primary_art)
    renderer_res = f"OK ({rendered_path})" if (rendered_path and not err) else f"FAILED ({err})"
    
    video_path = None
    if rendered_path and not err:
        video_path = generate_static_reel(rendered_path, story_id)
    video_res = f"OK ({video_path})" if video_path else "FAILED"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_caption_file(story_id, synth["caption"])
    save_hashtags_file(story_id, synth["hashtags"])
    meta_path = save_article_json(s_dict, status="post_ready")
    metadata_res = f"OK ({meta_path})" if meta_path else "FAILED"

    # 3. TRANSACTIONAL 5-ASSET VALIDATION (Bug #7)
    is_valid, missing_assets = validate_story_assets(story_id, rendered_path, status="post_ready")
    duration = round(time.time() - start_time, 2)

    if is_valid:
        s_dict["rendered_image_path"] = rendered_path
        s_dict["caption"] = synth["caption"]
        s_dict["hashtags"] = synth["hashtags"]
        s_dict["status"] = "post_ready"
        s_dict["generated_time"] = now_str

        if hasattr(story_obj, "status"):
            story_obj.status = "post_ready"
            story_obj.rendered_image_path = rendered_path
            story_obj.caption = synth["caption"]
            story_obj.hashtags = synth["hashtags"]
            story_obj.generated_time = now_str

        insert_or_update_story(story_obj)

        # Construct and log comprehensive diagnostics
        diag_log = (
            f"=== COMPREHENSIVE IMAGE DIAGNOSTICS ===\n"
            f"Article UUID: {story_id}\n"
            f"Source: {s_dict.get('primary_source', 'News')}\n"
            f"Original image URL: {diag.get('original_image_url', img_url)}\n"
            f"HTTP status code: {diag.get('http_status_code')}\n"
            f"Download success: {diag.get('download_success', False)}\n"
            f"PIL image validation success: {diag.get('pil_validation_success', False)}\n"
            f"Image width: {diag.get('image_width')}\n"
            f"Image height: {diag.get('image_height')}\n"
            f"Saved image path: {diag.get('saved_image_path', img_path)}\n"
            f"Renderer input path: {img_path}\n"
            f"Renderer output path: {rendered_path}\n"
            f"Final background used: {diag.get('final_background_used', 'Fallback')}\n"
            f"Generation success: True\n"
            f"Preview path: {rendered_path}\n"
            f"Preview exists?: True"
        )
        log_event("IMAGE_DIAGNOSTICS", diag_log, article_uuid=story_id)

        log_event(
            "STORY_GEN_DIAGNOSTIC",
            f"DIAGNOSTIC SUMMARY: Story ID={story_id} | Image URL={str(img_url)[:40]} | Download={download_res} | Renderer={renderer_res} | Video={video_res} | Caption={caption_res} | Hashtag={hashtag_res} | Metadata={metadata_res} | Overall Status=POST_READY | Time Taken={duration}s",
            article_uuid=story_id
        )
        return s_dict, None

    else:
        # Atomic Rollback: Revert to 'new'
        s_dict["status"] = "new"
        if hasattr(story_obj, "status"):
            story_obj.status = "new"
        
        save_article_json(s_dict, status="new")
        insert_or_update_story(story_obj)

        error_msg = f"Transactional validation failed. Missing required assets: {', '.join(missing_assets)}"
        if err:
            error_msg += f" | Renderer Error: {err}"
        
        # Construct and log comprehensive diagnostics on failure
        diag_log = (
            f"=== COMPREHENSIVE IMAGE DIAGNOSTICS ===\n"
            f"Article UUID: {story_id}\n"
            f"Source: {s_dict.get('primary_source', 'News')}\n"
            f"Original image URL: {diag.get('original_image_url', img_url)}\n"
            f"HTTP status code: {diag.get('http_status_code')}\n"
            f"Download success: {diag.get('download_success', False)}\n"
            f"PIL image validation success: {diag.get('pil_validation_success', False)}\n"
            f"Image width: {diag.get('image_width')}\n"
            f"Image height: {diag.get('image_height')}\n"
            f"Saved image path: {diag.get('saved_image_path', img_path)}\n"
            f"Renderer input path: {img_path}\n"
            f"Renderer output path: {rendered_path}\n"
            f"Final background used: {diag.get('final_background_used', 'Fallback')}\n"
            f"Generation success: False\n"
            f"Preview path: {rendered_path}\n"
            f"Preview exists?: False"
        )
        log_event("IMAGE_DIAGNOSTICS", diag_log, article_uuid=story_id, level="ERROR")
        
        log_event(
            "STORY_GEN_DIAGNOSTIC",
            f"DIAGNOSTIC SUMMARY: Story ID={story_id} | Image URL={img_url[:40]} | Download={download_res} | Renderer={renderer_res} | Video={video_res} | Caption={caption_res} | Hashtag={hashtag_res} | Metadata={metadata_res} | Overall Status=REVERTED_TO_NEW | Error={error_msg} | Time Taken={duration}s",
            article_uuid=story_id,
            level="ERROR"
        )
        return s_dict, error_msg



def handle_reset_story_render(story_obj):
    import os
    s_dict = story_obj.to_dict() if hasattr(story_obj, 'to_dict') else story_obj
    story_id = s_dict.get("story_id")
    existing_render = s_dict.get("rendered_image_path")
    if existing_render and os.path.exists(existing_render):
        try:
            os.remove(existing_render)
        except Exception:
            pass
    s_dict["rendered_image_path"] = None
    if hasattr(story_obj, "rendered_image_path"):
        story_obj.rendered_image_path = None
    transition_article_status(s_dict, "new")

