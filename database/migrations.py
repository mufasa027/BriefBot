import os
import sys
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine
from database.models import Base
from settings import BASE_DIR, DATABASE_NAME

def create_database():
    """
    Robust database initialization designed to survive Streamlit Cloud environments.
    """
    print("==================================================")
    print("DATABASE INITIALIZATION SEQUENCE")
    print("==================================================")
    
    try:
        # 1. Determine directories reliably
        base_path = Path(BASE_DIR).resolve()
        db_path = Path(DATABASE_NAME).resolve()
        data_dir = db_path.parent
        
        print(f"Project Root (BASE_DIR): {base_path}")
        print(f"Data Directory: {data_dir}")
        print(f"Database Path: {db_path}")
        print(f"Current Working Directory: {Path.cwd()}")
        
        # 2. Create the parent directory if required
        if not data_dir.exists():
            print(f"Creating data directory: {data_dir}")
            data_dir.mkdir(parents=True, exist_ok=True)
        else:
            print(f"Data directory already exists: {data_dir}")
            
        # 3 & 4. Verify directory exists and is writable
        if not data_dir.exists():
            raise RuntimeError(f"FATAL: Failed to create data directory at {data_dir}")
            
        if not os.access(data_dir, os.W_OK):
            raise PermissionError(f"FATAL: The directory {data_dir} is NOT writable by the current user.")
            
        print("[OK] Directory is accessible and writable")
        
        # 5. Construct SQLAlchemy URL safely
        # Use as_posix() to ensure forward slashes, avoiding Windows path issues.
        # Adding three slashes plus an absolute posix path creates a robust URI on both OSes.
        db_uri = f"sqlite:///{db_path.as_posix()}"
        print(f"SQLAlchemy URI: {db_uri}")
        
        # 6. Create engine and test connection BEFORE create_all
        engine = create_engine(db_uri, echo=False, future=True)
        try:
            with engine.connect() as conn:
                print("[OK] Successfully connected to SQLite via SQLAlchemy")
        except Exception as e:
            raise RuntimeError(f"FATAL: Could not connect to the database via SQLAlchemy. {type(e).__name__}: {e}")
            
        # 7. Create schema
        print("Creating tables (if they do not exist)...")
        Base.metadata.create_all(bind=engine)
        print("[OK] Schema verified")

        # 8. Perform legacy schema migrations
        print("Performing schema migrations...")
        conn = sqlite3.connect(db_path.as_posix())
        try:
            cursor = conn.cursor()
            columns_to_add = [
                ("rendered_image_path", "TEXT"),
                ("caption", "TEXT"),
                ("hashtags", "TEXT"),
                ("generated_time", "TEXT"),
                ("approved_time", "TEXT"),
                ("rejected_time", "TEXT"),
                ("instagram_media_id", "TEXT"),
                ("reel_video_path", "TEXT"),
                ("publish_attempts", "INTEGER"),
                ("queued_time", "TEXT"),
                ("publishing_time", "TEXT"),
                ("published_time", "TEXT"),
                ("publish_error", "TEXT"),
                ("last_publish_attempt", "TEXT"),
            ]

            # Migrate news table
            cursor.execute("PRAGMA table_info(news)")
            news_cols = [row[1] for row in cursor.fetchall()]
            for col_name, col_type in columns_to_add:
                if col_name not in news_cols:
                    try:
                        cursor.execute(f"ALTER TABLE news ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        pass

            # Migrate stories table
            cursor.execute("PRAGMA table_info(stories)")
            story_cols = [row[1] for row in cursor.fetchall()]
            for col_name, col_type in columns_to_add:
                if col_name not in story_cols:
                    try:
                        cursor.execute(f"ALTER TABLE stories ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        pass

            conn.commit()
            print("[OK] Migrations completed successfully")
        finally:
            conn.close()
            
        print("==================================================")
        print("DATABASE INITIALIZATION SUCCESSFUL")
        print("==================================================")
        
    except Exception as e:
        print("\n==================================================")
        print("DATABASE INITIALIZATION FAILED")
        print("==================================================")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        import traceback
        traceback.print_exc()
        print("==================================================")
        # On Streamlit Cloud, printing to stdout is helpful, but we also raise so Streamlit halts
        # and displays the exact trace to the developer.
        raise RuntimeError(f"Database Initialization Failed: {e}") from e
