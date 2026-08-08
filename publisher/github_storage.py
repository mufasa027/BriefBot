import os
import json
import base64
import requests


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # e.g., "mufasa027/BriefBot" or "user/repo"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")


def get_raw_github_url(repo_file_path):
    """
    Returns the public raw.githubusercontent.com URL for a given repository path.
    """
    if not GITHUB_REPO:
        return None
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{repo_file_path}"


def upload_file_to_github(repo_file_path, file_content_bytes, commit_message):
    """
    Uploads or updates a file in GitHub repository using GitHub REST API.
    Remains 100% FREE using standard GitHub Personal Access Tokens.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        err = f"GitHub Storage sync skipped (GITHUB_TOKEN or GITHUB_REPO not set). Saved locally to {repo_file_path}"
        print(f"[Notice] {err}")
        return False, err

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_file_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Check if file already exists to get SHA for update
    sha = None
    r_get = requests.get(url, headers=headers)
    if r_get.status_code == 200:
        sha = r_get.json().get("sha")

    encoded_content = base64.b64encode(file_content_bytes).decode("utf-8")

    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }
    if sha:
        payload["sha"] = sha

    r_put = requests.put(url, headers=headers, json=payload)
    if r_put.status_code in [200, 201]:
        print(f"[OK] Synced to GitHub Storage: {repo_file_path}")
        return True, None
    else:
        err = f"GitHub upload failed ({r_put.status_code}): {r_put.text[:100]}"
        print(f"[Error] {err}")
        return False, err


def sync_approved_post_to_github(article):
    """
    Commits approved post PNG image, JSON metadata, and caption text file to GitHub.
    """
    article_id = article.get("id") or article.get("title", "")[:20].replace(" ", "_")
    image_path = article.get("rendered_image_path")

    # 1. Sync Rendered PNG Image
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        upload_file_to_github(
            repo_file_path=f"storage/images/post_{article_id}.png",
            file_content_bytes=img_bytes,
            commit_message=f"storage: Add post PNG image for article #{article_id}"
        )

    # 1.5. Sync Rendered MP4 Video (if exists)
    mp4_path = image_path.replace(".png", ".mp4") if image_path else None
    mp4_repo_path = f"storage/videos/post_{article_id}.mp4"
    mp4_public_url = None
    
    if mp4_path and os.path.exists(mp4_path):
        with open(mp4_path, "rb") as f:
            video_bytes = f.read()
        success, err = upload_file_to_github(
            repo_file_path=mp4_repo_path,
            file_content_bytes=video_bytes,
            commit_message=f"storage: Add post MP4 video for article #{article_id}"
        )
        if success:
            mp4_public_url = get_raw_github_url(mp4_repo_path)
        else:
            return None, err

    # 2. Sync Metadata JSON
    json_bytes = json.dumps(article, indent=2, default=str).encode("utf-8")
    upload_file_to_github(
        repo_file_path=f"storage/json/article_{article_id}.json",
        file_content_bytes=json_bytes,
        commit_message=f"storage: Add article JSON metadata for #{article_id}"
    )

    # 3. Sync Caption Text
    caption_content = f"{article.get('caption', '')}\n\n{article.get('hashtags', '')}"
    upload_file_to_github(
        repo_file_path=f"storage/captions/caption_{article_id}.txt",
        file_content_bytes=caption_content.encode("utf-8"),
        commit_message=f"storage: Add caption text for #{article_id}"
    )

    return mp4_public_url, None
