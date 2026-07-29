# ==========================================
# BriefBot Configuration
# ==========================================

APP_NAME = "BriefBot"
VERSION = "1.0.0"

# ==========================================
# Database
# ==========================================

DATABASE_NAME = "briefbot.db"

# ==========================================
# News Collection
# ==========================================

FETCH_INTERVAL = 15  # Minutes

MAX_ARTICLES = 100

RSS_FEEDS = {
    "BBC": "https://feeds.bbci.co.uk/news/rss.xml",
    "Reuters World": "https://feeds.reuters.com/Reuters/worldNews",
    "AP News": "https://apnews.com/hub/ap-top-news/rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml"
}

# ==========================================
# Logging
# ==========================================

LOG_FOLDER = "logs"

# ==========================================
# Output
# ==========================================

OUTPUT_FOLDER = "output"