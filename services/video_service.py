import os
import subprocess
from settings import BASE_DIR
from services.logging_service import log_event

REEL_DURATION_SECONDS = 10

def generate_static_reel(png_path, article_uuid):
    """
    Converts a static 1080x1920 PNG into a static MP4 video using FFmpeg.
    Ensures optimal encoding for social media.
    Returns the path to the generated MP4 file or None if it fails.
    """
    if not png_path or not os.path.exists(png_path):
        log_event("VIDEO_GEN_FAILED", f"Source PNG missing: {png_path}", article_uuid=article_uuid, level="ERROR")
        return None

    # Derive output MP4 path from the PNG path
    mp4_path = png_path.replace(".png", ".mp4")
    
    # FFmpeg command to loop a single image for REEL_DURATION_SECONDS
    cmd = [
        "ffmpeg",
        "-y",               # Overwrite output files without asking
        "-loop", "1",       # Loop the single image
        "-i", png_path,     # Input image
        "-c:v", "libx264",  # Video codec
        "-t", str(REEL_DURATION_SECONDS), # Duration
        "-pix_fmt", "yuv420p", # Pixel format (highly recommended for social media compatibility)
        "-vf", "scale=1080:1920", # Ensure exact dimensions just in case
        mp4_path
    ]

    try:
        log_event("VIDEO_GEN_START", f"Starting FFmpeg MP4 generation for {REEL_DURATION_SECONDS}s", article_uuid=article_uuid)
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 1000:
            log_event("VIDEO_GEN_SUCCESS", f"Generated MP4: {mp4_path}", article_uuid=article_uuid)
            return os.path.abspath(mp4_path)
        else:
            log_event("VIDEO_GEN_FAILED", "FFmpeg completed but output file is missing or too small", article_uuid=article_uuid, level="ERROR")
            return None

    except subprocess.CalledProcessError as e:
        err_out = e.stderr or e.stdout
        log_event("VIDEO_GEN_ERROR", f"FFmpeg error: {err_out}", article_uuid=article_uuid, level="ERROR")
        return None
    except Exception as e:
        log_event("VIDEO_GEN_ERROR", f"Exception during video generation: {str(e)}", article_uuid=article_uuid, level="ERROR")
        return None
