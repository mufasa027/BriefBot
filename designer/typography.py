from PIL import ImageDraw, ImageFont


def balance_headline_lines(text, font, draw, max_width, max_lines=3):
    """
    Intelligently balances headline words across lines to prevent single-word orphan
    trailing lines and optimize visual symmetry.
    """
    words = text.strip().split()
    if not words:
        return []

    # Simple case: fits on a single line
    total_single_w = draw.textbbox((0, 0), text, font=font)[2]
    if total_single_w <= max_width:
        return [text]

    # Standard greedy line splitting
    greedy_lines = []
    current = ""
    for word in words:
        test = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                greedy_lines.append(current)
            current = word
    if current:
        greedy_lines.append(current)

    # If greedy result has > max_lines or last line is healthy (> 1 word), return greedy
    if len(greedy_lines) > max_lines or len(greedy_lines) <= 1:
        return greedy_lines[:max_lines]

    last_line_words = greedy_lines[-1].split()
    if len(last_line_words) > 1:
        return greedy_lines[:max_lines]

    # Optical re-balancing: shift words to equalize line lengths
    num_lines = min(len(greedy_lines), max_lines)
    words_per_line = len(words) // num_lines
    
    balanced_lines = []
    w_idx = 0
    for i in range(num_lines):
        if i == num_lines - 1:
            chunk = " ".join(words[w_idx:])
        else:
            chunk = " ".join(words[w_idx:w_idx + words_per_line])
            w_idx += words_per_line
        
        # Verify chunk width
        if draw.textbbox((0, 0), chunk, font=font)[2] > max_width and len(chunk.split()) > 1:
            # Fallback to safe split
            parts = chunk.split()
            chunk = parts[0]
            w_idx -= (len(parts) - 1)

        balanced_lines.append(chunk)

    return balanced_lines


def calculate_headline_font_size(text, font_path, draw, config):
    """
    Dynamically scales headline font size to target between 2 and 4 balanced lines
    without exceeding safe width or overflowing vertical limits.
    """
    max_w = config["max_width"]
    min_size = config.get("min_font_size", 50)
    max_size = config.get("max_font_size", 72)

    best_size = config.get("font_size", 62)
    best_lines = []

    # Iterative solver from max_size down to min_size
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size)
        lines = balance_headline_lines(text, font, draw, max_w, max_lines=4)

        if 2 <= len(lines) <= 4:
            best_size = size
            best_lines = lines
            break
        elif len(lines) < 2 and size > min_size:
            # Title is short, attempt larger size if possible
            best_size = size
            best_lines = lines
        elif len(lines) > 4:
            continue

    if not best_lines:
        best_size = min_size
        font = ImageFont.truetype(font_path, min_size)
        best_lines = balance_headline_lines(text, font, draw, max_w, max_lines=4)

    return best_size, best_lines



def draw_wrapped_text(
    image,
    text,
    box,
    font_path,
    color,
):
    """
    Renders wrapped text dynamically fitting the largest possible font size within box bounds.
    """
    text = str(text or "").strip()
    draw = ImageDraw.Draw(image)


    best_font = None
    best_lines = []
    best_line_height = 0

    # Dynamic font scaling to fit max_height
    start_size = box.get("font_size", 40)
    min_size = box.get("min_font_size", 18)

    for size in range(start_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size)
        words = text.split()
        lines = []
        current = ""

        for word in words:
            test = word if not current else f"{current} {word}"
            width = draw.textbbox((0, 0), test, font=font)[2]

            if width <= box["width"]:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_height = (bbox[3] - bbox[1]) + box.get("line_spacing", 6)
        total_height = line_height * len(lines)

        if total_height <= box.get("max_height", 999):
            best_font = font
            best_lines = lines
            best_line_height = line_height
            break

    if best_font is None:
        best_font = ImageFont.truetype(font_path, min_size)
        best_lines = [text]
        best_line_height = 24

    # Render lines starting at box['y']
    y = box["y"]
    for line in best_lines:
        draw.text(
            (box["x"], y),
            line,
            font=best_font,
            fill=color,
        )
        y += best_line_height

    return y