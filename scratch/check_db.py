import sqlite3

def check_db():
    conn = sqlite3.connect('data/briefbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT story_id, status, rendered_image_path, reel_video_path, publish_attempts, publish_error, instagram_media_id FROM stories WHERE status IN ('failed', 'publishing')")
    rows = cursor.fetchall()
    
    print("Failed or Publishing Stories:")
    for row in rows:
        print(f"story_id: {row[0]}")
        print(f"status: {row[1]}")
        print(f"rendered_image_path: {row[2]}")
        print(f"reel_video_path: {row[3]}")
        print(f"publish_attempts: {row[4]}")
        print(f"publish_error: {row[5]}")
        print(f"instagram_media_id: {row[6]}")
        print("-" * 40)

if __name__ == "__main__":
    check_db()
