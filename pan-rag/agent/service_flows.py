# agent/service_flows.py

# Every service the agent can handle
SERVICES = {
    "pan_apply_indian": {
        "name": "New PAN Card Application (Indian Citizen/Entity)",
        "form": "Form 49A",
        "steps": [
            "applicant_type",
            "personal_details",
            "documents",
            "photo",
            "summary",
        ],
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
        # Aadhaar covers all three proofs
        "smart_rules": {
            "aadhaar": ["identity_proof", "address_proof", "dob_proof"]
        },
    },

    "pan_apply_foreign": {
        "name": "New PAN Card Application (Foreign Citizen/Entity)",
        "form": "Form 49AA",
        "steps": [
            "applicant_type",
            "personal_details",
            "documents",
            "photo",
            "summary",
        ],
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
        "documents": {},  # No documents needed — just numbers
        "smart_rules": {},
    },

    "pan_verify": {
        "name": "PAN Verification",
        "form": "Online Verification",
        "steps": ["pan_number", "summary"],
        "documents": {},  # No documents needed
        "smart_rules": {},
    },
}


# Detect which service the user wants
SERVICE_KEYWORDS = {
    "pan_apply_indian": [
        "new pan", "apply pan", "apply for pan", "get pan", "fresh pan",
        "want pan", "need pan card", "make pan", "open pan",
    ],
    "pan_apply_foreign": [
        "foreign pan", "nri pan", "oci pan", "foreign national pan",
        "form 49aa", "non resident pan",
    ],
    "pan_reprint": [
        "reprint", "lost pan", "duplicate pan", "pan lost", "new card same pan",
        "pan card lost", "damaged pan", "replace pan card",
    ],
    "pan_correction": [
        "correction", "update pan", "change name", "change address",
        "wrong name", "wrong dob", "wrong date", "change date of birth",
        "pan correction", "modify pan", "edit pan",
    ],
    "aadhaar_link": [
        "link aadhaar", "aadhaar link", "link aadhar", "aadhar link",
        "link pan aadhaar", "aadhaar pan link", "connect aadhaar",
    ],
    "pan_verify": [
        "verify pan", "pan verify", "check pan", "validate pan",
        "is pan valid", "pan number check",
    ],
}


def detect_service(question: str) -> str | None:
    """Detect which PAN service the user wants."""
    q = question.lower()
    for service_id, keywords in SERVICE_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                return service_id
    return None


def get_service(service_id: str) -> dict:
    """Get service definition."""
    return SERVICES.get(service_id, {})