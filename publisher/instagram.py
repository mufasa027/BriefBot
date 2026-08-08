import os
import time
import requests


INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
GRAPH_API_VERSION = "v19.0"


def publish_reel_to_instagram(video_public_url, caption_text):
    """
    Publishes an MP4 video to Instagram Reels.
    Step A: Create Media Container (media_type=REELS)
    Step B: Poll Meta servers until container status is FINISHED
    Step C: Publish Media Container
    """
    from settings import INSTAGRAM_PUBLISH_MODE
    if INSTAGRAM_PUBLISH_MODE == "TEST":
        print("[Notice] TEST MODE: Bypassing actual Instagram Reels publishing.")
        return "test_mock_ig_reel_id_9999", None

    if not INSTAGRAM_ACCOUNT_ID or not INSTAGRAM_ACCESS_TOKEN:
        err = "Instagram Graph API skipped (Credentials missing)."
        print(f"[Error] {err}")
        return None, err

    base_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_ACCOUNT_ID}"

    # Step A: Create Media Container
    container_payload = {
        "media_type": "REELS",
        "video_url": video_public_url,
        "caption": caption_text,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    r_container = requests.post(f"{base_url}/media", data=container_payload)
    if r_container.status_code != 200:
        err = f"Failed to create Instagram Reels container: {r_container.text}"
        print(f"[Error] {err}")
        return None, err

    creation_id = r_container.json().get("id")
    print(f"[OK] Instagram Reels container created: {creation_id}")

    # Step B: Poll for FINISHED status
    max_attempts = 12  # up to 60 seconds
    for attempt in range(max_attempts):
        time.sleep(5)
        r_status = requests.get(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}",
            params={"fields": "status_code", "access_token": INSTAGRAM_ACCESS_TOKEN}
        )
        if r_status.status_code == 200:
            status_code = r_status.json().get("status_code")
            if status_code == "FINISHED":
                print("[OK] Reels container processed successfully.")
                break
            elif status_code == "ERROR":
                err = "Reels container processing failed on Meta's end."
                print(f"[Error] {err}")
                return None, err
            else:
                print(f"[Wait] Container status: {status_code}...")
        else:
            err = f"Failed to check status: {r_status.text}"
            print(f"[Error] {err}")
            return None, err
    else:
        err = "Reels container processing timed out."
        print(f"[Error] {err}")
        return None, err

    # Step C: Publish Container
    publish_payload = {
        "creation_id": creation_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    r_publish = requests.post(f"{base_url}/media_publish", data=publish_payload)

    if r_publish.status_code == 200:
        post_id = r_publish.json().get("id")
        print(f"[OK] Published Reel to Instagram! Post ID: {post_id}")
        return post_id, None
    else:
        err = f"Instagram Reel publish failed: {r_publish.text}"
        print(f"[Error] {err}")
        return None, err

