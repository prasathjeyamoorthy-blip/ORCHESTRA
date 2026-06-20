import os
import base64
import requests
from PIL import Image
from io import BytesIO
import json
import time
import logging
from pdf2image import convert_from_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POPPLER_PATH = r"D:\poppler\poppler-25.12.0\Library\bin"

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

'''AADHAAR_PROMPT = """
Extract ONLY these fields from Aadhaar image as JSON:

{
  "aadhar_number": "12 digits or masked",
  "name": "Full name",
  "first_name": "First name",
  "last_name": "Last name", 
  "middle_name": "Middle name or null",
  "father_name": "Full father name",
  "father_first_name": "Father first name",
  "father_middle_name": "Father middle name or null",
  "father_last_name": "Father last name",
  "mobile_number": "10 digits or null",
  "state": "State name",
  "city": "City or null",
  "gender": "Male/Female/Transgender or null",
  "dob": "DD/MM/YYYY or null",
  "confidence": "high/medium/low"
}

Rules: Raw JSON only. Null for missing. No extra text.
"""'''

AADHAAR_PROMPT = """
EExtract the below details and return ONLY valid JSON:

{
  "aadhar_number": "",
  "name": "",
  "first_name": "",
  "last_name": "",
  "middle_name": null,
  "father_name": "",
  "father_first_name": "",
  "father_middle_name": null,
  "father_last_name": "",
  "mobile_number":10 digits or null,
  "state": "",
  "city": "",
  "gender": "",
  "dob": "",
  "confidence": "low/medium/high depending on the quality of extraction"
}

Rules:
- Mobile number: Identify a valid Indian mobile number (10 digits, typically starting with 9).
- DOB: Identify the field labeled "DOB" or "Date of Birth"
- Father name may appear as S/O, C/O, D/O → remove prefix, extract only name
- City must be taken from VTC (Village/Town/City)
- Split names: first = first_name, last = last_name, rest = middle_name
- Use null if missing
- Output STRICT JSON only (no text, no markdown)
- Gender: Look for keywords like "Male", "Female", "M", "F", or similar indicators
"""
