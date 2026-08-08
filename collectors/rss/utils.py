def extract_image_url(entry):
    """
    Attempts to extract an image URL from a feedparser entry object.
    Checks media_content, media_thumbnail, and enclosure links.
    """
    # 1. Check media_content
    if hasattr(entry, 'media_content'):
        for media in entry.media_content:
            url = media.get('url')
            # sometimes type is image/jpeg
            if url and ('image' in media.get('medium', '') or 'image' in media.get('type', '')):
                return url
            # fallback if medium/type not perfectly specified
            if url and (url.lower().endswith('.jpg') or url.lower().endswith('.png') or url.lower().endswith('.jpeg')):
                return url

    # 2. Check media_thumbnail
    if hasattr(entry, 'media_thumbnail'):
        if len(entry.media_thumbnail) > 0:
            return entry.media_thumbnail[0].get('url')

    # 3. Check enclosure links
    if hasattr(entry, 'links'):
        for link in entry.links:
            if link.get('rel') == 'enclosure' and 'image' in link.get('type', ''):
                return link.get('href')
                
    # 4. Check for direct image attribute (sometimes feedparser puts it here)
    if hasattr(entry, 'image') and hasattr(entry.image, 'href'):
        return entry.image.href

    return None
