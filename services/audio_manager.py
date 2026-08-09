import os
import json
import random
from services.logging_service import log_event

AUDIO_DIR = os.path.join("assets", "audio")
HISTORY_FILE = os.path.join("data", "logs", "audio_history.json")

# Ensure directories exist
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

def _load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def _save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def get_next_audio_track(article_uuid="N/A"):
    """
    Scans the AUDIO_DIR for valid tracks and randomly selects one that has
    not been used recently (keeps memory of up to 12 previous tracks).
    """
    valid_exts = {".mp3", ".wav", ".m4a"}
    tracks = []
    
    if os.path.exists(AUDIO_DIR):
        for f in os.listdir(AUDIO_DIR):
            if os.path.splitext(f)[1].lower() in valid_exts:
                tracks.append(f)
                
    if not tracks:
        return None  # No audio available
        
    history = _load_history()
    
    # Track selection logic
    available_tracks = [t for t in tracks if t not in history]
    
    if not available_tracks:
        # If all tracks have been used recently (e.g., user put less than 13 tracks),
        # fallback: clear the history so we can pick again, but avoid the very last track if possible
        if len(tracks) > 1 and history:
            available_tracks = [t for t in tracks if t != history[-1]]
        else:
            available_tracks = tracks
        
    selected_track = random.choice(available_tracks)
    
    # Update history
    history.append(selected_track)
    
    # Keep only the last 12
    if len(history) > 12:
        history = history[-12:]
        
    _save_history(history)
    
    selected_path = os.path.abspath(os.path.join(AUDIO_DIR, selected_track))
    log_event("AUDIO_SELECTED", f"Selected track: {selected_track}", article_uuid=article_uuid)
    return selected_path
