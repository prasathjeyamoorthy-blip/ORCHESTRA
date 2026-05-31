from helpers import run_vlm
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
import cv2
import numpy as np
from PIL import Image

from dotenv import load_dotenv
load_dotenv()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MIN_FILE_SIZE = 20 * 1024          # 20KB


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
    country: str = "India"
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
You are a document extraction assistant for Indian government documents.
Analyze this Aadhaar card image and extract information.

IMPORTANT:
- Split the full name into first, middle, and last name.
- The "C/O" or "S/O" or "D/O" or "W/O" line is the father/guardian name. Split it too.
- Split the address into separate fields as listed below.

Return a JSON object with exactly these fields:
{
  "document_type": "aadhaar" or "unknown",
  "is_legible": true or false,
  "aadhaar_number": 12-digit number (may be masked like XXXX XXXX 1234),
  "name": full name exactly as printed,
  "first_name": first name only,
  "middle_name": middle name if any, else null,
  "last_name": last/family/surname,
  "father_name": full father/guardian name from C/O or S/O line,
  "father_first_name": father's first name,
  "father_middle_name": father's middle name if any, else null,
  "father_last_name": father's last/family/surname,
  "dob": date of birth in DD/MM/YYYY format,
  "gender": "Male" or "Female" or "Transgender",
  "mobile_number": 10-digit mobile number if printed on the card,
  "email_id": email address if printed on the card,
  "flat_door_building": flat/door/building number,
  "road_street_block": road/street/block/sector name,
  "post_office": post office name if visible,
  "area_locality_city": area/locality/town/city,
  "district": district name,
  "state": state or union territory name,
  "pincode": 6-digit pincode if visible,
  "country": "India",
  "is_masked": true if aadhaar number is partially hidden,
  "confidence": "high" / "medium" / "low",
  "issues": list any problems like ["blurry", "cropped", "glare", "tampered"] or empty list
}

Rules:
- Return ONLY raw JSON, no markdown, no backticks
- If a field is not visible, use null
- Do not guess — only extract what is clearly visible
- Split name and address carefully into the correct sub-fields
- father_name comes from C/O, S/O, D/O, or W/O line on the card
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
# STEP 1 — TECHNICAL CHECKS (instant, no AI)
# ==============================================================

def basic_file_check(file_path: str, label: str) -> tuple[bool, str]:
    path = Path(file_path)

    if not path.exists():
        return False, f"{label}: File not found"

    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"{label}: Invalid file type '{ext}'. Allowed: JPG, PNG, PDF"

    size = os.path.getsize(file_path)
    if size > MAX_FILE_SIZE:
        return False, f"{label}: File too large (max 10MB)"
    if size < MIN_FILE_SIZE:
        return False, f"{label}: File too small, likely low quality"

    return True, "OK"


def image_quality_check(file_path: str, label: str) -> tuple[bool, str]:
    if file_path.lower().endswith(".pdf"):
        return True, "OK"  # PDFs skip this check

    img = cv2.imread(file_path)
    if img is None:
        return False, f"{label}: Could not read image file"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Blur check — skipped for signatures because thin ink on white paper
    # inherently gives very low Laplacian variance even when perfectly clear.
    # Gemini will catch illegible signatures in the AI step.
    if label.lower() != "signature":
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 60:
            return False, f"{label}: Image is too blurry. Please retake in better lighting"

    # Brightness check
    brightness = np.mean(gray)
    if brightness < 40:
        return False, f"{label}: Image is too dark. Please retake in better lighting"
    if brightness > 240:
        return False, f"{label}: Image is overexposed / too bright"

    # Resolution check
    h, w = img.shape[:2]
    if h < 150 or w < 150:
        return False, f"{label}: Image resolution too low (minimum 150x150px)"

    return True, "OK"


# ==============================================================
# STEP 2 — GEMINI EXTRACTION (async, parallel)
# ==============================================================

def call_vlm(prompt: str, file_path: str) -> dict:
    return run_vlm(prompt, file_path)


async def extract_aadhaar_async(file_path: str) -> AadhaarData:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, call_vlm, AADHAAR_PROMPT, file_path)
    return AadhaarData(**data)


async def verify_photo_async(file_path: str) -> PhotoData:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, call_vlm, PHOTO_PROMPT, file_path)
    return PhotoData(**data)


async def verify_signature_async(file_path: str) -> SignatureData:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, call_vlm, SIGNATURE_PROMPT, file_path)
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

    # All confidence levels
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


# ==============================================================
# MAIN PIPELINE
# ==============================================================

async def run_pan_verification(aadhaar_path: str, photo_path: str, signature_path: str):
    print("\n" + "=" * 60)
    print("        PAN APPLICATION — DOCUMENT VERIFICATION")
    print("=" * 60)

    # ── Step 1: Technical checks (instant) ──
    print("\n⏳ Step 1: Running technical checks...")
    all_files = [
        (aadhaar_path, "Aadhaar"),
        (photo_path, "Photo"),
        (signature_path, "Signature"),
    ]
    tech_errors = []
    for path, label in all_files:
        ok, msg = basic_file_check(path, label)
        if not ok:
            tech_errors.append(msg)
            continue
        ok, msg = image_quality_check(path, label)
        if not ok:
            tech_errors.append(msg)

    if tech_errors:
        print("\n❌ Technical checks failed. Fix these before proceeding:\n")
        for e in tech_errors:
            print(f"   • {e}")
        print()
        return

    print("   ✅ All technical checks passed")

    # ── Step 2: Gemini analysis (parallel) ──
    print("\n⏳ Step 2: Analyzing documents with AI (running in parallel)...")
    try:
        aadhaar_data, photo_data, sig_data = await asyncio.gather(
            extract_aadhaar_async(aadhaar_path),
            )
    except Exception as e:
        print(f"\n❌ AI analysis failed: {e}")
        return

    print("   ✅ AI analysis complete")

    # ── Step 3: Field validation ──
    print("\n⏳ Step 3: Validating extracted fields...")
    aadhaar_errors = validate_aadhaar_fields(aadhaar_data)
    photo_errors   = validate_photo_fields(photo_data)
    sig_errors     = validate_signature_fields(sig_data)

    # ── Step 4: Cross validation ──
    cross_errors = cross_validate(aadhaar_data, photo_data, sig_data)

    # ── Print Results ──
    print("\n" + "=" * 60)
    print("                  AADHAAR CARD")
    print("=" * 60)
    print(f"  Aadhaar No.    : {aadhaar_data.aadhaar_number or 'N/A'} {'(masked)' if aadhaar_data.is_masked else ''}")
    print(f"  Confidence     : {aadhaar_data.confidence.upper()}")
    print()
    print("  ── Name ──")
    print(f"  Full Name      : {aadhaar_data.name or 'N/A'}")
    print(f"  First Name     : {aadhaar_data.first_name or 'N/A'}")
    print(f"  Middle Name    : {aadhaar_data.middle_name or 'N/A'}")
    print(f"  Last Name      : {aadhaar_data.last_name or 'N/A'}")
    print()
    print("  ── Father / Guardian ──")
    print(f"  Father Name    : {aadhaar_data.father_name or 'N/A'}")
    print(f"  Father First   : {aadhaar_data.father_first_name or 'N/A'}")
    print(f"  Father Middle  : {aadhaar_data.father_middle_name or 'N/A'}")
    print(f"  Father Last    : {aadhaar_data.father_last_name or 'N/A'}")
    print()
    print("  ── Personal ──")
    print(f"  Date of Birth  : {aadhaar_data.dob or 'N/A'}")
    print(f"  Gender         : {aadhaar_data.gender or 'N/A'}")
    print(f"  Mobile No.     : {aadhaar_data.mobile_number or 'N/A'}")
    print(f"  Email Id       : {aadhaar_data.email_id or 'N/A'}")
    print()
    print("  ── Address ──")
    print(f"  Flat/Door/Bldg : {aadhaar_data.flat_door_building or 'N/A'}")
    print(f"  Road/Street    : {aadhaar_data.road_street_block or 'N/A'}")
    print(f"  Post Office    : {aadhaar_data.post_office or 'N/A'}")
    print(f"  Area/City      : {aadhaar_data.area_locality_city or 'N/A'}")
    print(f"  District       : {aadhaar_data.district or 'N/A'}")
    print(f"  State/UT       : {aadhaar_data.state or 'N/A'}")
    print(f"  Pin Code       : {aadhaar_data.pincode or 'N/A'}")
    print(f"  Country        : {aadhaar_data.country}")
    print()
    print("  ── JSON Output ──")
    aadhaar_json = {
        "aadhaar_number": aadhaar_data.aadhaar_number,
        "name": aadhaar_data.name,
        "first_name": aadhaar_data.first_name,
        "middle_name": aadhaar_data.middle_name,
        "last_name": aadhaar_data.last_name,
        "father_name": aadhaar_data.father_name,
        "father_first_name": aadhaar_data.father_first_name,
        "father_middle_name": aadhaar_data.father_middle_name,
        "father_last_name": aadhaar_data.father_last_name,
        "dob": aadhaar_data.dob,
        "gender": aadhaar_data.gender,
        "mobile_number": aadhaar_data.mobile_number,
        "email_id": aadhaar_data.email_id,
        "state": aadhaar_data.state,
        "city": aadhaar_data.area_locality_city,
    }
    print(json.dumps(aadhaar_json, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("                 PASSPORT PHOTO")
    print("=" * 60)
    print(f"  Face Detected  : {'✅' if photo_data.has_face else '❌'}")
    print(f"  Face Count     : {photo_data.face_count}")
    print(f"  Face Centered  : {'✅' if photo_data.face_centered else '❌'}")
    print(f"  Eyes Visible   : {'✅' if photo_data.eyes_visible else '❌'}")
    print(f"  Plain BG       : {'✅' if photo_data.plain_background else '❌'}")
    print(f"  Colored Photo  : {'✅' if photo_data.is_colored else '❌'}")
    print(f"  Confidence     : {photo_data.confidence.upper()}")

    print("\n" + "=" * 60)
    print("                   SIGNATURE")
    print("=" * 60)
    print(f"  Signature Found: {'✅' if sig_data.has_signature else '❌'}")
    print(f"  Handwritten    : {'✅' if sig_data.is_handwritten else '❌'}")
    print(f"  Clearly Visible: {'✅' if sig_data.is_visible else '❌'}")
    print(f"  Plain BG       : {'✅' if sig_data.plain_background else '❌'}")
    print(f"  Not Cut Off    : {'✅' if not sig_data.is_cut_off else '❌'}")
    print(f"  Confidence     : {sig_data.confidence.upper()}")

    # ── Final verdict ──
    all_errors = aadhaar_errors + photo_errors + sig_errors + cross_errors

    print("\n" + "=" * 60)
    print("                  FINAL VERDICT")
    print("=" * 60)

    if not all_errors:
        print("\n  ✅ All documents verified successfully!")
        print("  ✅ Ready to proceed with PAN application.\n")
    else:
        print(f"\n  ❌ {len(all_errors)} issue(s) found. Please fix the following:\n")
        for i, err in enumerate(all_errors, 1):
            print(f"  {i}. {err}")
        print()

    return {
        "status": "pass" if not all_errors else "fail",
        "errors": all_errors,
        "aadhaar": aadhaar_data.model_dump(),
        "photo": photo_data.model_dump(),
        "signature": sig_data.model_dump(),
    }


# ==============================================================
# CLI ENTRY POINT
# ==============================================================

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("\nUsage: python pan_verification.py <aadhaar> <photo> <signature>")
        print("Example: python pan_verification.py aadhaar.jpg photo.jpg signature.png\n")
        sys.exit(1)

    aadhaar_path   = sys.argv[1]
    photo_path     = sys.argv[2]
    signature_path = sys.argv[3]

    asyncio.run(run_pan_verification(aadhaar_path, photo_path, signature_path))