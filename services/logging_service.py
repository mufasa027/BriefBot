import os
import logging
from datetime import datetime

LOGS_DIR = os.path.join("data", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

SYSTEM_LOG_PATH = os.path.join(LOGS_DIR, "system.log")

# Configure root logger
logger = logging.getLogger("CipherBrief")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(SYSTEM_LOG_PATH, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))

if not logger.handlers:
    logger.addHandler(file_handler)


def log_event(event_type, message, article_uuid=None, level="INFO"):
    """
    Logs structured backend actions to system.log and individual article log files.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    uuid_str = f" [UUID: {article_uuid}]" if article_uuid else ""
    formatted_msg = f"[{event_type}]{uuid_str} {message}"

    if level == "ERROR":
        logger.error(formatted_msg)
    elif level == "WARNING":
        logger.warning(formatted_msg)
    else:
        logger.info(formatted_msg)

    # If article_uuid provided, append to article-specific log file
    if article_uuid:
        art_log_path = os.path.join(LOGS_DIR, f"article_{article_uuid}.log")
        try:
            with open(art_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{level}] [{event_type}] {message}\n")
        except OSError:
            pass


def get_recent_logs(limit=50):
    """
    Retrieves recent log entries from system.log.
    """
    if not os.path.exists(SYSTEM_LOG_PATH):
        return []
    try:
        with open(SYSTEM_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-limit:]
    except OSError:
        return []

def get_audit_log_for_story(story_id):
    """
    Parses the article-specific log file and returns a list of formatted audit strings.
    Example line: [15:36:25] [INFO] [RENDER_SUCCESS] Story rendered
    Returns: ['15:36 - Story rendered']
    """
    art_log_path = os.path.join(LOGS_DIR, f"article_{story_id}.log")
    if not os.path.exists(art_log_path):
        return ["No audit logs available for this story."]
    
    parsed_logs = []
    try:
        with open(art_log_path, "r", encoding="utf-8") as f:
            for line in f:
                # Basic parsing to extract time and message
                # Expected format: [HH:MM:SS] [LEVEL] [EVENT] Message
                parts = line.split("] ", 3)
                if len(parts) >= 3:
                    time_part = parts[0].strip("[")
                    time_short = time_part[:5] # "HH:MM"
                    message = parts[-1].strip()
                    parsed_logs.append(f"{time_short} - {message}")
                else:
                    parsed_logs.append(line.strip())
        return parsed_logs if parsed_logs else ["No events recorded."]
    except OSError:
        return ["Error reading audit logs."]
