import os
import io
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFilter
from services.logging_service import log_event

MEDIA_DIR = "media"
ASSETS_DIR = "assets"
DEFAULT_BG_PATH = os.path.join(ASSETS_DIR, "fallback.png")

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)


def create_branded_fallback_image(output_path=None):
    """
    Generates a high-quality typographic editorial fallback background image (1080x1575)
    used when news photo downloads fail. Matches the new SVG aesthetic.
    """
    if output_path is None:
        output_path = DEFAULT_BG_PATH
        
    if os.path.exists(output_path):
        return output_path

    try:
        import random
        from PIL import ImageFont
        w, h = 1080, 1575
        base = Image.new("RGB", (w, h), (7, 9, 13)) # #07090D
        draw = ImageDraw.Draw(base)

        quotes = [
            "Peace begins with a smile.",
            "There is no path to peace. Peace is the path.",
            "Darkness cannot drive out darkness; only light can do that.",
            "We must learn to live together as brothers.",
            "PEACE", "UNITY", "HOPE", "TRUTH", "WORLD INTELLIGENCE"
        ]

        try:
            font_path = "assets/fonts/Roboto-Bold.ttf"
        except:
            font_path = None

        random.seed(42)
        for _ in range(30):
            q = random.choice(quotes)
            x = random.randint(-100, w + 100)
            y = random.randint(-100, h + 100)
            size = random.randint(20, 60)
            opacity = random.randint(5, 15)
            
            try:
                fnt = ImageFont.truetype(font_path, size)
            except:
                fnt = ImageFont.load_default()

            txt_img = Image.new('RGBA', (w, h), (0,0,0,0))
            d = ImageDraw.Draw(txt_img)
            d.text((x, y), q, font=fnt, fill=(255, 255, 255, opacity))
            
            if random.random() > 0.5:
                txt_img = txt_img.rotate(90, center=(x, y))
            
            base.paste(txt_img, (0,0), txt_img)

        base.save(output_path, quality=92)
        return output_path
    except Exception as e:
        print(f"Fallback generation error: {e}")
        return output_path


def scrape_article_image(url):
    """Fallback scraper to find og:image when RSS fails to provide one."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Try og:image
        og = soup.find('meta', property='og:image')
        if og and og.get('content'):
            return og['content']
            
        # Try twitter:image
        tw = soup.find('meta', {'name': 'twitter:image'})
        if tw and tw.get('content'):
            return tw['content']
    except Exception as e:
        pass
    return None


def download_valid_image(url, target_path, timeout=8):
    """
    Downloads image from URL, verifies PIL validity, and saves to target_path.
    Returns (success_boolean, reason_string, diagnostic_dict).
    """
    diag = {
        "http_status_code": None,
        "pil_validation_success": False,
        "image_width": None,
        "image_height": None
    }
    
    if not url or not str(url).startswith("http"):
        return False, "Invalid image URL format", diag

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        diag["http_status_code"] = resp.status_code
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code} status code", diag

        content_bytes = resp.content
        if len(content_bytes) < 2000:
            return False, "Downloaded payload too small (< 2KB)", diag

        # Verify image using PIL
        img = Image.open(io.BytesIO(content_bytes))
        img.verify()
        
        diag["pil_validation_success"] = True
        diag["image_width"] = img.width
        diag["image_height"] = img.height
        
        if img.width < 100 or img.height < 100:
            return False, f"Image dimensions too small ({img.width}x{img.height})", diag
        
        # Re-open and save validated image
        img = Image.open(io.BytesIO(content_bytes)).convert("RGB")
        img.save(target_path, quality=90)
        return True, "Success", diag

    except requests.exceptions.Timeout:
        return False, "Connection timeout", diag
    except Exception as e:
        return False, f"Download/PIL exception ({str(e)})", diag


def fetch_image(article, return_diagnostics=False):
    """
    Robust multi-candidate image downloader.
    Attempts primary image_url, Newspaper candidate images, and falls back
    to branded CipherBrief default background if all fail.
    """
    article_id = article.get("id") or article.get("uuid", "temp")
    out_filename = os.path.join(MEDIA_DIR, f"img_{article_id}.jpg")
    fallback_path = create_branded_fallback_image()
    
    candidate_urls = []
    
    # Use scraper for any missing primary image URL
    primary_url = article.get("image_url")
    if primary_url and str(primary_url) != "nan":
        candidate_urls.append(primary_url)
        
    # 1.5. If primary URL is missing, scrape it from the article page
    if not primary_url or str(primary_url) == "nan":
        article_url = article.get("url")
        if article_url and str(article_url) != "nan" and "news.google.com" not in article_url.lower():
            scraped_img = scrape_article_image(article_url)
            if scraped_img:
                candidate_urls.append(scraped_img)


    # 2. Newspaper parsed images
    extra_imgs = article.get("images", [])
    if isinstance(extra_imgs, list):
        for img_url in extra_imgs:
            if img_url and img_url not in candidate_urls and str(img_url).startswith("http"):
                candidate_urls.append(img_url)

    # Attempt download across candidates
    for idx, url in enumerate(candidate_urls):
        ok, reason, diag = download_valid_image(url, out_filename)
        
        if ok:
            log_event("IMAGE_DOWNLOAD", f"Successfully downloaded news image candidate #{idx+1} from {url[:50]}...", article_uuid=article.get("uuid"))
            result_path = os.path.abspath(out_filename)
            if return_diagnostics:
                diag["original_image_url"] = url
                diag["download_success"] = True
                diag["final_background_used"] = "Downloaded"
                diag["saved_image_path"] = result_path
                return result_path, diag
            return result_path
        else:
            log_event("IMAGE_DOWNLOAD_WARN", f"Candidate #{idx+1} failed ({reason}) for URL: {url[:50]}", article_uuid=article.get("uuid"), level="WARNING")
            if idx == len(candidate_urls) - 1 and return_diagnostics:
                # Save the last failed diagnostic
                diag["original_image_url"] = url
                diag["download_success"] = False

    # All candidate downloads failed - use branded fallback
    log_event("IMAGE_FALLBACK_USED", f"All photo downloads failed. Used branded fallback image: {fallback_path}", article_uuid=article.get("uuid"), level="WARNING")
    result_path = os.path.abspath(fallback_path)
    if return_diagnostics:
        if "diag" not in locals():
            diag = {
                "http_status_code": None,
                "pil_validation_success": False,
                "image_width": None,
                "image_height": None,
                "original_image_url": "N/A",
                "download_success": False,
            }
        diag["final_background_used"] = "Fallback"
        diag["saved_image_path"] = result_path
        return result_path, diag
        
    return result_path