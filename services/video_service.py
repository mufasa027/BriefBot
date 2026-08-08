import os
import subprocess
from settings import BASE_DIR, REEL_DURATION_SECONDS
from services.logging_service import log_event


def generate_static_reel(png_path, article_uuid):
    """
    Converts a static 1080x1920 PNG into a static MP4 video using FFmpeg.
    Ensures optimal encoding for Instagram Reels.
    Returns a tuple: (mp4_path, error_message).
    """
    if not png_path or not os.path.exists(png_path):
        err = f"Source PNG missing: {png_path}"
        log_event("VIDEO_GEN_FAILED", err, article_uuid=article_uuid, level="ERROR")
        return None, err

    # Derive output MP4 path from the PNG path
    mp4_path = png_path.replace(".png", ".mp4")
    
    # Example: ffmpeg -loop 1 -i input.png -c:v libx264 -t 5 -pix_fmt yuv420p output.mp4
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
            log_event("VIDEO_GEN_SUCCESS", f"Generated Reel MP4: {mp4_path}", article_uuid=article_uuid)
            return os.path.abspath(mp4_path), None
        else:
            err = "FFmpeg completed but output file is missing or too small."
            log_event("VIDEO_GEN_FAILED", err, article_uuid=article_uuid, level="ERROR")
            return None, err

    except subprocess.CalledProcessError as e:
        err_out = e.stderr or e.stdout
        err = f"FFmpeg error: {err_out}"
        log_event("VIDEO_GEN_ERROR", err, article_uuid=article_uuid, level="ERROR")
        return None, err
    except Exception as e:
        err = f"Exception during video generation: {str(e)}"
        log_event("VIDEO_GEN_ERROR", err, article_uuid=article_uuid, level="ERROR")
        return None, err
