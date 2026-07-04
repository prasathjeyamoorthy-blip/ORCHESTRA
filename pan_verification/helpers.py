import os
import base64
import requests
from PIL import Image
from io import BytesIO
import json
import time
import logging
from pdf2image import convert_from_bytes
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\poppler-25.12.0\Library\bin")

# -----------------------------------
# BYTES → BASE64 (NO TEMP FILE)
# -----------------------------------
def image_to_base64(file_bytes: bytes, filename: str) -> str:
    ext = filename.lower().split('.')[-1]

    try:
        # -----------------------------
        # PDF → Convert to image
        # -----------------------------
        if ext == "pdf":
            pages = convert_from_bytes(
                file_bytes,
                first_page=1,
                last_page=1,
                dpi=300,
                poppler_path=POPPLER_PATH
            )

            pil_img = pages[0]

        # -----------------------------
        # Image → Load directly
        # -----------------------------
        else:
            pil_img = Image.open(BytesIO(file_bytes))
            pil_img.load()

        # -----------------------------
        # Convert to base64
        # -----------------------------
        buffer = BytesIO()
        pil_img.save(buffer, format="JPEG", quality=95)

        return base64.b64encode(buffer.getvalue()).decode()

    except Exception as e:
        raise ValueError(f"Image conversion failed: {str(e)}")
def call_nvidia(prompt: str, image_b64: str) -> dict:
    """NVIDIA NIM VLM (primary)."""
    api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    api_key = os.getenv('NVIDIA_META_11B')
    if not api_key:
        raise ValueError("Set NVIDIA_META_11B in .env from build.nvidia.com")
    
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
            print(response.text)

            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
    
            return json.loads(content)
        except Exception as e:
            logger.warning(f"NVIDIA attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise RuntimeError(f"NVIDIA failed after retries. Key/network issue? DNS: ipconfig /flushdns")
            time.sleep(2 ** attempt)

def run_vlm(prompt: str, file_bytes: bytes, filename: str) -> dict:
    image_b64 = image_to_base64(file_bytes, filename)
    return call_nvidia(prompt, image_b64)

def detect_document_type(file_bytes: bytes, filename: str) -> dict:
    """Detect document type before processing."""
    return run_vlm(DOCUMENT_TYPE_PROMPT, file_bytes, filename)

def validate_profile_photo(file_bytes: bytes, filename: str) -> dict:
    """Validate profile photo quality and suitability."""
    return run_vlm(PROFILE_PHOTO_PROMPT, file_bytes, filename)


# Document Type Detection Prompt
DOCUMENT_TYPE_PROMPT = """
Analyze this image and identify the document type. Return ONLY valid JSON:

{
  "document_type": "aadhaar_card|pan_card|passport|driving_license|profile_photo|other_document",
  "is_human_face": true/false,
  "confidence": "low/medium/high",
  "description": "brief description of what you see"
}

Document Type Classification:
- "aadhaar_card": Contains Aadhaar logo, 12-digit number, person's photo, government format
- "pan_card": Contains PAN format (XXXXX0000X), Income Tax Department branding
- "passport": Contains passport format, government of India branding
- "driving_license": Contains DL number, transport department branding  
- "profile_photo": Just a person's face/portrait photo without any document background
- "other_document": Any other identity document or certificate

Human Face Detection:
- Set "is_human_face": true if you can clearly see a human face in the image
- Set "is_human_face": false if no clear human face is visible

Rules:
- Output STRICT JSON only (no text, no markdown)
- Confidence based on clarity and recognizability of document features
- Be specific about document type - don't guess if unclear
"""

AADHAAR_PROMPT = """
You are a document extraction assistant for Indian government documents.
Analyze this Aadhaar card image and extract information.

IMPORTANT:
- Split the full name into first, middle, and last name.
- The "C/O" or "S/O" or "D/O" or "W/O" line is the father/guardian name. Split it too.
- For mother/guardian line (if present), extract mother's name and split it.
- Split the address into separate fields as listed below.
- Extract phone/mobile number if visible.
- Determine residential status (Resident or Non-Resident).

Return a JSON object with exactly these fields:
{
  "document_type": "aadhaar" or "unknown",
  "is_legible": true or false,
  "aadhar_number": 12-digit number (may be masked like XXXX XXXX 1234),
  "name": full name exactly as printed,
  "first_name": first name only,
  "middle_name": middle name if any, else null,
  "last_name": last/family/surname,
  "phone": 10-digit phone number if printed on card,
  "father_name": full father/guardian name from C/O or S/O line,
  "father_first_name": father's first name,
  "father_middle_name": father's middle name if any, else null,
  "father_last_name": father's last/family/surname,
  "mother_name": full mother/guardian name if visible on card,
  "mother_first_name": mother's first name if visible, else null,
  "mother_middle_name": mother's middle name if any, else null,
  "mother_last_name": mother's last/family/surname if visible, else null,
  "dob": date of birth in DD/MM/YYYY format,
  "gender": "Male" or "Female" or "Transgender",
  "mobile_number": 10-digit mobile number if printed on the card,
  "email_id": email address if printed on the card,
  "residential_status": "Resident" or "Non-Resident" as indicated on card,
  "flat_room_door": flat/room/door number exactly as printed,
  "building_village": building name or village name,
  "road_street_post": road/street/sector/post name,
  "area_locality": area/locality/town name,
  "district": district name,
  "state": state or union territory name,
  "pincode": 6-digit pincode if visible,
  "country": "India",
  "is_masked": true if aadhar number is partially hidden,
  "confidence": "high" / "medium" / "low",
  "issues": list any problems like ["blurry", "cropped", "glare", "tampered"] or empty list
}

Rules:
- Return ONLY raw JSON, no markdown, no backticks
- If a field is not visible, use null
- Do not guess — only extract what is clearly visible
- Split name and address carefully into the correct sub-fields
- father_name comes from C/O, S/O, D/O, or W/O line on the card
- mother_name comes from mother/guardian designation line if present on the card
- phone field is for phone number (may be same as mobile_number)
- residential_status may be explicitly printed on the card
- Address fields should match exactly as they appear on the card
"""

PROFILE_PHOTO_PROMPT = """
Analyze this profile photo and return ONLY valid JSON:

{
  "is_human_face": true/false,
  "face_quality": "poor/good/excellent",
  "face_visibility": "partial/full/unclear",
  "photo_quality": "blurry/clear/high_quality",
  "suitable_for_pan": true/false,
  "issues": ["list of any issues like blur, poor lighting, multiple faces, etc"],
  "confidence": "low/medium/high"
}

Rules:
- Determine if this is suitable as a PAN application photo
- Check for single clear human face, good lighting, proper visibility
- List any quality issues that would make it unsuitable
- Output STRICT JSON only (no text, no markdown)
"""

OTHER_DOC_PROMPT = """
You are a document extraction assistant. Extract all visible text fields from this document.

Return a JSON object with the fields you can see, such as:
{
  "document_type": "detected type (e.g. driving_license, pan_card, passport, birth_certificate, etc.)",
  "name": "full name if visible",
  "dob": "date of birth in DD/MM/YYYY format if visible",
  "doc_number": "document number/ID if visible",
  "issue_date": "issue date if visible",
  "expiry_date": "expiry date if visible",
  "address": "full address if visible",
  "state": "state if visible",
  "gender": "Male/Female if visible",
  "confidence": "high/medium/low",
  "raw_fields": {}
}

Rules:
- Extract only what is clearly visible
- Use null for missing fields
- Return ONLY raw JSON, no markdown, no backticks
- Put any additional fields you find in raw_fields
"""
