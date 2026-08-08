from PIL import Image
import numpy as np
import os

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False



def detect_faces(image_path):
    """
    Detects faces in an image using OpenCV Haar Cascades.
    Returns a list of (x, y, w, h) bounding boxes in original image coordinates.
    """
    try:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if not os.path.exists(cascade_path):
            return []
        
        face_cascade = cv2.CascadeClassifier(cascade_path)
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40)
        )
        return faces if len(faces) > 0 else []
    except Exception:
        return []


def analyze_image_metrics(canvas_image, text_roi_box):
    """
    Analyzes canvas image metrics in the text ROI area:
    - Average perceived luminance (brightness)
    - Laplacian edge density / texture busyness (high contrast detail)
    Returns a dict with brightness, busyness, and contrast metrics.
    """
    try:
        x1, y1, w, h = text_roi_box["x"], text_roi_box["y_start"], text_roi_box["width"], text_roi_box["height"]
        x2 = min(canvas_image.width, x1 + w)
        y2 = min(canvas_image.height, y1 + h)

        roi = canvas_image.crop((x1, y1, x2, y2)).convert("RGB")
        roi_np = np.array(roi)

        # Perceived luminance (ITU-R BT.601)
        luminance = 0.299 * roi_np[:, :, 0] + 0.587 * roi_np[:, :, 1] + 0.114 * roi_np[:, :, 2]
        avg_brightness = float(np.mean(luminance))

        # Busyness via Laplacian edge variance
        gray_roi = cv2.cvtColor(roi_np, cv2.COLOR_RGB2GRAY)
        lap = cv2.Laplacian(gray_roi, cv2.CV_64F)
        busyness = float(np.std(lap))

        return {
            "brightness": avg_brightness,
            "busyness": busyness,
            "contrast": float(np.std(luminance)),
        }
    except Exception:
        return {
            "brightness": 100.0,
            "busyness": 10.0,
            "contrast": 30.0,
        }


def calculate_saliency_center(img_bgr):
    """
    Calculates the center of visual interest (saliency centroid)
    using Laplacian edge density and luminance variance.
    """
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        magnitude = np.abs(laplacian)
        
        # Focus on top 20% most salient pixels
        threshold = np.percentile(magnitude, 80)
        salient_mask = magnitude >= threshold
        
        y_indices, x_indices = np.where(salient_mask)
        if len(x_indices) > 0 and len(y_indices) > 0:
            center_x = int(np.mean(x_indices))
            center_y = int(np.mean(y_indices))
            return center_x, center_y
    except Exception:
        pass
    
    h, w = img_bgr.shape[:2]
    return w // 2, h // 2



def get_cropped_face_positions(image_path, target_w, target_h):
    """
    Returns face bounding boxes (y_top_canvas, y_bottom_canvas)
    transformed into final canvas coordinates after smart cropping.
    """
    faces = detect_faces(image_path)
    if len(faces) == 0:
        return []
    
    try:
        image = Image.open(image_path)
        orig_w, orig_h = image.size
        ratio = max(target_w / orig_w, target_h / orig_h)
        new_h = int(orig_h * ratio)
        
        total_y = sum(y + h / 2.0 for (x, y, w, h) in faces)
        focal_y = total_y / len(faces)
        scaled_focal_y = focal_y * ratio
        top_crop = int(clamp(scaled_focal_y - target_h / 2.0, 0, new_h - target_h))

        canvas_faces = []
        for (x, y, w, h) in faces:
            y_top_canvas = (y * ratio) - top_crop
            y_bottom_canvas = ((y + h) * ratio) - top_crop
            canvas_faces.append((y_top_canvas, y_bottom_canvas))
        return canvas_faces
    except Exception:
        return []


def fit_image(image_path, box):
    """
    Intelligently crops and resizes an image to fit target box dimensions (width, height)
    using face detection and saliency analysis to keep main subjects visible.
    """
    image = Image.open(image_path).convert("RGB")
    orig_w, orig_h = image.size
    target_w = box["width"]
    target_h = box["height"]

    # Calculate uniform scaling ratio to cover target dimensions
    ratio = max(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * ratio)
    new_h = int(orig_h * ratio)

    # Detect faces in original image
    faces = detect_faces(image_path)
    
    if len(faces) > 0:
        # Center crop window around detected faces centroid
        total_x = sum(x + w / 2.0 for (x, y, w, h) in faces)
        total_y = sum(y + h / 2.0 for (x, y, w, h) in faces)
        focal_x = total_x / len(faces)
        focal_y = total_y / len(faces)
    else:
        # Saliency centroid fallback
        img_bgr = np.array(image)[:, :, ::-1]
        focal_x, focal_y = calculate_saliency_center(img_bgr)

    # Scale focal coordinates to resized image dimensions
    scaled_focal_x = focal_x * ratio
    scaled_focal_y = focal_y * ratio

    # Calculate top-left crop origin, clamped within boundaries
    left = int(clamp(scaled_focal_x - target_w / 2.0, 0, new_w - target_w))
    top = int(clamp(scaled_focal_y - target_h / 2.0, 0, new_h - target_h))

    # Perform high-quality Lanczos resize and crop
    resized = image.resize((new_w, new_h), Image.LANCZOS)
    cropped = resized.crop((left, top, left + target_w, top + target_h))
    
    return cropped


def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))
