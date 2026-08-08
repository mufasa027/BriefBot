import sqlite3
from database.connection import engine
from database.models import Base
from config import DATABASE_NAME


def create_database():
    """
    Creates database tables if missing and safely migrates new columns to existing tables.
    Uses DATABASE_NAME from config to ensure migration targets the correct database file.
    """
    # Ensure the parent directory exists (critical for Streamlit Cloud deployment)
    import os
    os.makedirs(os.path.dirname(DATABASE_NAME), exist_ok=True)

    Base.metadata.create_all(bind=engine)

    # C-02 FIX: Use DATABASE_NAME from config instead of hardcoded "briefbot.db"
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        cursor = conn.cursor()

        columns_to_add = [
            ("rendered_image_path", "TEXT"),
            ("caption", "TEXT"),
            ("hashtags", "TEXT"),
            ("generated_time", "TEXT"),
            ("approved_time", "TEXT"),
            ("rejected_time", "TEXT"),
        ]

        # Migrate news table
        cursor.execute("PRAGMA table_info(news)")
        news_cols = [row[1] for row in cursor.fetchall()]
        for col_name, col_type in columns_to_add:
            if col_name not in news_cols:
                try:
                    cursor.execute(f"ALTER TABLE news ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

        # Migrate stories table
        # C-01 FIX: Target 'stories' table (was incorrectly targeting 'news' in original)
        cursor.execute("PRAGMA table_info(stories)")
        story_cols = [row[1] for row in cursor.fetchall()]
        for col_name, col_type in columns_to_add:
            if col_name not in story_cols:
                try:
                    cursor.execute(f"ALTER TABLE stories ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

        conn.commit()
    finally:
        conn.close()