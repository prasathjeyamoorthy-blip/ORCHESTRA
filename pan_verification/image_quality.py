import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_bytes
import io
import os
from dotenv import load_dotenv
load_dotenv()

POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\poppler-25.12.0\Library\bin")

# -----------------------------------
# LOAD IMAGE FROM MEMORY
# -----------------------------------
def load_image_from_bytes(file_bytes, filename):
    ext = filename.lower().split('.')[-1]

    try:
        # PDF
        if ext == "pdf":
            pages = convert_from_bytes(
                file_bytes,
                first_page=1,
                last_page=1,
                dpi=300,
                poppler_path=POPPLER_PATH
            )
            pil_img = pages[0]
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # Image
        else:
            pil_img = Image.open(io.BytesIO(file_bytes))
            pil_img.load()
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        return image, None

    except Exception as e:
        return None, str(e)


# -----------------------------------
# QUALITY CHECK
# -----------------------------------
def check_quality(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape
    resolution_score = 1 if w >= 800 and h >= 600 else 0.3

    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_score = 1 if blur > 100 else 0.4

    brightness = np.mean(gray)
    brightness_score = 1 if 50 < brightness < 200 else 0.4

    contrast = np.std(gray)
    contrast_score = 1 if contrast > 30 else 0.4

    return (
        0.35 * resolution_score +
        0.30 * blur_score +
        0.20 * brightness_score +
        0.15 * contrast_score
    )


# -----------------------------------
# DOCUMENT DETECTION (CROP)
# -----------------------------------
def detect_document(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            return image[y:y+h, x:x+w]

    # fallback
    h, w = image.shape[:2]
    return image[int(h*0.3):int(h*0.9), int(w*0.1):int(w*0.9)]


# -----------------------------------
# ENHANCEMENT
# -----------------------------------
def enhance_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    kernel = np.array([[0,-1,0],
                       [-1,5,-1],
                       [0,-1,0]])

    return cv2.filter2D(enhanced, -1, kernel)


# -----------------------------------
# EXTRACTION (HOOK YOUR NIM HERE)
# -----------------------------------
def extract_text(image):
    # Actual extraction is done by the VLM in app.py via run_vlm()
    # This function is kept for pipeline compatibility but is not used for real extraction
    return {}


# -----------------------------------
# MAIN PIPELINE
# -----------------------------------
def process_document(file_bytes, filename):
    image, error = load_image_from_bytes(file_bytes, filename)

    if error:
        return {"status": "error", "message": error}

    quality_score = check_quality(image)

    if quality_score < 0.5:
        return {
            "status": "rejected",
            "quality_score": round(quality_score, 2),
            "message": "Low quality image"
        }

    return {
        "status": "processed",
        "quality_score": round(quality_score, 2),
    }