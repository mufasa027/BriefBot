import os
import subprocess
from settings import BASE_DIR
from services.logging_service import log_event
from services.audio_manager import get_next_audio_track

def generate_static_reel(png_path, article_uuid, duration=10, motion="NONE"):
    """
    Converts a static 1080x1920 PNG into an MP4 video using FFmpeg.
    Supports dynamic durations and subtle Ken Burns zoom.
    """
    if not png_path or not os.path.exists(png_path):
        log_event("VIDEO_GEN_FAILED", f"Source PNG missing: {png_path}", article_uuid=article_uuid, level="ERROR")
        return None

    mp4_path = png_path.replace(".png", ".mp4")
    audio_path = get_next_audio_track(article_uuid)
    
    # Configure video filter based on motion
    if motion == "ZOOM_IN":
        # Subtle zoom from 1.0 to 1.1x over the duration
        # fps=25 is assumed by zoompan 'd' parameter
        vf_filter = f"zoompan=z='min(zoom+0.0015,1.1)':d={duration*25}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920"
    else:
        vf_filter = "scale=1080:1920"
    
    if audio_path:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", png_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", vf_filter,
            "-t", str(duration),
            "-shortest",
            mp4_path
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", png_path,
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-vf", vf_filter,
            mp4_path
        ]

    try:
        log_event("VIDEO_GEN_START", f"Starting FFmpeg MP4 generation for {duration}s, motion: {motion}", article_uuid=article_uuid)
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
