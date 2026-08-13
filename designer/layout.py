from PIL import ImageFont, ImageDraw, Image
from designer.typography import calculate_headline_font_size
from designer.template import (
    WIDTH,
    HEIGHT,
    FONTS,
    HEADLINE_CONFIG,
    SUMMARY_CONFIG,
    META_CONFIG,
    FOOTER_CONFIG,
    GRADIENT_CONFIG,
    ADAPTIVE_OVERLAY_CONFIG,
)


class LayoutPlan:
    """
    Data object holding all precomputed coordinates, font sizes, text line splits,
    summary length, and adaptive overlay boosts for rendering.
    """
    def __init__(
        self,
        headline_start_y,
        headline_font_size,
        headline_lines,
        headline_bottom_y,
        summary_text,
        summary_y,
        summary_bottom_y,
        meta_y,
        footer_divider_y,
        alpha_boost,
        top_overlay_alpha,
    ):
        self.headline_start_y = headline_start_y
        self.headline_font_size = headline_font_size
        self.headline_lines = headline_lines
        self.headline_bottom_y = headline_bottom_y
        self.summary_text = summary_text
        self.summary_y = summary_y
        self.summary_bottom_y = summary_bottom_y
        self.meta_y = meta_y
        self.footer_divider_y = footer_divider_y
        self.alpha_boost = alpha_boost
        self.top_overlay_alpha = top_overlay_alpha


class LayoutEngine:
    """
    Calculates dynamic element placement, font sizes, optical line balancing,
    and adaptive summary space fitting without any hardcoded element positioning.
    """
    def __init__(self, template_config=None):
        self.dummy_canvas = Image.new("RGBA", (WIDTH, HEIGHT))
        self.draw = ImageDraw.Draw(self.dummy_canvas)

    def calculate_layout(self, article, image_metrics, canvas_faces=None):
        # 1. Headline Landing Y position based on face safe zones
        default_y = HEADLINE_CONFIG["default_y"]
        headline_y = default_y

        if canvas_faces:
            for (face_top, face_bottom) in canvas_faces:
                if face_top < default_y + 150 and face_bottom > default_y - 50:
                    if (face_top + face_bottom) / 2.0 < default_y:
                        headline_y = HEADLINE_CONFIG["max_y"]
                    else:
                        headline_y = HEADLINE_CONFIG["min_y"]
                    break

        # 2. Dynamic Headline Font Scaling & Line Balancing
        title_text = str(article.get("title") or "").strip()
        headline_font_size, headline_lines = calculate_headline_font_size(
            title_text,
            FONTS["bold"],
            self.draw,
            HEADLINE_CONFIG
        )

        headline_font = ImageFont.truetype(FONTS["bold"], headline_font_size)
        padding_y = HEADLINE_CONFIG["padding_y"]
        line_gap = HEADLINE_CONFIG["line_gap"]

        current_y = headline_y
        _, ref_top, _, ref_bottom = self.draw.textbbox((0, 0), "Ayjp", font=headline_font)
        uniform_height = ref_bottom - ref_top

        for line in headline_lines:
            current_y += (uniform_height + padding_y * 2 + line_gap)
        headline_bottom_y = current_y

        # 3. Dynamic Summary Space Solver
        summary_y = headline_bottom_y + SUMMARY_CONFIG["offset_y"]
        meta_y_reserved = META_CONFIG["font_size"] + META_CONFIG["offset_y"]
        footer_y = FOOTER_CONFIG["divider_y"]
        safety_gap = 25

        available_summary_h = max(60, footer_y - summary_y - meta_y_reserved - safety_gap)

        summary_font_size = SUMMARY_CONFIG["font_size"]
        summary_font = ImageFont.truetype(FONTS["regular"], summary_font_size)
        bbox_sample = self.draw.textbbox((0, 0), "Ag", font=summary_font)
        line_h = (bbox_sample[3] - bbox_sample[1]) + SUMMARY_CONFIG["line_spacing"]

        max_summary_lines = max(1, available_summary_h // line_h)

        # Fit summary text words within available_summary_h
        raw_summary = str(article.get("summary") or "").strip()
        import re
        raw_summary = re.sub(r'<[^>]+>', '', raw_summary)
        words = raw_summary.split()

        fitted_lines = []
        curr_line = ""
        word_idx = 0
        truncated = False

        while word_idx < len(words):
            word = words[word_idx]
            test_line = word if not curr_line else f"{curr_line} {word}"
            w_box = self.draw.textbbox((0, 0), test_line, font=summary_font)[2]

            if w_box <= SUMMARY_CONFIG["width"]:
                curr_line = test_line
                word_idx += 1
            else:
                if curr_line:
                    fitted_lines.append(curr_line)
                    curr_line = ""
                else:
                    fitted_lines.append(word)
                    word_idx += 1

                if len(fitted_lines) >= max_summary_lines:
                    truncated = True
                    break

        if curr_line and len(fitted_lines) < max_summary_lines:
            fitted_lines.append(curr_line)
        elif curr_line:
            truncated = True

        final_summary_text = " ".join(fitted_lines)
        if truncated or word_idx < len(words):
            final_summary_text = final_summary_text.rstrip(".,!?") + "..."

        actual_summary_h = len(fitted_lines) * line_h
        summary_bottom_y = summary_y + actual_summary_h

        # 4. Metadata Position
        meta_y = summary_bottom_y + META_CONFIG["offset_y"]

        # 5. Adaptive Overlay Boost from Image Luminance & Busyness
        brightness = image_metrics.get("brightness", 100.0)
        busyness = image_metrics.get("busyness", 10.0)

        lum_diff = brightness - ADAPTIVE_OVERLAY_CONFIG["target_luminance"]
        alpha_boost = lum_diff * 0.4

        if busyness > ADAPTIVE_OVERLAY_CONFIG["busyness_threshold"]:
            alpha_boost += ADAPTIVE_OVERLAY_CONFIG["busyness_alpha_boost"]

        min_boost = ADAPTIVE_OVERLAY_CONFIG["min_alpha_boost"]
        max_boost = ADAPTIVE_OVERLAY_CONFIG["max_alpha_boost"]
        alpha_boost = float(max(min_boost, min(max_boost, alpha_boost)))

        top_alpha = GRADIENT_CONFIG["base_top_alpha"] + (alpha_boost * 0.5)
        top_overlay_alpha = int(max(20, min(80, top_alpha)))

        return LayoutPlan(
            headline_start_y=headline_y,
            headline_font_size=headline_font_size,
            headline_lines=headline_lines,
            headline_bottom_y=headline_bottom_y,
            summary_text=final_summary_text,
            summary_y=summary_y,
            summary_bottom_y=summary_bottom_y,
            meta_y=meta_y,
            footer_divider_y=footer_y,
            alpha_boost=alpha_boost,
            top_overlay_alpha=top_overlay_alpha,
        )
