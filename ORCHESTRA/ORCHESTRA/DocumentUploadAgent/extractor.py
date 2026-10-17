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

    # Compress image before encoding with high quality and 1280x1280 to prevent OCR/VLM hallucinations
    img = img.convert("RGB")
    img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    img.save(buffer, format="JPEG", quality=88)

    return base64.b64encode(buffer.getvalue()).decode()


# keep run_vlm logic exactly as reference

def get_groq_keys():
    """Retrieve all available Groq API keys from environment variables for automatic failover."""
    keys = []
    raw_keys = os.getenv("GROQ_API_KEYS", "")
    if raw_keys:
        for k in raw_keys.split(","):
            k = k.strip()
            if k.startswith("gsk_") and k not in keys:
                keys.append(k)
    var_names = ["GROQ_API_KEY"] + [f"GROQ_API_KEY{i}" for i in range(1, 10)] + [f"GROQ_API_KEY_{i}" for i in range(1, 10)]
    for env_var in var_names:
        k = os.getenv(env_var, "").strip()
        if k.startswith("gsk_") and k not in keys:
            keys.append(k)
    return keys


def get_nvidia_keys():
    """Retrieve all available NVIDIA NIM API keys for automatic failover."""
    keys = []
    raw_keys = os.getenv("NVIDIA_API_KEYS", "")
    if raw_keys:
        for k in raw_keys.split(","):
            k = k.strip()
            if k.startswith("nvapi-") and k not in keys:
                keys.append(k)
    var_names = ["NVIDIA_META_11B", "NVIDIA_API_KEY"] + [f"NVIDIA_API_KEY{i}" for i in range(1, 10)] + [f"NVIDIA_API_KEY_{i}" for i in range(1, 10)]
    for env_var in var_names:
        k = os.getenv(env_var, "").strip()
        if k.startswith("nvapi-") and k not in keys:
            keys.append(k)
    return keys


def run_vlm(image, text_prompt):
    image_b64 = pil_to_base64(image)

    # NVIDIA NIM API with multi-key failover
    nvidia_keys = get_nvidia_keys()
    if nvidia_keys:
        invoke_url = config.NVIDIA_API_URL
        for idx, key in enumerate(nvidia_keys):
            headers = {
                "Authorization": f"Bearer {key}",
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
            try:
                res = requests.post(invoke_url, headers=headers, json=payload, timeout=60)
                if res.status_code == 200:
                    content = res.json()["choices"][0]["message"]["content"]
                    if content and content.strip():
                        print(f"[run_vlm] NVIDIA NIM VLM extraction success with Key #{idx+1}!")
                        return content
                else:
                    print(f"[run_vlm] NVIDIA NIM Key #{idx+1} returned status {res.status_code}: {res.text[:150]}")
            except Exception as ne:
                print(f"[run_vlm] NVIDIA NIM Key #{idx+1} call exception: {ne}")
                continue

    raise RuntimeError("All Groq and NVIDIA NIM VLM API keys exhausted or failed.")


# ------- Anti-hallucination sanitization & JSON helper -------

def sanitize_extracted_data(data: dict) -> dict:
    """Universal strict anti-hallucination post-processor and data sanitizer."""
    if not isinstance(data, dict):
        return data

    cert_type = str(data.get("certificate_type", "")).strip()

    # Clean strings and strip empty/null phrases
    _EMPTY_PHRASES = {
        "null", "none", "n/a", "na", "-", "--", "not available", "not found",
        "unknown", "nil", "undefined", "n.a.", "not applicable", "pending"
    }
    for k, v in list(data.items()):
        if isinstance(v, str):
            cleaned = v.strip()
            data[k] = "" if cleaned.lower() in _EMPTY_PHRASES else cleaned

    # 1. Name Sanitization: remove honorifics / prefixes and detect dummy / hallucinated values
    DUMMY_NAMES = {
        "john doe", "jane doe", "sample name", "test name", "dummy name",
        "test user", "applicant name", "full name", "name of applicant",
        "first name", "last name", "citizen name", "candidate name",
        "government of india", "unique identification authority", "uidai",
        "transport department", "civil supplies", "government", "india",
        "tamil nadu", "department", "certificate"
    }
    name = data.get("name", "")
    if name and isinstance(name, str):
        name = re.sub(r"^(?:Mr\.|Mrs\.|Ms\.|Shri|Smt\.?|Thiru|Selvi|To)\s+", "", name, flags=re.IGNORECASE)
        name = re.sub(r"[\.,]+$", "", name).strip()
        name = re.sub(r"\s+", " ", name)
        if name.lower() in DUMMY_NAMES or len(name) < 2 or bool(re.search(r"^\d+$", name)):
            data["name"] = ""
        else:
            data["name"] = name

    # 2. Father's Name Sanitization
    father_name = data.get("father_name", "")
    if father_name and isinstance(father_name, str):
        father_name = re.sub(r"^(?:C/O:?|S/O:?|D/O:?|W/O:?|Father(?:\x27s)?\s*Name:?)\s*", "", father_name, flags=re.IGNORECASE)
        father_name = re.sub(r"[\.,]+$", "", father_name).strip()
        father_name = re.sub(r"\s+", " ", father_name)
        # Father's name cannot be identical to the applicant name
        if name and father_name.lower() == name.lower():
            father_name = ""
        # Discard generic placeholder words or dummy names
        if father_name.lower() in DUMMY_NAMES or father_name.lower() in {"father", "name", "father name", "husband", "son", "daughter"}:
            father_name = ""
        data["father_name"] = father_name

    # 3. Aadhaar Number Sanitization & Strict Pattern Validation
    aadhaar_num = str(data.get("aadhaar_number", "")).strip()
    if aadhaar_num:
        m_adh = re.search(r"\b([X0-9]{4}\s*[X0-9]{4}\s*[0-9]{4})\b", aadhaar_num, re.IGNORECASE)
        if m_adh:
            clean_adh = re.sub(r"\s+", " ", m_adh.group(1)).upper()
            digits_only = re.sub(r"[^0-9]", "", clean_adh)
            DUMMY_AADHAAR = {
                "123456789012", "012345678901", "000000000000", "111111111111",
                "222222222222", "333333333333", "444444444444", "555555555555",
                "666666666666", "777777777777", "888888888888", "999999999999",
                "123412341234", "987654321098"
            }
            if digits_only in DUMMY_AADHAAR:
                data["aadhaar_number"] = ""
            else:
                parts = clean_adh.split()
                if len(parts) == 3:
                    data["aadhaar_number"] = f"{parts[0]} {parts[1]} {parts[2]}"
                elif len(digits_only) == 12:
                    data["aadhaar_number"] = f"{digits_only[:4]} {digits_only[4:8]} {digits_only[8:]}"
                else:
                    data["aadhaar_number"] = clean_adh
        else:
            data["aadhaar_number"] = ""

    # 4. PAN Number Sanitization
    pan_num = str(data.get("pan_number", "")).strip().upper()
    if pan_num:
        m_pan = re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan_num)
        if m_pan and not pan_num.startswith("XXXXX") and pan_num != "ABCDE1234F":
            data["pan_number"] = pan_num
        else:
            data["pan_number"] = ""

    # 5. DL Number Sanitization
    dl_num = str(data.get("dl_number", "")).strip()
    if dl_num:
        if len(dl_num) < 6 or dl_num.lower() in {"dl123456", "test", "dummy", "sample"}:
            data["dl_number"] = ""
        else:
            data["dl_number"] = re.sub(r"\s+", " ", dl_num)

    # 6. Pincode Sanitization: extract exact 6-digit Indian postal code & reject dummy codes
    pincode = str(data.get("pincode", "")).strip()
    if pincode:
        m_pin = re.search(r"\b([1-9][0-9]{5})\b", pincode)
        if m_pin:
            pin_val = m_pin.group(1)
            if pin_val in {"111111", "222222", "333333", "444444", "555555", "666666", "777777", "888888", "999999", "123456"}:
                data["pincode"] = ""
            else:
                data["pincode"] = pin_val
        else:
            data["pincode"] = ""

    # 7. DOB Normalization to DD/MM/YYYY & Boundary Validation (1920 - 2026)
    dob = str(data.get("dob", "")).strip()
    if dob:
        m_dob1 = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", dob)
        m_dob2 = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", dob)
        day, month, year = 0, 0, 0
        if m_dob1:
            d, m, y = m_dob1.groups()
            day, month, year = int(d), int(m), int(y)
        elif m_dob2:
            y, m, d = m_dob2.groups()
            day, month, year = int(d), int(m), int(y)

        if 1 <= day <= 31 and 1 <= month <= 12 and 1920 <= year <= 2026:
            data["dob"] = f"{day:02d}/{month:02d}/{year}"
        else:
            data["dob"] = ""

    # 8. Phone Number Sanitization
    phone = str(data.get("phone_number", "")).strip()
    if phone:
        digits = re.sub(r"[^0-9]", "", phone)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) == 10 and digits[0] in "6789":
            if digits in {"1234567890", "0000000000", "1111111111", "9999999999"}:
                data["phone_number"] = ""
            else:
                data["phone_number"] = digits
        else:
            data["phone_number"] = ""

    # 9. Gender Normalization
    gender = str(data.get("gender", "")).strip().lower()
    if gender in ["male", "m", "ஆண்"]:
        data["gender"] = "Male"
    elif gender in ["female", "f", "பெண்"]:
        data["gender"] = "Female"
    elif gender in ["transgender", "tg", "trans"]:
        data["gender"] = "Transgender"
    else:
        if "gender" in data and data["gender"]:
            data["gender"] = ""

    # 10. Anti-hallucination for Aadhaar / DL / PAN / Voter ID / Address Proof:
    # These documents never specify religion or community
    if any(t in cert_type.lower() for t in ["aadhaar", "driving", "pan", "voter", "address proof"]):
        if "religion" in data:
            data["religion"] = ""
        if "community" in data:
            data["community"] = ""

    # 11. Address hygiene: ensure father/applicant name or C/O are not echoed in door_no/street
    f_val = (data.get("father_name") or "").lower()
    n_val = (data.get("name") or "").lower()
    for addr_key in ["door_no", "street", "area", "city", "street_name", "building_no"]:
        val = str(data.get(addr_key, "")).strip()
        val_lower = val.lower()
        if (f_val and val_lower == f_val) or (n_val and val_lower == n_val) or any(bad in val_lower for bad in ["c/o", "s/o", "d/o", "w/o"]):
            data[addr_key] = ""

    # 12. Door No length and plausibility
    door = str(data.get("door_no", "")).strip()
    if door:
        if len(door) > 20 or any(bad in door.lower() for bad in ["father", "resident", "address", "india", "pincode", "district", "state"]):
            data["door_no"] = ""

    return data


def parse_vlm_output(text):
    """Safely convert the VLM text response into a Python dict and sanitize it."""
    if not text:
        raise ValueError("Empty VLM response")

    cleaned_text = text.strip()

    # 1. Strip markdown ```json ... ``` wrapper if present
    if "```" in cleaned_text:
        m_code = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned_text, re.IGNORECASE)
        if m_code:
            try:
                parsed = json.loads(m_code.group(1).strip())
                return sanitize_extracted_data(parsed)
            except Exception:
                pass

    # 2. Direct JSON parse
    try:
        parsed = json.loads(cleaned_text)
        return sanitize_extracted_data(parsed)
    except Exception:
        pass

    # 3. Find JSON object between outer braces { ... }
    start_idx = cleaned_text.find('{')
    end_idx = cleaned_text.rfind('}')
    if start_idx != -1 and end_idx > start_idx:
        json_candidate = cleaned_text[start_idx:end_idx+1]
        try:
            parsed = json.loads(json_candidate)
            return sanitize_extracted_data(parsed)
        except Exception:
            pass

    # 4. Narrative fallback — model returned prose instead of JSON.
    print("[parse_vlm_output] Narrative response detected — extracting fields via strict regex")
    result = {}
    _FIELDS = [
        "certificate_type", "name", "gender", "dob", "aadhaar_number",
        "father_name", "religion", "community", "address", "door_no",
        "street", "area", "city", "state", "district", "taluk",
        "pincode", "phone_number"
    ]

    for field in _FIELDS:
        variants = [re.escape(field), re.escape(f'"{field}"'), re.escape(field.replace("_", " "))]
        var_pat = "|".join(variants)
        # Pattern 1: field: "VALUE"
        p1 = rf'(?:^|[\n,{{])\s*(?:{var_pat})\s*[:\-]\s*"([^"\n]+)"'
        m1 = re.search(p1, cleaned_text, re.IGNORECASE)
        if m1:
            val = m1.group(1).strip()
            if val.lower() not in {"null", "none", "n/a", "not available"}:
                result[field] = val
                continue

        # Pattern 2: field: VALUE
        p2 = rf'(?:^|[\n,{{])\s*(?:{var_pat})\s*[:\-]\s*([^\n,}}]+)'
        m2 = re.search(p2, cleaned_text, re.IGNORECASE)
        if m2:
            val = m2.group(1).strip().strip('"').strip("'")
            if val.lower() not in {"null", "none", "n/a", "not available"}:
                result[field] = val
                continue

    # Special C/O extraction for father_name if missing
    if not result.get("father_name"):
        m3 = re.search(r"(?:C/O|S/O|D/O|W/O)[:\s]+([A-Za-z][^\n,]+)", cleaned_text, re.IGNORECASE)
        if m3:
            result["father_name"] = m3.group(1).strip()

    # Fallback: parse door_no, street, area from full address string if missing
    raw_addr = result.get("address", "")
    if raw_addr and isinstance(raw_addr, str):
        addr_parts = [p.strip() for p in raw_addr.split(",") if p.strip()]
        if addr_parts:
            if not result.get("door_no"):
                p0 = addr_parts[0]
                if not any(bad in p0.lower() for bad in ["c/o", "s/o", "d/o", "w/o"]):
                    result["door_no"] = p0
            if len(addr_parts) > 1 and not result.get("street"):
                p1 = addr_parts[1]
                if not any(bad in p1.lower() for bad in ["c/o", "s/o", "d/o", "w/o"]):
                    result["street"] = p1
            if len(addr_parts) > 2 and not result.get("area"):
                p2 = addr_parts[2]
                if not any(bad in p2.lower() for bad in ["c/o", "s/o", "d/o", "w/o"]):
                    result["area"] = p2

    if result:
        result.setdefault("certificate_type", "Aadhaar")
        sanitized = sanitize_extracted_data(result)
        print(f"[parse_vlm_output] Narrative extraction result: {sanitized}")
        return sanitized

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

    # Combined prompt: detect type and extract in one shot with strict anti-hallucination constraints
    COMBINED_PROMPT = """
Look at this document image and do two things in one response:

1. Identify the certificate type. Choose ONLY from:
   Aadhaar, Ration Card, Address Proof, PAN, Driving License,
   Voter ID, Caste Certificate, Residence Certificate, Income Certificate

2. Extract all relevant fields based on the type.

CRITICAL ANTI-HALLUCINATION RULES:
- Extract ONLY facts explicitly and visibly printed on the document image.
- NEVER guess, assume, estimate, or extrapolate any values.
- If any field is NOT explicitly visible on the document, set its value to "" (empty string).
- For Aadhaar, Driving License, PAN, or Voter ID cards, NEVER invent religion or community. Always set them to "".
- For father_name on Aadhaar: look for a line like "C/O: Name" or "S/O: Name" — extract only the name after the colon. NEVER set father_name equal to the applicant's own name.
- Return a single JSON object. Always include "certificate_type" as the first key.

For Aadhaar use keys: certificate_type, name, gender, dob, aadhaar_number, father_name, religion, community, address, door_no, street, area, city, state, district, taluk, pincode, phone_number
For Ration Card use keys: certificate_type, name, mother_name, number, district, taluk, state
For Driving License use keys: certificate_type, name, dob, dl_number, address, state, pincode
For Address Proof use keys: certificate_type, username, father_name, religion, community, door_no, address, street_name, pincode, from_date, to_date, state, district, taluk, count_of_residence_years
For PAN use keys: certificate_type, name, father_name, dob, pan_number
For Voter ID use keys: certificate_type, name, father_name, dob, voter_id
For Caste Certificate use keys: certificate_type, name, father_name, mother_name, dob, religion, community, caste, sub_caste, address, door_no, street, area, city, state, district, taluk, pincode, issued_date, issuing_authority
For Residence Certificate use keys: certificate_type, name, father_name, religion, community, gender, address, door_no, street, area, city, state, pincode, taluk
For Income Certificate use keys: certificate_type, name, father_name, religion, community, dob, address, income, issued_date, issuing_authority

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


# ---------- Deterministic Text Extractors ----------

def _extract_aadhaar_from_text(text: str) -> dict:
    data = {"certificate_type": "Aadhaar"}
    clean_text = text.replace("\t", " ")

    # Aadhaar Number
    m_num = re.search(r"\b([X0-9]{4}\s+[X0-9]{4}\s+[0-9]{4})\b", clean_text)
    if not m_num:
        m_num = re.search(r"\b([0-9]{4}\s+[0-9]{4}\s+[0-9]{4})\b", clean_text)
    if not m_num:
        m_num = re.search(r"\b([0-9]{12})\b", clean_text)
    if m_num:
        data["aadhaar_number"] = re.sub(r"\s+", " ", m_num.group(1)).strip()

    # DOB
    m_dob = re.search(r"(?:DOB|Birth|பிறந்த\s*நாள்)[:\s/]+([0-9]{2}[/-][0-9]{2}[/-][0-9]{4})", clean_text, re.IGNORECASE)
    if m_dob:
        data["dob"] = m_dob.group(1).replace("-", "/")

    # Gender
    m_gen = re.search(r"\b(MALE|FEMALE|TRANSGENDER|ஆண்|பெண்)\b", clean_text, re.IGNORECASE)
    if m_gen:
        g = m_gen.group(1).upper()
        data["gender"] = "Male" if g in ["MALE", "ஆண்"] else ("Female" if g in ["FEMALE", "பெண்"] else "Transgender")

    # Name
    m_name = re.search(r"To\s*\n[^\n]+\n([A-Za-z][A-Za-z\s\.]+)\n\s*(?:S/O|C/O|D/O|W/O)", text)
    if not m_name:
        m_name = re.search(r"([A-Za-z][A-Za-z\s\.]+)\s*\n[^\n]*DOB:", text)
    if m_name:
        data["name"] = re.sub(r"\s+", " ", m_name.group(1)).strip()

    # Father Name
    m_father = re.search(r"(?:S/O|C/O|D/O|W/O)[:\s]+([A-Za-z][A-Za-z\s\.]+?)(?:,|\n|\r|$)", clean_text)
    if m_father:
        data["father_name"] = m_father.group(1).strip()

    # Pincode
    m_pin = re.search(r"(?:PIN\s*Code|Pincode|Pin)[:\s]+([1-9][0-9]{5})", clean_text, re.IGNORECASE)
    if not m_pin:
        m_pin = re.search(r"\b([1-9][0-9]{5})\b", clean_text)
    if m_pin:
        data["pincode"] = m_pin.group(1)

    # State & District & Taluk
    m_dist = re.search(r"(?:District|Dist)[:\s]+([A-Za-z\s]+?)(?:,|\n|State|$)", clean_text, re.IGNORECASE)
    if m_dist:
        data["district"] = m_dist.group(1).strip()
    m_state = re.search(r"(?:State)[:\s]+([A-Za-z\s]+?)(?:,|\n|PIN|$)", clean_text, re.IGNORECASE)
    if m_state:
        data["state"] = m_state.group(1).strip()
    m_vtc = re.search(r"(?:VTC|Taluk)[:\s]+([A-Za-z\s]+?)(?:,|\n|PO:|$)", clean_text, re.IGNORECASE)
    if m_vtc:
        data["taluk"] = m_vtc.group(1).strip()

    # Address
    m_addr = re.search(r"Address:\s*([\s\S]+?)(?:\b\d{6}\b|XXXX\s*XXXX|$)", text)
    if m_addr:
        data["address"] = re.sub(r"\s+", " ", m_addr.group(1)).strip().rstrip(",")

    # Door No & Street
    m_door_street = re.search(r"(?:S/O:[^\n,]+,?\s*|\n)([0-9]+[A-Za-z\-/0-9]*)\s*,\s*([A-Za-z0-9\s]+?(?:NAGAR|STREET|ROAD|COLONY|LANE|SALAI|PURAM|PALAYAM|GRAMAM|AVENUE|GARDEN|LAYOUT|COMPLEX|KUPPAM))", clean_text, re.IGNORECASE)
    if not m_door_street:
        m_door_street = re.search(r"\n([0-9]+[A-Za-z\-/0-9]*)\n([A-Za-z0-9\s]+?(?:NAGAR|STREET|ROAD|COLONY|LANE|SALAI|PURAM|PALAYAM|GRAMAM|AVENUE|GARDEN|LAYOUT|COMPLEX|KUPPAM))", text, re.IGNORECASE)
    if m_door_street:
        data["door_no"] = m_door_street.group(1).strip()
        data["street"] = re.sub(r"\s+", " ", m_door_street.group(2)).strip()

    return sanitize_extracted_data(data)


def _extract_dl_from_text(text: str) -> dict:
    data = {"certificate_type": "Driving License"}
    clean_text = text.replace("\t", " ")

    # License No
    m_lic = re.search(r"License\s*No\.?\s*[:\s]+([A-Z0-9\s/-]+?)(?=\n|Date\s*of\s*Expiry|Valid|$)", clean_text, re.IGNORECASE)
    if m_lic:
        data["dl_number"] = re.sub(r"\s+", " ", m_lic.group(1)).strip()

    # Name
    m_name = re.search(r"Name\s*[:\s]+([A-Za-z\s\.]+?)(?=\n|DOB|Date\s*of\s*Birth|Blood|$)", clean_text)
    if m_name:
        data["name"] = re.sub(r"\s+", " ", m_name.group(1)).strip()

    # DOB
    m_dob = re.search(r"DOB\s*[:\s]+([0-9]{2}[/-][0-9]{2}[/-][0-9]{4})", clean_text, re.IGNORECASE)
    if m_dob:
        data["dob"] = m_dob.group(1).replace("-", "/")

    # Father Name / S/W/D
    m_swd = re.search(r"S/W/D\s*[:\s]+([A-Za-z\s\.]+?)(?=\n|Present\s*Address|Address|Permanent|$)", clean_text)
    if m_swd:
        data["father_name"] = re.sub(r"\s+", " ", m_swd.group(1)).strip()

    # Pincode
    m_pin = re.search(r"\b([1-9][0-9]{5})\b", clean_text)
    if m_pin:
        data["pincode"] = m_pin.group(1)

    # Address
    m_addr = re.search(r"(?:Present\s*Address|Address)\s*[:\s]+([\s\S]+?)(?=Permanent|Note|Powered|$)", clean_text)
    if m_addr:
        raw_addr = re.sub(r"\s+", " ", m_addr.group(1)).strip()
        data["address"] = raw_addr
        m_parts = re.search(r"^([0-9]+[A-Za-z\-/0-9]*)\s*,\s*([A-Za-z0-9\s]+?(?:NAGAR|STREET|ROAD|COLONY|LANE|SALAI|PURAM|PALAYAM|GRAMAM|AVENUE|GARDEN|LAYOUT|COMPLEX|KUPPAM))", raw_addr, re.IGNORECASE)
        if m_parts:
            data["door_no"] = m_parts.group(1).strip()
            data["street"] = re.sub(r"\s+", " ", m_parts.group(2)).strip()

    # State
    if "TAMIL NADU" in clean_text.upper():
        data["state"] = "Tamil Nadu"

    return sanitize_extracted_data(data)


def _extract_ration_from_text(text: str) -> dict:
    data = {"certificate_type": "Ration Card"}
    clean_text = text.replace("\t", " ")

    # Card / UFC No
    m_num = re.search(r"(?:Ration\s*Card\s*No|Card\s*No|UFC\s*No|Family\s*Card\s*No|எண்)[:\s]+([A-Z0-9/]+)", clean_text, re.IGNORECASE)
    if not m_num:
        m_num = re.search(r"\b([0-9]{2}/[A-Z0-9]/[0-9]{6,})\b", clean_text)
    if m_num:
        data["number"] = m_num.group(1).strip()
        data["ration_card_number"] = data["number"]

    # Name
    m_name = re.search(r"(?:Head\s*of\s*Family|Name|பெயர்|குடும்பத்தலைவர்)[:\s]+([A-Za-z\s\.]+)", clean_text)
    if m_name:
        data["name"] = re.sub(r"\s+", " ", m_name.group(1)).strip()

    m_dist = re.search(r"(?:District|மாவட்டம்)[:\s]+([A-Za-z\s]+)", clean_text)
    if m_dist:
        data["district"] = m_dist.group(1).strip()

    m_taluk = re.search(r"(?:Taluk|வட்டம்)[:\s]+([A-Za-z\s]+)", clean_text)
    if m_taluk:
        data["taluk"] = m_taluk.group(1).strip()

    return sanitize_extracted_data(data)


def _extract_pan_from_text(text: str) -> dict:
    data = {"certificate_type": "PAN"}
    clean_text = text.replace("\t", " ")

    # 10-character PAN
    m_pan = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", clean_text)
    if m_pan:
        data["pan_number"] = m_pan.group(1).strip()

    # DOB
    m_dob = re.search(r"(?:DOB|Date\s*of\s*Birth)[:\s/]+([0-9]{2}[/-][0-9]{2}[/-][0-9]{4})", clean_text, re.IGNORECASE)
    if m_dob:
        data["dob"] = m_dob.group(1).replace("-", "/")

    # Name and Father Name
    m_name = re.search(r"Name\s*[:\s]+([A-Za-z\s\.]+?)(?=\n|Father|$)", clean_text)
    if m_name:
        data["name"] = re.sub(r"\s+", " ", m_name.group(1)).strip()
    m_f = re.search(r"Father(?:\x27s)?\s*Name\s*[:\s]+([A-Za-z\s\.]+?)(?=\n|DOB|$)", clean_text)
    if m_f:
        data["father_name"] = re.sub(r"\s+", " ", m_f.group(1)).strip()

    return sanitize_extracted_data(data)


def _extract_general_cert_from_text(text: str) -> dict:
    clean_text = text.replace("\t", " ")
    u = clean_text.upper()
    data = {}

    if "INCOME" in u and ("CERTIFICATE" in u or "CERTFICATE" in u):
        data["certificate_type"] = "Income Certificate"
    elif "CASTE" in u or "COMMUNITY" in u:
        data["certificate_type"] = "Caste Certificate"
    elif "RESIDENCE" in u or "NATIVITY" in u:
        data["certificate_type"] = "Residence Certificate"
    else:
        return None

    # Name
    m_name = re.search(r"certify\s*that\s*(?:Thiru\s*/?\s*|Tmt\.?\s*/?\s*|Selvi\.?\s*/?\s*)*([A-Za-z\s\.]+?)(?=\.|\n|Son|Daughter|Wife|residing|$)", clean_text, re.IGNORECASE)
    if m_name:
        data["name"] = re.sub(r"[\.\s]+$", "", m_name.group(1)).strip()

    # Father Name
    m_f = re.search(r"(?:Son|Daughter|Wife)\s*/?\s*(?:Daughter|Wife)?\s*of\s*(?:Thiru|Tmt|Mr\.)?\s*([A-Za-z\s\.]+?)(?=\.|\n|residing|$)", clean_text, re.IGNORECASE)
    if m_f:
        data["father_name"] = re.sub(r"[\.\s]+$", "", m_f.group(1)).strip()

    if "PUDUCHERRY" in u:
        data["state"] = "Puducherry"
    elif "TAMIL NADU" in u:
        data["state"] = "Tamil Nadu"

    m_pin = re.search(r"\b([1-9][0-9]{5})\b", clean_text)
    if m_pin:
        data["pincode"] = m_pin.group(1)

    return sanitize_extracted_data(data)


def extract_deterministic_from_text(text: str) -> dict:
    """Detect document type and run deterministic regex extractor on digital text."""
    if not text or len(text.strip()) < 20:
        return None

    u = re.sub(r"\s+", " ", text).upper()
    if "ENROLMENT NO" in u or "AADHAAR" in u or "UIDAI" in u or re.search(r"\b[X0-9]{4}\s+[X0-9]{4}\s+[0-9]{4}\b", text):
        return _extract_aadhaar_from_text(text)
    elif "DRIVING LICENSE" in u or "UNION OF INDIA DRIVING" in u or "AUTHORIZATION TO DRIVE" in u or "DL NO" in u:
        return _extract_dl_from_text(text)
    elif "RATION" in u or "CIVIL SUPPLIES" in u or "FAMILY CARD" in u:
        return _extract_ration_from_text(text)
    elif "PERMANENT ACCOUNT NUMBER" in u or re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text):
        return _extract_pan_from_text(text)
    else:
        return _extract_general_cert_from_text(text)



def run_text_llm(text_content: str) -> dict:
    """Extract document fields from digital text using deterministic parsing with LLM fallback."""
    if not text_content or len(text_content.strip()) < 20:
        return None

    # First, run ultra-fast deterministic regex extraction (zero-latency, zero-hallucination)
    det = extract_deterministic_from_text(text_content)
    if det and det.get("name") and (det.get("aadhaar_number") or det.get("dl_number") or det.get("pincode") or det.get("dob")):
        print(f"[run_text_llm] Deterministic extraction succeeded for {det.get('certificate_type')}: {det.get('name')}")
        return det

    prompt = f"""You are a precise Indian government document data extraction system.
Extract all relevant fields from the following document text into a single JSON object.

CRITICAL ANTI-HALLUCINATION RULES:
1. Extract ONLY facts explicitly printed in the text below.
2. NEVER guess, assume, or extrapolate any values.
3. If any field is not explicitly printed in the text, you MUST return an empty string "".
4. Do NOT guess religion or community for Aadhaar, Driving License, PAN or Voter ID cards. Always set them to "".
5. For father_name on Aadhaar: extract ONLY the name following C/O or S/O. NEVER use the applicant's own name.

Keys to include:
certificate_type (e.g. "Aadhaar", "Driving License", "Ration Card", "PAN", "Income Certificate", "Caste Certificate", "Residence Certificate")
name
father_name
dob (DD/MM/YYYY)
gender
aadhaar_number
dl_number
pan_number
address
door_no
street
area
city
district
taluk
state
pincode

Document Text:
{text_content[:4000]}

Return ONLY the JSON object.
"""
    # Try NVIDIA NIM text completion
    nvidia_keys = get_nvidia_keys()
    for key in nvidia_keys:
        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": "meta/llama-3.2-11b-vision-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 500
            }
            res = requests.post(config.NVIDIA_API_URL, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                content = res.json()["choices"][0]["message"]["content"]
                parsed = parse_vlm_output(content)
                if parsed:
                    if det:
                        for k, v in det.items():
                            if v and not parsed.get(k):
                                parsed[k] = v
                    return sanitize_extracted_data(parsed)
        except Exception:
            continue

    # Try Groq API keys if configured
    groq_keys = get_groq_keys()
    for key in groq_keys:
        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 500
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                content = res.json()["choices"][0]["message"]["content"]
                parsed = parse_vlm_output(content)
                if parsed:
                    if det:
                        for k, v in det.items():
                            if v and not parsed.get(k):
                                parsed[k] = v
                    return sanitize_extracted_data(parsed)
        except Exception:
            continue

    # Fallback to deterministic extraction if LLM is offline or unconfigured
    if det:
        return sanitize_extracted_data(det)

    return None


def extract_from_pdf(pdf_input) -> list:
    """Extract data from a PDF (or image) from bytes, HTTP/Supabase URL, or file path.

    Operates completely in-memory without requiring local disk storage.
    Raises HTTPException(400) if invalid.
    """
    pdf_bytes = None

    if isinstance(pdf_input, bytes):
        pdf_bytes = pdf_input
    elif isinstance(pdf_input, str):
        if pdf_input.startswith("http://") or pdf_input.startswith("https://"):
            try:
                resp = requests.get(pdf_input, timeout=15)
                if resp.status_code == 200:
                    pdf_bytes = resp.content
            except Exception as e:
                print(f"[extractor] Failed to fetch document from URL '{pdf_input}': {e}")
        elif os.path.exists(pdf_input):
            try:
                with open(pdf_input, "rb") as f:
                    pdf_bytes = f.read()
            except Exception as e:
                print(f"[extractor] Failed to read local file '{pdf_input}': {e}")

    if not pdf_bytes:
        raise HTTPException(
            status_code=400,
            detail="Failed to read document content or invalid input source."
        )

    # Strictly reject non-PDF documents to eliminate OCR/vision hallucinations
    if not pdf_bytes.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents are accepted. Images (JPG, PNG) are not accepted to prevent extraction hallucination."
        )

    # 1. Fast path: Extract digital vector text directly using pypdf
    try:
        try:
            import pypdf
        except ImportError:
            for p in ["/home/devaprasath/.local/lib/python3.14/site-packages", "/home/devaprasath/.local/lib/python3.11/site-packages", "/usr/lib/python3.14/site-packages"]:
                if p not in sys.path:
                    sys.path.append(p)
            import pypdf

        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        extracted_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        if len(extracted_text.strip()) > 50:
            print(f"[extractor] Digital PDF text detected ({len(extracted_text)} chars). Using deterministic/text extraction.")
            # Run deterministic regex extraction first (zero hallucination, exact match)
            det = extract_deterministic_from_text(extracted_text)
            if det and det.get("name") and (det.get("aadhaar_number") or det.get("dl_number") or det.get("pincode") or det.get("dob")):
                print(f"[extractor] High-confidence deterministic extraction succeeded: {det.get('certificate_type')} -> {det.get('name')}")
                return [det]

            # LLM text completion fallback if deterministic missed critical fields
            raw_json = run_text_llm(extracted_text)
            if raw_json and raw_json.get("name"):
                print(f"[extractor] Text LLM extracted {raw_json.get('certificate_type')}: {raw_json.get('name')}")
                return [raw_json]
            elif det:
                return [det]
    except Exception as te:
        print(f"[extractor] Digital PDF text extraction fast-path skipped: {te}")

    # 2. Render PDF pages as high-resolution images for scanned documents
    try:
        from pdf2image import convert_from_bytes
        pages = convert_from_bytes(
            pdf_bytes,
            dpi=200,
            poppler_path=config.POPPLER_PATH
        )
    except Exception as exc:
        print(f"[extractor] pdf2image convert_from_bytes failed: {exc}")
        raise HTTPException(
            status_code=422,
            detail=f"PDF conversion failed: {exc}"
        )

    return _process_pages(pages)


