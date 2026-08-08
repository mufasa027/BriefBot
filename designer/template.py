# ========================================================
# BRIEFBOT DESIGN SYSTEM & TEMPLATE CONFIGURATION
# ========================================================

WIDTH = 1080
HEIGHT = 1920

# Primary Image Area
IMAGE = {
    "x": 0,
    "y": 0,
    "width": 1080,
    "height": 1575,
}

# Color Palette (RGB / RGBA tuples)
COLORS = {
    "white": (255, 255, 255),
    "yellow": (255, 214, 0),
    "gray": (170, 170, 170),
    "dark_gray": (175, 175, 180),
    "black": (0, 0, 0),
    "background": (11, 12, 14, 255),
    "footer_divider": (255, 255, 255, 30),
}

import os
from settings import BASE_DIR

# TrueType Font Paths
FONTS = {
    "bold": os.path.join(BASE_DIR, "assets", "fonts", "Roboto-Bold.ttf"),
    "regular": os.path.join(BASE_DIR, "assets", "fonts", "Roboto-Regular.ttf"),
}

# Headline Configuration & Box Layout
HEADLINE_CONFIG = {
    "x": 60,
    "default_y": 960,
    "min_y": 880,
    "max_y": 1040,
    "max_width": 880,
    "font_size": 62,
    "min_font_size": 50,
    "max_font_size": 72,
    "target_min_lines": 2,
    "target_max_lines": 4,
    "padding_x": 16,
    "padding_y": 8,
    "box_radius": 8,
    "line_gap": 14,
    "max_lines": 4,
}

# Summary Configuration
SUMMARY_CONFIG = {
    "x": 60,
    "offset_y": 18,
    "width": 920,
    "font_size": 40,
    "min_font_size": 32,
    "line_spacing": 10,
    "max_height": 220,
    "max_chars": 200,
}

# Metadata Configuration
META_CONFIG = {
    "x": 60,
    "offset_y": 16,
    "font_size": 22,
    "color": (175, 175, 180),
}

# Gradient & Overlay System
GRADIENT_CONFIG = {
    "fade_start_y": 650,
    "fade_end_y": 1620,
    "base_top_alpha": 40,
    "dither_amplitude": 0.5,
}

# Adaptive Color & Luminance System
ADAPTIVE_OVERLAY_CONFIG = {
    "roi_y_start": 650,
    "roi_y_end": 1575,
    "target_luminance": 110,
    "min_alpha_boost": -15,
    "max_alpha_boost": 45,
    "busyness_threshold": 12.0,
    "busyness_alpha_boost": 15,
}

# Footer System
FOOTER_CONFIG = {
    "divider_y": 1680,
    "divider_margin_x": 60,
    "logo_path": "assets/logo.png",
    "logo_x": 60,
    "logo_y": 1710,
    "logo_size": 72,
    "handle_text": "@cipherbrief",
    "handle_offset_x": 18,
    "handle_offset_y": 4,
    "handle_font_size": 32,
    "tagline_text": "Stay Informed",
    "tagline_offset_y": 42,
    "tagline_font_size": 18,
    "source_y": 1845,
    "source_font_size": 22,
    "source_prefix": "SOURCE: ",
    "source_color": COLORS["yellow"],
}

# Legacy Compatibility Definitions
HEADLINE = {
    "x": HEADLINE_CONFIG["x"],
    "y": HEADLINE_CONFIG["default_y"],
    "width": HEADLINE_CONFIG["max_width"],
    "font_size": HEADLINE_CONFIG["font_size"],
    "line_spacing": HEADLINE_CONFIG["line_gap"],
    "max_height": 260,
}

SUBHEAD = {
    "x": SUMMARY_CONFIG["x"],
    "y": 0,
    "width": SUMMARY_CONFIG["width"],
    "font_size": SUMMARY_CONFIG["font_size"],
    "line_spacing": SUMMARY_CONFIG["line_spacing"],
    "max_height": SUMMARY_CONFIG["max_height"],
}

MICROTEXT = {
    "x": META_CONFIG["x"],
    "y": 0,
    "width": 900,
    "font_size": META_CONFIG["font_size"],
    "line_spacing": 4,
    "max_height": 40,
}

SOURCE = {
    "x": 60,
    "y": FOOTER_CONFIG["source_y"],
    "width": 350,
    "font_size": FOOTER_CONFIG["source_font_size"],
}

LOGO = {
    "x": FOOTER_CONFIG["logo_x"],
    "y": FOOTER_CONFIG["logo_y"],
    "size": FOOTER_CONFIG["logo_size"],
}

HANDLE = {
    "x": FOOTER_CONFIG["logo_x"] + FOOTER_CONFIG["logo_size"] + FOOTER_CONFIG["handle_offset_x"],
    "y": FOOTER_CONFIG["logo_y"] + FOOTER_CONFIG["handle_offset_y"],
    "font_size": FOOTER_CONFIG["handle_font_size"],
}
