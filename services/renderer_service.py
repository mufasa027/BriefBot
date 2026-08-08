import os
from designer.renderer import render
from services.image_fetcher import fetch_image
from services.logging_service import log_event
from services.storage_service import get_or_create_article_uuid, get_render_path_for_uuid


def render_post_for_article(article):
    """
    Renders Instagram post PNG for an article using v1.0 rendering engine.
    Saves image to data/renders/post_<uuid>.png.
    Returns (rendered_path, error_message). Never raises uncaught exceptions.
    """
    art_uuid = get_or_create_article_uuid(article)
    out_path = get_render_path_for_uuid(art_uuid)

    image_path = article.get("image_local_path")
    if not image_path or not os.path.exists(image_path):
        try:
            image_path = fetch_image(article)
            article["image_local_path"] = image_path
        except Exception as e:
            log_event("IMAGE_FETCH_WARN", f"Failed fetching image ({e})", article_uuid=art_uuid, level="WARNING")
            image_path = "assets/fallback.png"

    log_event("RENDER_START", f"Rendering post PNG to {out_path}", article_uuid=art_uuid)

    try:
        rendered_path = render(
            article=article,
            image_path=image_path,
            template_path="assets/template.png",
            output_path=out_path
        )

        if rendered_path and os.path.exists(rendered_path):
            article["rendered_image_path"] = rendered_path
            log_event("RENDER_SUCCESS", f"Rendered post successfully: {rendered_path}", article_uuid=art_uuid)
            return rendered_path, None
        else:
            err = "Renderer produced no file output."
            log_event("RENDER_ERROR", err, article_uuid=art_uuid, level="ERROR")
            return None, err

    except Exception as e:
        err_msg = f"Render exception: {str(e)}"
        log_event("RENDER_EXCEPTION", err_msg, article_uuid=art_uuid, level="ERROR")
        return None, err_msg
