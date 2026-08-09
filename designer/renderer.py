from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import os
import numpy as np

from designer.template import (
    WIDTH,
    HEIGHT,
    IMAGE,
    COLORS,
    FONTS,
    HEADLINE_CONFIG,
    SUMMARY_CONFIG,
    META_CONFIG,
    GRADIENT_CONFIG,
    FOOTER_CONFIG,
)
from designer.image import fit_image, get_cropped_face_positions, analyze_image_metrics
from designer.typography import draw_wrapped_text
from designer.layout import LayoutEngine
from services.image_fetcher import create_branded_fallback_image
from services.logging_service import log_event


def prepare_canvas(template_path=None):
    """
    Step 1: Initializes and returns a clean 1080x1920 RGBA canvas.
    """
    canvas_w, canvas_h = WIDTH, HEIGHT

    if template_path and os.path.exists(template_path):
        try:
            canvas = Image.open(template_path).convert("RGBA")
            if canvas.size != (canvas_w, canvas_h):
                canvas = canvas.resize((canvas_w, canvas_h), Image.LANCZOS)
            return canvas
        except Exception:
            pass
            
    return Image.new("RGBA", (canvas_w, canvas_h), COLORS["background"])


def prepare_image(canvas, image_path):
    """
    Step 2: Smart crops news photo and pastes onto canvas.
    Guarantees a valid background photo is ALWAYS pasted (uses fallback if missing or corrupted).
    """
    valid_path = image_path if (image_path and os.path.exists(image_path)) else None
    
    if not valid_path:
        fallback_path = create_branded_fallback_image()
        log_event("RENDERER_WARN", f"Provided image_path invalid ('{image_path}'). Using branded fallback background: {fallback_path}", level="WARNING")
        valid_path = fallback_path

    try:
        news_image = fit_image(valid_path, IMAGE)
        canvas.paste(news_image, (IMAGE["x"], IMAGE["y"]))
    except Exception as e:
        log_event("RENDERER_ERROR", f"fit_image failed on '{valid_path}' ({e}). Attempting direct fallback paste.", level="ERROR")
        try:
            fallback_path = create_branded_fallback_image()
            fb_img = Image.open(fallback_path).convert("RGB").resize((IMAGE["width"], IMAGE["height"]), Image.LANCZOS)
            canvas.paste(fb_img, (IMAGE["x"], IMAGE["y"]))
        except Exception as ex:
            log_event("RENDERER_CRITICAL", f"Fallback paste failed ({ex})", level="ERROR")

    return canvas


def layout_engine(canvas, article, image_path):
    """
    Step 3: Analyzes image metrics, calculates dynamic layout plan,
    and composites top overlay and dithered cinematic fade gradient.
    """
    text_roi = {"x": 60, "y_start": 650, "width": 920, "height": 925}
    image_metrics = analyze_image_metrics(canvas, text_roi)

    canvas_faces = []
    if image_path and os.path.exists(image_path):
        canvas_faces = get_cropped_face_positions(image_path, IMAGE["width"], IMAGE["height"])

    engine = LayoutEngine()
    plan = engine.calculate_layout(article, image_metrics, canvas_faces)

    # Composite Top Dark Overlay
    top_overlay = Image.new("RGBA", (canvas.width, IMAGE["height"]), (0, 0, 0, plan.top_overlay_alpha))
    canvas.alpha_composite(top_overlay, (0, 0))

    # Composite Anti-Aliased Dithered Cinematic Bottom Fade
    gradient_layer = generate_cinematic_fade(
        width=canvas.width,
        height=canvas.height,
        fade_start_y=GRADIENT_CONFIG["fade_start_y"],
        fade_end_y=GRADIENT_CONFIG["fade_end_y"],
        alpha_boost=plan.alpha_boost
    )
    canvas.alpha_composite(gradient_layer, (0, 0))

    return plan


def generate_cinematic_fade(width, height, fade_start_y, fade_end_y, alpha_boost=0):
    """
    Helper: Generates smooth Perlin quintic smoothstep gradient layer with subtle dithering.
    """
    fade_distance = max(1, fade_end_y - fade_start_y)
    y_indices = np.arange(height, dtype=np.float32)
    t = np.clip((y_indices - fade_start_y) / fade_distance, 0.0, 1.0)
    
    smooth_t = t * t * t * (t * (6.0 * t - 15.0) + 10.0)
    boosted_alpha = np.clip(smooth_t * 255.0 + (smooth_t * alpha_boost), 0.0, 255.0)
    
    alpha_2d = np.tile(boosted_alpha[:, np.newaxis], (1, width))
    dither = (np.random.rand(height, width) - 0.5) * GRADIENT_CONFIG["dither_amplitude"]
    final_alpha = np.clip(alpha_2d + dither, 0.0, 255.0).astype(np.uint8)
    
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[:, :, 3] = final_alpha
    
    return Image.fromarray(rgba, mode="RGBA")


def draw_headline(canvas, draw, article, layout_plan):
    """
    Step 4: Renders yellow rounded headline boxes with dynamically solved font size and balanced lines.
    """
    headline_font = ImageFont.truetype(FONTS["bold"], layout_plan.headline_font_size)
    start_x = HEADLINE_CONFIG["x"]
    current_y = layout_plan.headline_start_y

    padding_x = HEADLINE_CONFIG["padding_x"]
    padding_y = HEADLINE_CONFIG["padding_y"]
    box_radius = HEADLINE_CONFIG["box_radius"]
    line_gap = HEADLINE_CONFIG["line_gap"]

    # Calculate uniform vertical metrics for this specific font size
    # We use a string with max ascenders (A, h, l, d) and max descenders (y, j, p, g)
    _, ref_top, _, ref_bottom = draw.textbbox((0, 0), "Ayjp", font=headline_font)
    uniform_height = ref_bottom - ref_top

    for line in layout_plan.headline_lines:
        # Get exact horizontal bounds for this specific line
        left, _, right, _ = draw.textbbox((start_x, current_y), line, font=headline_font)

        # Calculate uniform box relative to current_y
        box_top = current_y + ref_top
        box_bottom = current_y + ref_bottom

        box_rect = (
            left - padding_x,
            box_top - padding_y,
            right + padding_x,
            box_bottom + padding_y,
        )

        draw.rounded_rectangle(
            box_rect,
            radius=box_radius,
            fill=COLORS["yellow"],
        )

        draw.text(
            (start_x, current_y),
            line,
            font=headline_font,
            fill=COLORS["black"],
        )

        current_y += (uniform_height + padding_y * 2 + line_gap)


def draw_summary(canvas, article, layout_plan):
    """
    Step 5: Renders dynamically fitted summary text.
    """
    summary_box = {
        "x": SUMMARY_CONFIG["x"],
        "y": layout_plan.summary_y,
        "width": SUMMARY_CONFIG["width"],
        "font_size": SUMMARY_CONFIG["font_size"],
        "line_spacing": SUMMARY_CONFIG["line_spacing"],
        "max_height": SUMMARY_CONFIG["max_height"],
    }

    return draw_wrapped_text(
        canvas,
        layout_plan.summary_text,
        summary_box,
        FONTS["regular"],
        COLORS["white"],
    )


def draw_metadata(canvas, draw, article, layout_plan):
    """
    Step 6: Renders category & date metadata tag.
    """
    category = (article.get("category") or "NEWS").upper()
    published = str(article.get("published") or "")
    date_str = published[:16] if published else ""
    
    meta_str = f"{category}  •  {date_str}" if date_str else category
    meta_font = ImageFont.truetype(FONTS["bold"], META_CONFIG["font_size"])

    draw.text(
        (META_CONFIG["x"], layout_plan.meta_y),
        meta_str,
        font=meta_font,
        fill=META_CONFIG["color"],
    )


def draw_footer(canvas, draw, article, layout_plan):
    """
    Step 7: Renders pixel-perfect footer.
    """
    canvas_w = canvas.width
    divider_y = FOOTER_CONFIG["divider_y"]
    margin_x = FOOTER_CONFIG["divider_margin_x"]

    # Divider line
    draw.line([(margin_x, divider_y), (canvas_w - margin_x, divider_y)], fill=COLORS["footer_divider"], width=1)

    logo_path = FOOTER_CONFIG["logo_path"]
    logo_size = FOOTER_CONFIG["logo_size"]
    logo_x = FOOTER_CONFIG["logo_x"]
    logo_y = FOOTER_CONFIG["logo_y"]

    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((logo_size, logo_size), Image.LANCZOS)
            canvas.alpha_composite(logo, (logo_x, logo_y))
        except Exception as e:
            print(f"Warning: Could not render logo ({e}).")

    text_x = logo_x + logo_size + FOOTER_CONFIG["handle_offset_x"]
    handle_font = ImageFont.truetype(FONTS["bold"], FOOTER_CONFIG["handle_font_size"])
    tagline_font = ImageFont.truetype(FONTS["regular"], FOOTER_CONFIG["tagline_font_size"])
    source_font = ImageFont.truetype(FONTS["bold"], FOOTER_CONFIG["source_font_size"])

    draw.text(
        (text_x, logo_y + FOOTER_CONFIG["handle_offset_y"]),
        FOOTER_CONFIG["handle_text"],
        font=handle_font,
        fill=COLORS["white"],
    )

    draw.text(
        (text_x, logo_y + FOOTER_CONFIG["tagline_offset_y"]),
        FOOTER_CONFIG["tagline_text"],
        font=tagline_font,
        fill=COLORS["gray"],
    )

    source_name = (article.get("source") or "BriefBot").strip()
    source_str = f"{FOOTER_CONFIG['source_prefix']}{source_name.upper()}"

    src_bbox = draw.textbbox((0, 0), source_str, font=source_font)
    src_w = src_bbox[2] - src_bbox[0]
    src_x = (canvas_w - src_w) // 2
    src_y = FOOTER_CONFIG["source_y"]

    draw.text(
        (src_x, src_y),
        source_str,
        font=source_font,
        fill=FOOTER_CONFIG["source_color"],
    )


def export(canvas, output_path):
    """
    Step 8: Enhances contrast/sharpness and exports PNG image.
    """
    enhanced = ImageEnhance.Contrast(canvas).enhance(1.04)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.10)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    enhanced.save(output_path, format="PNG")
    return output_path


def render(article, image_path, template_path=None, output_path="output/final_post.png"):
    """
    Main entry point: Executes the 8-step modular rendering pipeline.
    """
    canvas = prepare_canvas(template_path)
    canvas = prepare_image(canvas, image_path)
    plan = layout_engine(canvas, article, image_path)
    
    draw = ImageDraw.Draw(canvas)
    
    draw_headline(canvas, draw, article, plan)
    draw_summary(canvas, article, plan)
    draw_metadata(canvas, draw, article, plan)
    draw_footer(canvas, draw, article, plan)
    
    return export(canvas, output_path)
