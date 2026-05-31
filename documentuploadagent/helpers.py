import os
import base64
import requests
from PIL import Image
from io import BytesIO
from pathlib import Path
import json
import tempfile
from pdf2image import convert_from_path
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POPPLER_PATH = r"D:\poppler\poppler-25.12.0\Library\bin"

def image_to_base64(image_path: str) -> str:
    """Convert image/PDF path to base64."""
    path = Path(image_path)
    
    temp_img_path = None
    img_path = image_path
    
    if path.suffix.lower() == '.pdf':
        try:
            pages = convert_from_path(image_path, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
            temp_fd, temp_img_path = tempfile.mkstemp(suffix='.jpg')
            pages[0].save(temp_img_path, 'JPEG', quality=95)
            os.close(temp_fd)
            img_path = temp_img_path
        except Exception as e:
            raise ValueError(f"PDF conversion failed: {str(e)}. Install poppler or use JPG/PNG.")
    
    with Image.open(img_path) as img:
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
    
    if temp_img_path:
        os.unlink(temp_img_path)
    
    return img_b64

def _parse_json_content(content: str) -> dict:
    """Extract JSON from model response, handling prose, markdown fences, or partial wrapping."""
    content = content.strip()
    # Strip ```json ... ``` or ``` ... ```
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    # If model added prose before/after, find the first { ... } block
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        content = content[start:end + 1]
    return json.loads(content)


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
        "model": "meta/llama-3.2-11b-vision-instruct",
        "temperature": 0,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a document OCR API. "
                    "You ONLY output raw JSON. "
                    "No explanations, no descriptions, no markdown, no prose. "
                    "Your entire response must be a single valid JSON object."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract the fields from this document image.\n"
                            "OUTPUT ONLY THE JSON OBJECT BELOW — fill in the values:\n\n"
                            + prompt
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                    }
                ]
            }
        ]
    }

    for attempt in range(3):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            # Log full error body before raising so we can see what went wrong
            if not response.ok:
                logger.error(f"NVIDIA HTTP {response.status_code}: {response.text[:500]}")
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            logger.info(f"NVIDIA raw response: {content[:300]}")
            return _parse_json_content(content)
        except json.JSONDecodeError as e:
            logger.warning(f"NVIDIA attempt {attempt+1} JSON parse failed: {e} | content: {content[:300]}")
            if attempt == 2:
                raise RuntimeError(f"NVIDIA returned non-JSON after retries: {content[:200]}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"NVIDIA attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise RuntimeError(f"NVIDIA failed after retries: {e}")
            time.sleep(2 ** attempt)

def run_vlm(prompt: str, image_path: str) -> dict:
    """Call NVIDIA NIM VLM."""
    image_b64 = image_to_base64(image_path)
    return call_nvidia(prompt, image_b64)

AADHAAR_PROMPT = """
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
"""

