import os
import time
import requests


INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
GRAPH_API_VERSION = "v19.0"


def publish_to_instagram(image_public_url, caption_text):
    """
    Publishes an image post to Instagram using official Meta Instagram Graph API containers.
    Step A: Create Media Container (POST /{ig-user-id}/media)
    Step B: Publish Media Container (POST /{ig-user-id}/media_publish)
    """
    if not INSTAGRAM_ACCOUNT_ID or not INSTAGRAM_ACCESS_TOKEN:
        print("[Notice] Instagram Graph API skipped (INSTAGRAM_ACCOUNT_ID or INSTAGRAM_ACCESS_TOKEN missing).")
        return None

    base_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_ACCOUNT_ID}"

    # Step A: Create Media Container
    container_payload = {
        "image_url": image_public_url,
        "caption": caption_text,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    r_container = requests.post(f"{base_url}/media", data=container_payload)

    if r_container.status_code != 200:
        print(f"[Error] Failed to create Instagram container ({r_container.status_code}): {r_container.text}")
        return None

    creation_id = r_container.json().get("id")
    print(f"[OK] Instagram container created: {creation_id}")

    # Short delay for Meta server processing
    time.sleep(3)

    # Step B: Publish Container
    publish_payload = {
        "creation_id": creation_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    r_publish = requests.post(f"{base_url}/media_publish", data=publish_payload)

    if r_publish.status_code == 200:
        post_id = r_publish.json().get("id")
        print(f"[OK] Published to Instagram successfully! Post ID: {post_id}")
        return post_id
    else:
        print(f"[Error] Instagram publish failed ({r_publish.status_code}): {r_publish.text}")
        return None
