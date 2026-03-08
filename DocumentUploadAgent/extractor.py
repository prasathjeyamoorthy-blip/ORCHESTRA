import os
import json
import base64
from io import BytesIO

from pdf2image import convert_from_path
from PIL import Image
import requests
from dotenv import load_dotenv

import config
load_dotenv()


# ---------- helper functions ----------

def pil_to_base64(img):
    buffer = BytesIO()

    # Compress image before encoding (VERY IMPORTANT)
    img = img.convert("RGB")
    img.thumbnail((1400, 1400))  # reduce size safely
    img.save(buffer, format="JPEG", quality=70)

    return base64.b64encode(buffer.getvalue()).decode()


# keep run_vlm logic exactly as reference

def run_vlm(image, text_prompt):

    invoke_url = config.NVIDIA_API_URL

    headers = {
        "Authorization": f"Bearer {os.getenv('NVIDIA_META_11B')}",
        "Content-Type": "application/json"
    }

    image_b64 = pil_to_base64(image)

    payload = {
        "model": "meta/llama-3.2-11b-vision-instruct",
        "temperature": 0,
        "max_tokens": 400,
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

import re

def parse_vlm_output(text):
    """Safely convert the VLM text response into a Python dict."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip()
        
        # Extract JSON blocks using regex
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except Exception:
                pass
                
        # Try to find just the outermost braces
        brace_match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(1).strip())
            except Exception:
                pass
                
        # --- Extreme Fallback: Parse Markdown Bullet Points ---
        fallback_dict = {}
        for line in cleaned.split('\n'):
            line = line.strip()
            # Match formats like "* **Aadhaar Number**: 6071 2653 0111" or "Name: Lohith"
            match = re.match(r'^[\*\-\s]*\**([a-zA-Z0-9\s\(\)\_\-]+)\**:\s*(.*)$', line)
            if match:
                key = match.group(1).strip().lower().replace(' ', '_')
                val = match.group(2).strip()
                # strip trailing/leading markdown bolding from value just in case
                if val.startswith('**') and val.endswith('**'): val = val[2:-2].strip()
                fallback_dict[key] = val
                
        if fallback_dict:
            # Map standard keys back to our JSON Schema expected by Frontend/Config
            mapped_dict = {}
            for k, v in fallback_dict.items():
                if 'certificate' in k and 'type' in k: mapped_dict['certificate_type'] = v
                elif 'aadhaar' in k and 'number' in k: mapped_dict['aadhaar_number'] = v
                elif ('dob' in k or 'birth' in k): mapped_dict['dob'] = v
                elif 'name' in k and 'father' not in k and 'mother' not in k: mapped_dict['name'] = v
                if k not in mapped_dict: mapped_dict[k] = v
            return mapped_dict
                
        raise ValueError(f"Failed to parse VLM output as JSON: {text}")


# ---------- extraction logic ----------


def detect_certificate_type(image):
    prompt = """
    Carefully identify the certificate type out of the following options:
    - Aadhaar
    - Ration Card (Look for "Food and Civil Supplies" or family member tables)
    - Address Proof
    - PAN
    - Residence Certificate
    - Income Certificate
    - Driving License
    - Voter ID (Look for "Election Commission of India")

    Return ONLY the exact name from the list above. Do not include any other words.
    """

    result = run_vlm(image, prompt)
    # normalize answer to make matching robust
    text = result.strip().rstrip('.').strip().lower()
    
    # Strict checks for the easily confused ones first:
    if "election" in text or "voter" in text:
        return "Voter ID"
    if "ration" in text or "food" in text or "civil supplies" in text:
        return "Ration Card"

    if "aadhaar" in text:
        return "Aadhaar"
    if "address proof" in text or ("address" in text and "proof" in text):
        return "Address Proof"
    if "pan" in text:
        return "PAN"
    if "income" in text and "certificate" in text:
        return "Income Certificate"
    if "residence" in text:
        return "Residence Certificate"
    # if "caste" in text:
    #     return "Caste Certificate"
    if "driving" in text or "dl" in text:
        return "Driving License"
    # fallback to raw stripped text
    return result.strip().rstrip('.').strip()


def extract_from_pdf(file_path):
    pages = []

    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.pdf']:
        # Convert PDF to images
        pages = convert_from_path(
            file_path,
            dpi=200,
            poppler_path=config.POPPLER_PATH
        )
    elif ext in ['.jpg', '.jpeg', '.png']:
        # Directly open the image
        try:
            img = Image.open(file_path)
            # Ensure it is in RGB format for consistency
            img = img.convert("RGB")
            pages.append(img)
        except Exception as e:
            print(f"Failed to open image file {file_path}: {e}")
            raise
    else:
        print(f"Unsupported file extension: {ext}")
        return []

    outputs = []

    for i, page in enumerate(pages):
        print(f"Processing page {i+1}")

        try:
            cert_type = detect_certificate_type(page)
            print("Detected:", cert_type)

            # select prompt
            if cert_type == "Aadhaar":
                raw = run_vlm(page, config.AADHAAR_PROMPT)
            elif cert_type == "Ration Card":
                raw = run_vlm(page, config.RATION_CARD_PROMPT)
            elif cert_type == "Address Proof":
                raw = run_vlm(page, config.ADDRESS_PROOF_PROMPT)
            elif cert_type == "PAN":
                raw = run_vlm(page, config.PAN_PROMPT)
            elif cert_type == "Voter ID":
                raw = run_vlm(page, config.VOTER_ID_PROMPT)
            # elif cert_type in ("Caste", "Caste Certificate"):
            #     raw = run_vlm(page, config.CASTE_CERTIFICATE_PROMPT)
            elif cert_type == "Residence":
                raw = run_vlm(page, config.RESIDENCE_PROMPT)
            elif cert_type == "Driving License":
                raw = run_vlm(page, config.DRIVING_LICENSE_PROMPT)
            else:
                # unknown/other
                raw = '{"certificate_type": "Other", "extracted_fields": {}}'

            data = parse_vlm_output(raw)
            outputs.append(data)

        except Exception as e:
            print(f"Error processing page {i+1}: {e}")

    return outputs
