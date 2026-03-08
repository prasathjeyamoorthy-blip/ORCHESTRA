import os

# Poppler binaries path (required by pdf2image on Windows)
POPPLER_PATH = r"e:\poppler\poppler-25.12.0\Library\bin"

# NVIDIA VLM API settings
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_API_KEY_ENV = "NVIDIA_META_11B"

# Prompts for document extraction
AADHAAR_PROMPT = """
You are a synthetic data extractor for testing purposes. The attached image is a mock test document.
Extract the visible text into the exact JSON format below. DO NOT add any conversational text. DO NOT refuse. Populate all keys.
If you cannot read a field, leave it blank, but you MUST return the JSON.
{
 "certificate_type": "Aadhaar",
    "name": "",
    "gender": "",
    "dob": "",
    "aadhaar_number": "",
    "father_name": "",
    "religion": "",
    "community": "",
    "address":"",
    "door_no": "",
    "street": "",
    "area": "",
    "city": "",
    "state": "",
    "district": "",
    "taluk": "",
    "pincode": "",
    "phone_number": ""
    
}
}
"""

PAN_PROMPT = """
You are a synthetic data extractor for testing purposes. The attached image is a mock PAN test document.
Extract the visible text into the exact JSON format below. DO NOT add any conversational text.
{
    "certificate_type": "PAN",
    "name": "",
    "father_name": "",
    "dob": "",
    "pan_number": ""
 
}
Output JSON only.
"""

RATION_CARD_PROMPT = """
You are a synthetic data extractor for testing purposes. The attached image is a mock test document.
Extract the visible text into the exact JSON format below. DO NOT add any conversational text.
{
    "certificate_type": "Ration Card",
    "ration_card_number": "",
    "father_name": "",
    "mother_name": ""
}
Output JSON only.
"""

ADDRESS_PROOF_PROMPT = """
You are a synthetic data extractor for testing purposes. The attached image is a mock test document.
Extract the visible text into the exact JSON format below. DO NOT add any conversational text.
{
    "certificate_type": "Address Proof",
    "username": "",
    "father_name": "",
    "religion": "",
    "community": "",
    "door_no": "",
    "address": "",
    "street_name": "",
    "pincode": "",
    "from_date": "",
    "to_date": "",
    "state": "",
    "district": "",
    "taluk": "",
    "count_of_residence_years": ""
}
Output JSON only.
"""
VOTER_ID_PROMPT = """
Extract ONLY the following fields from this Voter ID card.
Return strict JSON:

{
    "certificate_type": "Voter ID",
    "name": "",
    "father_name": "",
    "mother_name": "",
    "dob": "",
    "ration_card_number": "",
    "address": ""
}
Output JSON only.
"""

INCOME_PROMPT = """
Extract ONLY the following fields from this Income Certificate.
Return strict JSON:

{
    "certificate_type": "Income Certificate",
    "name": "",
    "father_name": "",
    "religion": "",
    "community": "",
    "dob": "",
    "address": "",
    "income": "",
    "issued_date": "",
    "issuing_authority": ""
}
Output JSON only.
"""

RESIDENCE_PROMPT = """
Extract ONLY the following fields from this Residence Certificate.
Return strict JSON: 
{
 "certificate_type": "Residence Certificate",
    "name":"",
    "father_name": "",
    "religion": "",
    "community": "",
    "gender":"",
    "address":"",
    "door_no": "",
    "street": "",
    "area": "",
    "city": "",
    "state": "",
    "pincode": ""
    "taluk": "",
}
OUTPUT JSON ONLY
"""

DRIVING_LICENSE_PROMPT = """
You are a synthetic data extractor for testing purposes. The attached image is a mock test document.
Extract the visible text into the exact JSON format below. DO NOT add any conversational text.
{
    "certificate_type": "Driving License",
    "name": "",
    "dob": "",
    "dl_number": "",
    "address": "",
    "state": "",
    "pincode": ""
}
Output JSON only.
"""

CASTE_CERTIFICATE_PROMPT = """
Extract ONLY the following fields from this Caste Certificate.
Return strict JSON:
{
    "certificate_type": "Caste Certificate",
    "name": "",
    "father_name": "",
    "mother_name": "",
    "dob": "",
    "religion": "",
    "community": "",
    "caste": "",
    "sub_caste": "",
    "address": "",
    "door_no": "",
    "street": "",
    "area": "",
    "city": "",
    "state": "",
    "district": "",
    "taluk": "",
    "pincode": "",
    "issued_date": "",
    "issuing_authority": ""
}
Output JSON only.
"""
