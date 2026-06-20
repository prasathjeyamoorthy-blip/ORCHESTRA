import asyncio
import json
import os
import re
import sys
import base64
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
from pdf2image import convert_from_bytes
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MIN_FILE_SIZE = 20 * 1024          # 20KB
POPPLER_PATH = r"D:\poppler\poppler-25.12.0\Library\bin"


# ==============================================================
# PYDANTIC SCHEMAS
# ==============================================================

class AadhaarData(BaseModel):
    document_type: str
    is_legible: bool
    aadhaar_number: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    father_name: Optional[str] = None
    father_first_name: Optional[str] = None
    father_middle_name: Optional[str] = None
    father_last_name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    mobile_number: Optional[str] = None
    email_id: Optional[str] = None
    flat_door_building: Optional[str] = None
    road_street_block: Optional[str] = None
    post_office: Optional[str] = None
    area_locality_city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = "India"
    is_masked: Optional[bool] = False
    confidence: str
    issues: Optional[list[str]] = None

class PhotoData(BaseModel):
    has_face: bool
    face_count: int
    face_centered: bool
    eyes_visible: bool
    plain_background: bool
    has_sunglasses: bool
    is_colored: bool
    confidence: str
    issues: Optional[list[str]] = None

class SignatureData(BaseModel):
    has_signature: bool
    is_handwritten: bool
    is_visible: bool
    plain_background: bool
    is_cut_off: bool
    confidence: str
    issues: Optional[list[str]] = None


# ==============================================================
# PROMPTS
# ==============================================================

AADHAAR_PROMPT = """
Extract the below details and return ONLY valid JSON:

{
  "document_type": "aadhaar" or "unknown",
  "is_legible": true or false,
  "aadhaar_number": "12 digits or masked like XXXX XXXX 1234",
  "name": "",
  "first_name": "",
  "last_name": "",
  "middle_name": null,
  "father_name": "",
  "father_first_name": "",
  "father_middle_name": null,
  "father_last_name": "",
  "mobile_number": "10 digits or null",
  "state": "",
  "city": "",
  "gender": "",
  "dob": "DD/MM/YYYY or null",
  "email_id": "email address or null",
  "flat_door_building": "flat/door/building number or null",
  "road_street_block": "road/street/block/sector name or null",
  "post_office": "post office name or null",
  "area_locality_city": "area/locality/town/city or null",
  "district": "district name or null",
  "pincode": "6-digit pincode or null",
  "country": "India",
  "is_masked": true or false,
  "confidence": "low/medium/high depending on the quality of extraction",
  "issues": []
}

Rules:
- Mobile number: Identify a valid Indian mobile number (10 digits, typically starting with 9).
- DOB: Identify the field labeled "DOB" or "Date of Birth"
- Father name may appear as S/O, C/O, D/O, W/O → remove prefix, extract only name
- City must be taken from VTC (Village/Town/City)
- Split names: first = first_name, last = last_name, rest = middle_name
- Use null if missing
- Output STRICT JSON only (no text, no markdown)
- Gender: Look for keywords like "Male", "Female", "M", "F", or similar indicators
"""

PHOTO_PROMPT = """
You are verifying a passport-style photograph for an Indian government PAN card application.
Analyze this photo strictly.

Return a JSON object with exactly these fields:
{
  "has_face": true or false (is there a human face?),
  "face_count": number of faces visible,
  "face_centered": true if face is centered and takes up most of the frame,
  "eyes_visible": true if both eyes are clearly open and visible,
  "plain_background": true if background is plain white or light colored,
  "has_sunglasses": true if person is wearing sunglasses or dark glasses,
  "is_colored": true if photo is in color (not black and white),
  "confidence": "high" / "medium" / "low",
  "issues": list problems like ["dark background", "multiple faces", "eyes closed", "sunglasses", "blurry"] or empty list
}

Rules:
- Return ONLY raw JSON, no markdown, no backticks
- Be strict — government photo standards must be met
"""

SIGNATURE_PROMPT = """
You are verifying a signature image for an Indian government PAN card application.
Analyze this signature image strictly.

Return a JSON object with exactly these fields:
{
  "has_signature": true or false (is there a visible signature?),
  "is_handwritten": true if it is a hand-drawn signature (not typed/printed text),
  "is_visible": true if the signature is clearly visible and not too faint,
  "plain_background": true if background is plain white or very light,
  "is_cut_off": true if the signature appears to go outside the image boundary,
  "confidence": "high" / "medium" / "low",
  "issues": list problems like ["typed text", "too faint", "cut off", "dark background"] or empty list
}

Rules:
- Return ONLY raw JSON, no markdown, no backticks
- A signature must be handwritten, not a typed name
"""


# ==============================================================
# HELPERS FOR IMAGE TO BASE64 AND NVIDIA NIM
# ==============================================================

def image_to_base64_from_bytes(file_bytes: bytes, filename: str) -> str:
    ext = filename.lower().split('.')[-1]
    try:
        if ext == "pdf":
            pages = convert_from_bytes(
                file_bytes,
                first_page=1,
                last_page=1,
                dpi=300,
                poppler_path=POPPLER_PATH
            )
            pil_img = pages[0]
        else:
            pil_img = Image.open(BytesIO(file_bytes))
            pil_img.load()

        buffer = BytesIO()
        pil_img.save(buffer, format="JPEG", quality=95)
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        raise ValueError(f"Image conversion failed: {str(e)}")


def image_to_base64_from_path(file_path: str) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        if ext == ".pdf":
            pages = convert_from_bytes(
                file_bytes,
                first_page=1,
                last_page=1,
                dpi=300,
                poppler_path=POPPLER_PATH
            )
            pil_img = pages[0]
        else:
            pil_img = Image.open(BytesIO(file_bytes))
            pil_img.load()

        buffer = BytesIO()
        pil_img.save(buffer, format="JPEG", quality=95)
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        raise ValueError(f"Image conversion failed for path {file_path}: {str(e)}")


def call_nvidia(prompt: str, image_b64: str) -> dict:
    """NVIDIA NIM VLM (primary)."""
    api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    api_key = os.getenv('NVIDIA_API_KEY') or os.getenv('NVIDIA_META_11B') or os.getenv('NVIDIA_META_90B')
    if not api_key:
        raise ValueError("Set NVIDIA_API_KEY or NVIDIA_META_11B in .env")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta/llama-3.2-90b-vision-instruct",
        "temperature": 0,
        "max_tokens": 1000,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": f"""{prompt}

STRICT INSTRUCTIONS:
- Output ONLY valid JSON
- No explanation
- No text before or after JSON
- No markdown
- Start with {{ and end with }}
                     """},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        }]
    }
    
    for attempt in range(3):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            logger.warning(f"NVIDIA attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise RuntimeError(f"NVIDIA VLM request failed after retries.")
            asyncio.run(asyncio.sleep(2 ** attempt))


def run_vlm(prompt: str, file_source: Union[bytes, str], filename: Optional[str] = None) -> dict:
    if isinstance(file_source, bytes):
        image_b64 = image_to_base64_from_bytes(file_source, filename or "file.jpg")
    else:
        image_b64 = image_to_base64_from_path(file_source)
    return call_nvidia(prompt, image_b64)


# ==============================================================
# STEP 1 — TECHNICAL CHECKS (instant, no AI)
# ==============================================================

def basic_file_check(file_source: Union[bytes, str], label: str, filename: Optional[str] = None) -> tuple[bool, str]:
    if isinstance(file_source, str):
        path = Path(file_source)
        if not path.exists():
            return False, f"{label}: File not found"
        ext = path.suffix.lower()
        size = os.path.getsize(file_source)
    else:
        ext = "." + (filename or "file.jpg").lower().split('.')[-1]
        size = len(file_source)

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"{label}: Invalid file type '{ext}'. Allowed: JPG, PNG, PDF"

    if size > MAX_FILE_SIZE:
        return False, f"{label}: File too large (max 10MB)"
    if size < MIN_FILE_SIZE:
        return False, f"{label}: File too small, likely low quality"

    return True, "OK"


def image_quality_check(file_source: Union[bytes, str], label: str, filename: Optional[str] = None) -> tuple[bool, str]:
    if isinstance(file_source, str):
        if file_source.lower().endswith(".pdf"):
            return True, "OK"
        img = cv2.imread(file_source)
    else:
        if filename and filename.lower().endswith(".pdf"):
            return True, "OK"
        nparr = np.frombuffer(file_source, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return False, f"{label}: Could not read image file"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if label.lower() != "signature":
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 60:
            return False, f"{label}: Image is too blurry. Please retake in better lighting"

    brightness = np.mean(gray)
    if brightness < 40:
        return False, f"{label}: Image is too dark. Please retake in better lighting"
    if brightness > 240:
        return False, f"{label}: Image is overexposed / too bright"

    h, w = img.shape[:2]
    if h < 150 or w < 150:
        return False, f"{label}: Image resolution too low (minimum 150x150px)"

    return True, "OK"


# ==============================================================
# STEP 2 — GEMINI EXTRACTION (async, parallel)
# ==============================================================

def call_vlm_wrapper(prompt: str, file_source: Union[bytes, str], filename: Optional[str] = None) -> dict:
    return run_vlm(prompt, file_source, filename)


async def extract_aadhaar_async(file_source: Union[bytes, str], filename: Optional[str] = None) -> AadhaarData:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, call_vlm_wrapper, AADHAAR_PROMPT, file_source, filename)
    return AadhaarData(**data)


async def verify_photo_async(file_source: Union[bytes, str], filename: Optional[str] = None) -> PhotoData:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, call_vlm_wrapper, PHOTO_PROMPT, file_source, filename)
    return PhotoData(**data)


async def verify_signature_async(file_source: Union[bytes, str], filename: Optional[str] = None) -> SignatureData:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, call_vlm_wrapper, SIGNATURE_PROMPT, file_source, filename)
    return SignatureData(**data)


# ==============================================================
# STEP 3 — FIELD VALIDATION (instant, rule-based)
# ==============================================================

def validate_aadhaar_fields(data: AadhaarData) -> list[str]:
    errors = []

    if not data.name:
        errors.append("Could not extract name from Aadhaar")

    if not data.dob:
        errors.append("Could not extract date of birth from Aadhaar")
    else:
        try:
            dob = datetime.strptime(data.dob, "%d/%m/%Y")
            age = (datetime.now() - dob).days // 365
            if age < 0 or age > 120:
                errors.append(f"Date of birth seems invalid (age calculated: {age})")
            if dob > datetime.now():
                errors.append("Date of birth cannot be in the future")
        except ValueError:
            errors.append(f"Date of birth format not recognized: '{data.dob}' (expected DD/MM/YYYY)")

    if data.aadhaar_number:
        digits = re.sub(r'\D', '', data.aadhaar_number)
        if len(digits) not in [4, 12]:
            errors.append(f"Aadhaar number format invalid: '{data.aadhaar_number}'")
    else:
        errors.append("Could not extract Aadhaar number")

    if data.pincode:
        if not re.match(r'^[1-9]\d{5}$', data.pincode):
            errors.append(f"Pincode invalid: '{data.pincode}' (must be 6 digits, not starting with 0)")

    if data.document_type.lower() != "aadhaar":
        errors.append(f"Document does not appear to be an Aadhaar card (detected: {data.document_type})")

    return errors


def validate_photo_fields(data: PhotoData) -> list[str]:
    errors = []
    if not data.has_face:
        errors.append("No face detected in the photo")
    if data.face_count > 1:
        errors.append(f"Multiple faces detected ({data.face_count}). Please upload a solo photo")
    if not data.face_centered:
        errors.append("Face is not centered. Please retake with face in center of frame")
    if not data.eyes_visible:
        errors.append("Eyes are not clearly visible. Please ensure eyes are open")
    if not data.plain_background:
        errors.append("Background must be plain white or light colored")
    if data.has_sunglasses:
        errors.append("Please remove sunglasses or dark glasses")
    if not data.is_colored:
        errors.append("Please upload a color photograph, not black and white")
    return errors


def validate_signature_fields(data: SignatureData) -> list[str]:
    errors = []
    if not data.has_signature:
        errors.append("No signature detected in the image")
    if not data.is_handwritten:
        errors.append("Signature must be handwritten, not typed or printed text")
    if not data.is_visible:
        errors.append("Signature is too faint. Please use a dark pen on white paper")
    if not data.plain_background:
        errors.append("Signature must be on a plain white background")
    if data.is_cut_off:
        errors.append("Signature appears cut off. Please ensure the full signature is visible")
    return errors


# ==============================================================
# STEP 4 — CROSS VALIDATION
# ==============================================================

def cross_validate(aadhaar: AadhaarData, photo: PhotoData, sig: SignatureData) -> list[str]:
    issues = []

    low_confidence = []
    if aadhaar.confidence == "low":
        low_confidence.append("Aadhaar")
    if photo.confidence == "low":
        low_confidence.append("Photo")
    if sig.confidence == "low":
        low_confidence.append("Signature")

    if low_confidence:
        issues.append(f"Low confidence reading: {', '.join(low_confidence)} — please re-upload clearer images")

    return issues
