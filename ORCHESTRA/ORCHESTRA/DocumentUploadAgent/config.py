import os

# Poppler binaries path (required by pdf2image on Windows)
POPPLER_PATH = "/usr/bin" if os.name != "nt" else r"D:\Release-25.12.0-0\Release-25.12.0-0 (1)\poppler-25.12.0\Library\bin"
# NVIDIA VLM API settings
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_API_KEY_ENV = "NVIDIA_META_11B"

# Prompts for document extraction
AADHAAR_PROMPT = """
Extract the following fields from this Aadhaar card and return them as a JSON object only.
Do not include any explanation or steps — return only the JSON.

Note: for "father_name", the card has a line like "C/O: Arokiaraj" or "S/O: Arokiaraj" in the address block — extract only the name after the colon, not the prefix.

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
"""


PAN_PROMPT = r"""
Extract ONLY the following fields from this PAN card.
father_name = value captured by the pattern C/O:\s*([^\n,]+)
Return strict JSON:

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
Extract ONLY the following fields from this Ration Card image.
Return strict JSON only. Do not include any explanation.

{
    "certificate_type": "Ration Card",
    "name": "",
    "mother_name": "",
    "number": "",
    "district": "",
    "taluk": "",
    "state": ""
}
Output JSON only.
"""

ADDRESS_PROOF_PROMPT = """
Extract ONLY the following fields from this address document (Aadhaar or Driving License).
Return strict JSON:

{
    "certificate_type": "Aadhaar",
    "name": "",
    "father_name": "",
    "dob": "",
    "door_no": "",
    "address": "",
    "street": "",
    "pincode": "",
    "state": "",
    "district": "",
    "taluk": ""
}
Output JSON only.
"""

VOTER_ID_PROMPT = """
Extract ONLY the following fields from this Voter ID / Election Card.
Return strict JSON:

{
    "certificate_type": "Voter ID",
    "name": "",
    "father_name": "",
    "dob": "",
    "gender": "",
    "voter_id": "",
    "address": "",
    "state": "",
    "pincode": ""
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
    "name": "",
    "father_name": "",
    "religion": "",
    "community": "",
    "gender": "",
    "door_no": "",
    "address": "",
    "street": "",
    "area": "",
    "city": "",
    "state": "",
    "pincode": "",
    "taluk": ""
}
OUTPUT JSON ONLY
"""

DRIVING_LICENSE_PROMPT = """
Extract ONLY the following fields from this Driving License.
Return strict JSON:
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
