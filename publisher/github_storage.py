import os
import json
import base64
import requests


def get_github_env():
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO", "").replace(".git", "").strip() if os.getenv("GITHUB_REPO") else None
    branch = os.getenv("GITHUB_BRANCH", "").strip()
    return token, repo, branch


def get_raw_github_url(repo_file_path):
    """
    Returns the public raw.githubusercontent.com URL for a given repository path.
    """
    _, repo, branch = get_github_env()
    if not repo:
        return None
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{repo_file_path}"


def upload_file_to_github(repo_file_path, file_content_bytes, commit_message):
    """
    Uploads or updates a file in GitHub repository using GitHub REST API.
    Remains 100% FREE using standard GitHub Personal Access Tokens.
    """
    token, repo, branch = get_github_env()
    
    if not token or not repo:
        err = f"GitHub Storage sync skipped (GITHUB_TOKEN or GITHUB_REPO not set). Saved locally to {repo_file_path}"
        print(f"[Notice] {err}")
        return False, err

    import urllib.parse
    safe_path = urllib.parse.quote(repo_file_path)
    url = f"https://api.github.com/repos/{repo}/contents/{safe_path}"
    headers = {
        "Authorization": f"Bearer {token}",
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
        "content": encoded_content
    }
    if branch:
        payload["branch"] = branch
    if sha:
        payload["sha"] = sha

    r_put = requests.put(url, headers=headers, json=payload)
    if r_put.status_code in [200, 201]:
        print(f"[OK] Synced to GitHub Storage: {repo_file_path}")
        return True, None
    else:
        err = f"GitHub upload failed (404) for repo '{repo}', path '{safe_path}': {r_put.text[:100]}" if r_put.status_code == 404 else f"GitHub upload failed ({r_put.status_code}): {r_put.text[:100]}"
        print(f"[Error] {err}")
        return False, err


def sync_approved_post_to_github(article):
    """
    Commits approved post PNG image, JSON metadata, and caption text file to GitHub.
    """
    article_id = article.get("story_id") or article.get("id") or article.get("story_title", article.get("title", ""))[:20].replace(" ", "_")
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
