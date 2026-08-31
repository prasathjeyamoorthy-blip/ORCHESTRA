import os
import sys
import re
import json
import base64
from io import BytesIO

from pdf2image import convert_from_path
from PIL import Image
import requests
from dotenv import load_dotenv
from fastapi import HTTPException

import config
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)


# ---------- PDF validation ----------

PDF_MAGIC = b"%PDF-"

def _is_valid_pdf(path: str) -> bool:
    """Check the file starts with the PDF magic bytes."""
    try:
        with open(path, "rb") as f:
            return f.read(5) == PDF_MAGIC
    except Exception:
        return False


def _is_image_file(path: str) -> bool:
    """Return True if PIL can open the file as an image."""
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


# ---------- helper functions ----------

def get_image_resolution(pil_image):
    """Get the resolution of a PIL image.
    
    Returns:
        dict: Contains width, height, and total_pixels (area)
    """
    width, height = pil_image.size
    return {
        "width": width,
        "height": height,
        "total_pixels": width * height,
        "aspect_ratio": width / height if height > 0 else 0
    }


# HTTP Session with connection pooling for fast repeated VLM calls
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


def pil_to_base64(img):
    buffer = BytesIO()

    # Compress image before encoding (VERY IMPORTANT)
    img = img.convert("RGB")
    img.thumbnail((512, 512))  # optimal size (12k vision tokens) to stay well under 100k TPM rate limit
    img.save(buffer, format="JPEG", quality=75)

    return base64.b64encode(buffer.getvalue()).decode()


# keep run_vlm logic exactly as reference

def run_vlm(image, text_prompt):
    image_b64 = pil_to_base64(image)
    groq_key = os.getenv("GROQ_API_KEY")

    # Try Groq ultra-fast LPU Vision API first if key available
    if groq_key and groq_key.startswith("gsk_"):
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "qwen/qwen3.6-27b",
            "reasoning_format": "hidden",
            "temperature": 0,
            "max_tokens": 450,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ]
        }

        # Try up to 3 times with short sleep if 429 rate limit is hit
        for attempt in range(3):
            try:
                res = requests.post(groq_url, headers=headers, json=payload, timeout=90)
                if res.status_code == 200:
                    content = res.json()["choices"][0]["message"]["content"]
                    if content and content.strip():
                        print(f"[run_vlm] Groq VLM extraction success! (Attempt {attempt+1})")
                        return content
                elif res.status_code == 429:
                    print(f"[run_vlm] Groq VLM 429 rate limit, waiting 2.5s before retry {attempt+1}/3...")
                    import time
                    time.sleep(2.5)
                else:
                    print(f"[run_vlm] Groq VLM returned status {res.status_code}: {res.text[:150]}")
                    break
            except Exception as ge:
                print(f"[run_vlm] Groq VLM call exception (attempt {attempt+1}): {ge}")
                import time
                time.sleep(1.5)

    # Fallback to NVIDIA NIM API
    invoke_url = config.NVIDIA_API_URL
    headers = {
        "Authorization": f"Bearer {os.getenv('NVIDIA_META_11B')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama-3.2-11b-vision-instruct",
        "temperature": 0,
        "max_tokens": 450,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ]
    }
    
    response = requests.post(
        invoke_url,
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


# ------- JSON helper -------

def parse_vlm_output(text):
    """Safely convert the VLM text response into a Python dict."""
    # 1. Direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Find a JSON block anywhere in the text
    json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except Exception:
            pass

    # 3. Strip and retry
    cleaned = text.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 4. Extract after "Here is the output in JSON format:"
    if "Here is the output in JSON format:" in text:
        try:
            json_part = text.split("Here is the output in JSON format:")[-1].strip()
            return json.loads(json_part)
        except Exception:
            pass

    # 5. Narrative fallback — model returned prose instead of JSON.
    #    Extract key field values from natural-language sentences.
    print("[parse_vlm_output] Narrative response detected — extracting fields via regex")
    result = {}
    _FIELDS = [
        "certificate_type", "name", "gender", "dob", "aadhaar_number",
        "father_name", "religion", "community", "address", "door_no",
        "street", "area", "city", "state", "district", "taluk",
        "pincode", "phone_number"
    ]
    for field in _FIELDS:
        # pattern: field_name is "VALUE" or field_name: VALUE
        pattern = rf'"{field}"\s*[:\-]\s*"([^"]+)"'
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result[field] = m.group(1).strip()
            continue
        # looser: "the X is VALUE" sentences
        label = field.replace("_", "[ _]?")
        m2 = re.search(rf'{label}[^\w]*(?:is|:)\s*["\']?([A-Za-z0-9][^,\n"\'\.]+)', text, re.IGNORECASE)
        if m2:
            result[field] = m2.group(1).strip()

    # Special C/O extraction for father_name if still missing
    if not result.get("father_name"):
        m3 = re.search(r"(?:C/O|S/O|D/O|W/O)[:\s]+([A-Za-z][^\n,]+)", text, re.IGNORECASE)
        if m3:
            result["father_name"] = m3.group(1).strip()

    if result:
        result.setdefault("certificate_type", "Aadhaar")
        print(f"[parse_vlm_output] Narrative extraction result: {result}")
        return result

    raise ValueError(f"Failed to parse VLM output as JSON: {text}")


# ---------- extraction logic ----------


def detect_certificate_type(image):
    prompt = """
    Identify the certificate type from this image.
    Return ONLY one word or two-word phrase from:
    Aadhaar
    Ration Card
    Address Proof
    PAN
    Residence Certificate
    Income Certificate
    Caste Certificate
    Driving License
    Voter ID
    """

    result = run_vlm(image, prompt)
    # normalize answer to make matching robust
    text = result.strip().rstrip('.').strip().lower()
    if "aadhaar" in text:
        return "Aadhaar"
    if "ration" in text:
        return "Ration Card"
    if "address proof" in text or ("address" in text and "proof" in text):
        return "Address Proof"
    if "pan" in text:
        return "PAN"
    if "voter" in text:
        return "Voter ID"
    if "income" in text and "certificate" in text:
        return "Income Certificate"
    if "residence" in text:
        return "Residence Certificate"
    if "caste" in text:
        return "Caste Certificate"
    if "driving" in text or "dl" in text:
        return "Driving License"
    # fallback to raw stripped text
    return result.strip().rstrip('.').strip()


def _process_pages(pages: list) -> list:
    """Run VLM extraction on a list of PIL page images.
    
    Uses a single combined VLM call per page to detect certificate type
    AND extract fields simultaneously, halving the number of API calls.
    """
    outputs = []

    # Combined prompt: detect type and extract in one shot
    COMBINED_PROMPT = """
Look at this document image and do two things in one response:

1. Identify the certificate type. Choose ONLY from:
   Aadhaar, Ration Card, Address Proof, PAN, Driving License,
   Voter ID, Caste Certificate, Residence Certificate, Income Certificate

2. Extract all relevant fields based on the type.

Return a single JSON object. Always include "certificate_type" as the first key.

For Aadhaar use keys: certificate_type, name, gender, dob, aadhaar_number, father_name, religion, community, address, door_no, street, area, city, state, district, taluk, pincode, phone_number
For Ration Card use keys: certificate_type, name, mother_name, number, district, taluk, state
For Driving License use keys: certificate_type, name, dob, dl_number, address, state, pincode
For Address Proof use keys: certificate_type, username, father_name, religion, community, door_no, address, street_name, pincode, from_date, to_date, state, district, taluk, count_of_residence_years
For PAN use keys: certificate_type, name, father_name, dob, pan_number
For Voter ID use keys: certificate_type, name, father_name, dob, voter_id
For Caste Certificate use keys: certificate_type, name, father_name, mother_name, dob, religion, community, caste, sub_caste, address, door_no, street, area, city, state, district, taluk, pincode, issued_date, issuing_authority
For Residence Certificate use keys: certificate_type, name, father_name, religion, community, gender, address, door_no, street, area, city, state, pincode, taluk
For Income Certificate use keys: certificate_type, name, father_name, religion, community, dob, address, income, issued_date, issuing_authority

Note: for father_name on Aadhaar, look for a line like "C/O: Name" or "S/O: Name" — extract only the name after the colon.

Return ONLY the JSON object. No explanation.
"""

    _REFUSAL_PHRASES = ["i'm sorry", "i cannot", "i can't assist", "i am unable", "cannot assist"]
    _MISSING = {"", "not available", "n/a", "na", "none", "null", "-", "not found"}

    for i, page in enumerate(pages):
        print(f"Processing page {i+1}")

        resolution = get_image_resolution(page)
        print(f"Page resolution: {resolution['width']}x{resolution['height']} (total pixels: {resolution['total_pixels']})")

        try:
            # Single combined VLM call — detects type and extracts fields together
            raw = run_vlm(page, COMBINED_PROMPT)
            cert_type = "Unknown"

            # Refusal detection: retry with minimal prompt
            if any(p in raw.lower() for p in _REFUSAL_PHRASES):
                print(f"[VLM] Refusal detected, retrying with minimal prompt...")
                _minimal = (
                    "Read the text on this card image and return a JSON object with these keys: "
                    "certificate_type, name, gender, dob, aadhaar_number, father_name (the name after C/O: or S/O:), "
                    "address, door_no, street, area, city, state, district, taluk, pincode, phone_number. "
                    "Return only the JSON."
                )
                raw = run_vlm(page, _minimal)

            data = parse_vlm_output(raw)
            cert_type = data.get("certificate_type", "Unknown")
            print("Detected:", cert_type)

            # --- Aadhaar: two-stage fallback for father_name ---
            _current = data.get("father_name", "") or ""
            if "aadhaar" in cert_type.lower() and _current.strip().lower() in _MISSING:

                # Stage 1: regex on raw VLM text
                _match = re.search(r"(?:C/O|S/O|D/O|W/O|Father|Father\s*Name)[:\s]+([^\n,\"{}]+)", raw, re.IGNORECASE)
                if _match:
                    _candidate = _match.group(1).strip().strip('"').strip("'")
                    if _candidate.lower() not in _MISSING:
                        data["father_name"] = _candidate
                        print(f"[regex fallback] father_name → {data['father_name']}")

                # Stage 2: targeted VLM call directly on the image
                if (data.get("father_name") or "").strip().lower() in _MISSING:
                    _father_prompt = (
                        "Look at this Aadhaar card image carefully.\n"
                        "Find the line that contains C/O or S/O or D/O or W/O followed by a name.\n"
                        "Return ONLY that name as plain text — no labels, no explanation, no punctuation.\n"
                        "For example if the card shows 'C/O: Arokiaraj' just return: Arokiaraj"
                    )
                    try:
                        _father_raw = run_vlm(page, _father_prompt)
                        print(f"[DEBUG] VLM fallback raw response: {repr(_father_raw)}")
                        _father_raw = _father_raw.strip().strip('"').strip("'")
                        if _father_raw and _father_raw.lower() not in _MISSING:
                            data["father_name"] = _father_raw
                            print(f"[VLM fallback] father_name → {data['father_name']}")
                        else:
                            print(f"[VLM fallback] response still missing: {repr(_father_raw)}")
                    except Exception as _fe:
                        print(f"[father_name VLM fallback failed]: {_fe}")

            data["_resolution"] = resolution
            outputs.append(data)

        except Exception as e:
            print(f"Error processing page {i+1}: {e}")

    return outputs


def run_text_llm(text_content: str) -> dict:
    prompt = f"""
Look at this document text and extract all relevant fields.

1. Identify the certificate type. Choose ONLY from:
   Aadhaar, Ration Card, Address Proof, PAN, Driving License,
   Voter ID, Caste Certificate, Residence Certificate, Income Certificate

2. Extract all relevant fields based on the type.

Return a single JSON object. Always include "certificate_type" as the first key.

For Aadhaar use keys: certificate_type, name, gender, dob, aadhaar_number, father_name, religion, community, address, door_no, street, area, city, state, district, taluk, pincode, phone_number
For Ration Card use keys: certificate_type, name, mother_name, number, district, taluk, state
For Driving License use keys: certificate_type, name, dob, dl_number, address, state, pincode
For Address Proof use keys: certificate_type, username, father_name, religion, community, door_no, address, street_name, pincode, from_date, to_date, state, district, taluk, count_of_residence_years
For PAN use keys: certificate_type, name, father_name, dob, pan_number
For Voter ID use keys: certificate_type, name, father_name, dob, voter_id

Return ONLY the JSON object. No explanation.

Document Text:
{text_content}
"""
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key.startswith("gsk_"):
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "temperature": 0,
                "max_tokens": 450,
                "messages": [{"role": "user", "content": prompt}]
            }
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                return parse_vlm_output(res.json()["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"[run_text_llm] Groq text LLM failed: {e}")
    return None


def extract_from_pdf(pdf_path: str) -> list:
    """Extract data from a PDF (or image) file.

    Raises HTTPException(400) if the file is neither a valid PDF nor a
    recognisable image, so callers get a clear error instead of a 500.
    """
    # --- validate the file first ---
    if _is_valid_pdf(pdf_path):
        # Fast path: Try extracting digital text directly using pypdf
        try:
            try:
                import pypdf
            except ImportError:
                for p in ["/home/devaprasath/.local/lib/python3.14/site-packages", "/home/devaprasath/.local/lib/python3.11/site-packages", "/usr/lib/python3.14/site-packages"]:
                    if p not in sys.path:
                        sys.path.append(p)
                import pypdf

            reader = pypdf.PdfReader(pdf_path)
            extracted_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            if len(extracted_text.strip()) > 50:
                print(f"[extractor] Digital PDF text detected ({len(extracted_text)} chars). Using fast LLM text extraction.")
                raw_json = run_text_llm(extracted_text)
                if raw_json:
                    return [raw_json]
        except Exception as te:
            print(f"[extractor] Digital PDF text extraction fast-path skipped: {te}")

        try:
            pages = convert_from_path(
                pdf_path,
                dpi=200,
                poppler_path=config.POPPLER_PATH
            )
        except Exception as exc:
            print(f"[extractor] pdf2image failed even for a valid PDF: {exc}")
            raise HTTPException(
                status_code=422,
                detail=f"PDF conversion failed: {exc}"
            )
    elif _is_image_file(pdf_path):
        # File is actually an image (JPG/PNG/etc.) – open it directly
        print("[extractor] File is an image, not a PDF – processing as single page image.")
        pages = [Image.open(pdf_path).convert("RGB")]
    else:
        # Not a PDF and not a recognisable image
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file is not a valid PDF or recognised image. "
                "Please upload a proper PDF document."
            )
        )

    return _process_pages(pages)
