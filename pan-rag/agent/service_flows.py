# agent/service_flows.py
import re

SERVICES = {
    "pan_apply_indian": {
        "name": "New PAN Card Application (Indian Citizen/Entity)",
        "form": "Form 49A",
        "steps": ["applicant_type", "personal_details", "documents", "photo", "summary"],
        "documents": {
            "identity_proof": {
                "label": "Proof of Identity",
                "options": ["Aadhaar Card", "Passport", "Voter ID", "Driving License"],
                "count": 1,
            },
            "address_proof": {
                "label": "Proof of Address",
                "options": ["Aadhaar Card", "Passport", "Bank Statement (last 3 months)", "Utility Bill"],
                "count": 1,
            },
            "dob_proof": {
                "label": "Proof of Date of Birth",
                "options": ["Aadhaar Card", "Passport", "Birth Certificate", "Matriculation Certificate"],
                "count": 1,
            },
            "photograph": {
                "label": "Passport-size Photograph",
                "options": ["Recent passport-size photo (white background)"],
                "count": 1,
            },
        },
        "smart_rules": {"aadhaar": ["identity_proof", "address_proof", "dob_proof"]},
    },

    "pan_apply_foreign": {
        "name": "New PAN Card Application (Foreign Citizen/Entity)",
        "form": "Form 49AA",
        "steps": ["applicant_type", "personal_details", "documents", "photo", "summary"],
        "documents": {
            "identity_proof": {
                "label": "Proof of Identity",
                "options": ["Passport", "OCI Card", "PIO Card"],
                "count": 1,
            },
            "address_proof_foreign": {
                "label": "Proof of Foreign Address",
                "options": ["Passport", "Bank Statement from foreign bank", "NRE/NRO Bank Statement"],
                "count": 1,
            },
            "address_proof_india": {
                "label": "Proof of Indian Address (if any)",
                "options": ["Bank Statement", "Utility Bill", "Aadhaar Card"],
                "count": 1,
                "optional": True,
            },
            "photograph": {
                "label": "Passport-size Photograph",
                "options": ["Recent passport-size photo (white background)"],
                "count": 1,
            },
        },
        "smart_rules": {},
    },

    "pan_reprint": {
        "name": "PAN Card Reprint",
        "form": "Reprint Request",
        "steps": ["pan_number", "identity_verification", "summary"],
        "documents": {
            "identity_proof": {
                "label": "Proof of Identity",
                "options": ["Aadhaar Card", "Passport", "Voter ID"],
                "count": 1,
            },
        },
        "smart_rules": {},
    },

    "pan_correction": {
        "name": "PAN Card Correction / Update",
        "form": "Change Request Form",
        "steps": ["pan_number", "correction_type", "documents", "summary"],
        "documents": {
            "identity_proof": {
                "label": "Proof of Identity",
                "options": ["Aadhaar Card", "Passport", "Voter ID"],
                "count": 1,
            },
            "correction_proof": {
                "label": "Proof supporting correction",
                "options": [
                    "For name change: Marriage Certificate / Gazette",
                    "For DOB change: Birth Certificate / Passport",
                    "For address change: Utility Bill / Bank Statement",
                ],
                "count": 1,
            },
        },
        "smart_rules": {},
    },

    "aadhaar_link": {
        "name": "Aadhaar-PAN Linking",
        "form": "Online / SMS",
        "steps": ["pan_number", "aadhaar_number", "summary"],
        "documents": {},
        "smart_rules": {},
    },

    "pan_verify": {
        "name": "PAN Verification",
        "form": "Online Verification",
        "steps": ["pan_number", "summary"],
        "documents": {},
        "smart_rules": {},
    },
}


# ── Informational question guard ──────────────────────────────────────────────
_INFO_QUESTION_PATTERN = re.compile(
    r"^(why|what|how\s+does|how\s+is|what\s+is|what\s+are|"
    r"should\s+i|do\s+i\s+need|is\s+it|are\s+there|"
    r"tell\s+me|explain|describe|difference|benefit|reason|"
    r"purpose|importance|advantage|disadvantage|"
    r"when\s+should|when\s+do|who\s+should|who\s+needs|"
    r"what\s+happens|what\s+if|can\s+you\s+tell|"
    r"i\s+want\s+to\s+know|i\s+want\s+to\s+understand|"
    r"i\s+want\s+to\s+learn|curious\s+about|"
    r"what\s+documents|which\s+documents|documents\s+required|"
    r"how\s+long|how\s+much|what\s+is\s+the\s+fee|"
    r"how\s+many\s+days|processing\s+time)",
    re.IGNORECASE
)

def _is_informational(question: str) -> bool:
    return bool(_INFO_QUESTION_PATTERN.match(question.strip()))


# ── Service patterns ──────────────────────────────────────────────────────────
_SERVICE_PATTERNS = [
    ("pan_apply_foreign", re.compile(
        r"\b(foreign|nri|oci|pio|non.?resident|overseas)\b.{0,30}\bpan\b"
        r"|\bpan\b.{0,30}\b(foreign|nri|oci|pio|non.?resident|overseas)\b"
        r"|\bform\s*49\s*aa\b",
        re.IGNORECASE
    )),
    ("pan_apply_indian", re.compile(
        r"i\s+want\s+to\s+(apply|register|get|create|make|obtain).{0,20}pan"
        r"|i\s+need\s+to\s+(apply|register|get|create).{0,20}pan"
        r"|i\s+want\s+(a\s+)?(new\s+)?pan\b"
        r"|i\s+need\s+(a\s+)?(new\s+)?pan\b"
        r"|help\s+me\s+(apply|get|register|create).{0,20}pan"
        r"|apply\s+(for\s+)?(a\s+)?(new\s+)?pan\b"
        r"|register\s+(for\s+)?(a\s+)?pan\b"
        r"|get\s+(a\s+)?(new\s+)?pan\s*card\b"
        r"|create\s+(a\s+)?pan\b"
        r"|obtain\s+(a\s+)?pan\b"
        r"|enroll\s+(for\s+)?pan\b"
        r"|new\s+pan\s*(card)?\b"
        r"|fresh\s+pan\b"
        r"|first\s+time\s+pan\b"
        r"|pan\s*(card)?\s*(apply|application|registration)\b"
        r"|\bform\s*49\s*a\b(?!\s*a)",
        re.IGNORECASE
    )),
    ("pan_reprint", re.compile(
        r"\b(reprint|re.?print|lost|misplaced|damaged|stolen|"
        r"duplicate|replace|replacement)\b.{0,30}\bpan\b"
        r"|\bpan\b.{0,30}\b(lost|misplaced|damaged|stolen|reprint|duplicate|replace)\b",
        re.IGNORECASE
    )),
    ("pan_correction", re.compile(
        r"\b(correct|correction|update|change|modify|edit|fix|wrong|"
        r"mistake|error|amend)\b.{0,40}\bpan\b"
        r"|\bpan\b.{0,40}\b(correct|correction|update|change|modify|edit|fix|wrong)\b"
        r"|\b(name\s+change|address\s+change|dob\s+change|date\s+of\s+birth\s+change)\b",
        re.IGNORECASE
    )),
    # aadhaar_link and pan_verify intentionally excluded — handled by RAG only
]


def detect_service(question: str) -> str | None:
    q = question.strip()
    if _is_informational(q):
        return None
    for service_id, pattern in _SERVICE_PATTERNS:
        if pattern.search(q):
            return service_id
    return None


def get_service(service_id: str) -> dict:
    return SERVICES.get(service_id, {})