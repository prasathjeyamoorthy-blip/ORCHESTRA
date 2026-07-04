# agent/service_flows.py
import re

SERVICES = {
    "pan_apply_indian": {
        "name": "New PAN Card Application (Indian Citizen/Entity)",
        "form": "Form 49A",
        "steps": ["applicant_type", "submission_mode", "delivery_mode", "aadhaar_photo", "source_of_income", "address_for_comm", "residential_status", "rep_assessee", "details_collection", "confirmation", "documents", "summary"],
        "documents": {
            "aadhaar": {
                "label": "Aadhaar Card",
                "options": ["Aadhaar Card (front & back scan or photo)"],
                "count": 1,
            },
            "photograph": {
                "label": "Applicant Photograph",
                "options": ["Recent passport-size photo (white background, no sunglasses)"],
                "count": 1,
            },
            "signature": {
                "label": "Applicant Signature",
                "options": ["Signature on white paper (scanned or photo)"],
                "count": 1,
            },
            "driving_license": {
                "label": "Driving License",
                "options": ["Valid Driving License (front side) - Optional, used as age proof"],
                "count": 1,
                "optional": True,
            },
        },
        # No smart rules — all 3 docs are mandatory and distinct
        "smart_rules": {},
    },

    "pan_apply_foreign": {
        "name": "New PAN Card Application (Foreign Citizen/Entity)",
        "form": "Form 49AA",
        "steps": ["applicant_type", "documents", "summary"],
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
# NOTE: "how to apply / how do I apply" are ACTION intents, not informational — excluded here
_INFO_QUESTION_PATTERN = re.compile(
    r"^(why|what\s+is|what\s+are|what\s+documents|which\s+documents|"
    r"how\s+does|how\s+is|how\s+long|how\s+much|how\s+many\s+days|"
    r"should\s+i|do\s+i\s+need|is\s+it|are\s+there|"
    r"tell\s+me|explain|describe|difference|benefit|reason|"
    r"purpose|importance|advantage|disadvantage|"
    r"when\s+should|when\s+do|who\s+should|who\s+needs|"
    r"what\s+happens|what\s+if|can\s+you\s+tell|"
    r"i\s+want\s+to\s+know|i\s+want\s+to\s+understand|"
    r"i\s+want\s+to\s+learn|curious\s+about|"
    r"documents\s+required|"
    r"what\s+is\s+the\s+fee|processing\s+time)",
    re.IGNORECASE
)

def _is_informational(question: str) -> bool:
    q = question.strip()
    # "how to apply", "how do I apply", "how can I apply" → action intent, NOT informational
    _HOW_TO_APPLY = re.compile(
        r"^how\s+(to|do\s+i|can\s+i|do\s+we|should\s+i)\s+(apply|register|get|create|obtain|start|begin|proceed)",
        re.IGNORECASE
    )
    if _HOW_TO_APPLY.match(q):
        return False
    return bool(_INFO_QUESTION_PATTERN.match(q))


# ── Service patterns ──────────────────────────────────────────────────────────
_SERVICE_PATTERNS = [
    # Only Indian citizen PAN application triggers the guided flow + upload panel
    ("pan_apply_indian", re.compile(
        # ── Standard intent + action + pan ───────────────────────────────────
        r"i\s+(want|wanna|wana)\s+(to\s+)?(apply|register|get|create|make|obtain|have)\s.{0,15}\bpan\b"
        r"|i\s+(want|wanna|wana)\s+(to\s+)?(apply|register|get|create|make|obtain|have)\s+(for\s+)?(a\s+)?(new\s+)?\bpan\b"
        r"|i\s+need\s+to\s+(apply|register|get|create)\s.{0,15}\bpan\b"
        r"|i\s+(want|wanna|wana)\s+(a\s+)?(new\s+)?pan\b"
        r"|i\s+need\s+(a\s+)?(new\s+)?pan\b"
        r"|help\s+me\s+(apply|get|register|create)\s.{0,15}\bpan\b"
        r"|apply\s+(for\s+)?(a\s+)?(new\s+)?pan\b"
        r"|register\s+(for\s+)?(a\s+)?pan\b"
        r"|get\s+(a\s+)?(new\s+)?pan\b"
        r"|create\s+(a\s+)?pan\b"
        r"|obtain\s+(a\s+)?pan\b"
        r"|enroll\s+(for\s+)?pan\b"
        r"|new\s+pan\s*(card)?\b"
        r"|fresh\s+pan\b"
        r"|first\s+time\s+pan\b"
        r"|pan\s+(card\s+)?(apply|application|registration|banao|banana|chahiye|venum|edukkanum|thaa|tharuvai)\b"
        r"|\bform\s*49\s*a\b(?!\s*a)"
        # "how to apply for pan"
        r"|how\s+(to|do\s+i|can\s+i|do\s+we|should\s+i)\s+(apply|register|get|create|obtain|start|begin)\s.{0,25}\bpan\b"
        # ── Short / bare phrases ──────────────────────────────────────────────
        # "pan card" alone, "pan card please", "need pan card", "want pan card"
        r"|^pan\s+card\s*$"
        r"|^pan\s*$"
        r"|\bpan\s+card\s+(please|now|today|required|needed|thevai|venum|chahiye)\b"
        r"|\b(need|want|require|need\s+a|want\s+a)\s+pan\s+card\b"
        r"|\bgive\s+me\s+(a\s+)?pan\b"
        r"|\bget\s+me\s+(a\s+)?pan\b"
        r"|\bmake\s+(me\s+)?(a\s+)?pan\b"
        r"|\bstart\s+pan\b"
        r"|\bbegin\s+pan\b"
        # ── Hindi ────────────────────────────────────────────────────────────
        r"|\bpan\s+(banao|banana|chahiye|banaiye|bana\s+do|banana\s+hai|card\s+chahiye|apply\s+karna)\b"
        r"|\b(mujhe|muje|mujhko)\s+pan\b"
        r"|\bnaya\s+pan\b"
        r"|\bpan\s+ke\s+liye\b"
        # ── Tamil ────────────────────────────────────────────────────────────
        # "venum" = want/need, "edukkanum" = need to take, "thaa" = give
        # "pannanum" = need to do, "seiyanum" = need to do, "vendum" = need
        r"|\bpan\s+(venum|vendum|edukkanum|thaa|tharuvai|seiyanum)\b"
        r"|\bpan\s+card\s+(venum|vendum|edukkanum|thaa|pannanum|pnnanum|pananum|seiyanum)\b"
        r"|\b(enakku|enikku|enaku|naa|naan|naanu)\s+pan\b"
        r"|\bpan\s+(apply|register)\s+(pannanum|pnnanum|pananum|seiyanum)?\b"
        r"|\bpan\s+card\s+(apply|register)\s*(pannanum|pnnanum|pananum|seiyanum)?\b"
        r"|\bpan\s+card\s+\w{1,5}\s+(apply|register)\s*(pannanum|pnnanum|pananum)?\b"
        r"|\bpan\s+card\s+la\s+register\b"
        # ── Typos of "apply" — still require space before pan ────────────────
        r"|i\s+(want|wanna|wana|wan)\s+(to\s+)?(aply|appply|appley|applay|aplly|applyy|applu|apli|pply|paly|appl|apliy)\s.{0,15}\bpan\b"
        r"|i\s+(wnat|watn|wan|wana|wnna|wannt|wwant|wantt|wnt|wany|wann)\s+(to\s+)?(apply|aply|appply|pply|appl)\s.{0,15}\bpan\b"
        # ── Typos of "pan" itself with action words ───────────────────────────
        r"|i\s+(want|wanna|wana|wnat|watn)\s+(to\s+)?(apply|aply|pply|register|get)\s+(for\s+)?(a\s+)?(new\s+)?(oan|paan|pam|pn|pna)\b"
        r"|(apply|aply|pply|register|get)\s+(for\s+)?(a\s+)?(new\s+)?(oan|paan|pam|pn|pna)\b",
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
    # pan_apply_foreign, aadhaar_link, pan_verify — RAG only, no guided flow
]


# ── Fuzzy spelling correction ─────────────────────────────────────────────────
# Maps common action words (with typos) to their canonical form
_FUZZY_ACTION_WORDS = [
    "apply", "register", "get", "create", "obtain", "enroll", "make", "have",
    "start", "begin", "open", "fill",
]
_FUZZY_INTENT_WORDS = [
    "want", "wanna", "need", "like", "wish", "trying", "looking", "hoping", "planning",
    "naa", "naan", "naanu", "enakku", "enikku", "enaku",  # Tamil: "I/for me" → intent
]

# Common phonetic / keyboard typos of "pan" to catch directly
_PAN_TYPOS = {
    "oan", "pn", "paan", "pna", "apn", "nap", "pa", "pann", "ppan", "pam", "ban", "pan",
}

def _fuzzy_correct_word(word: str, candidates: list[str], threshold: float = 0.65) -> str | None:
    """Return the best matching candidate if similarity >= threshold, else None."""
    from difflib import SequenceMatcher
    best, best_score = None, 0.0
    for c in candidates:
        score = SequenceMatcher(None, word.lower(), c).ratio()
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= threshold else None


def _token_looks_like_pan(token: str) -> bool:
    """Return True if the token is 'pan' or a close typo of it."""
    t = token.lower()
    if t in _PAN_TYPOS:
        return True
    # SequenceMatcher fallback for anything that's 2–4 chars and close to "pan"
    if 2 <= len(t) <= 5:
        from difflib import SequenceMatcher
        score = SequenceMatcher(None, t, "pan").ratio()
        if score >= 0.70:
            return True
    return False


def _fuzzy_detect_pan_apply(question: str) -> bool:
    """
    Fuzzy fallback: tokenise the question and check if it contains
    a near-match for an intent word + action word + 'pan' (or a typo of pan).
    Catches typos like 'aply', 'wnat', 'oan', 'pply', etc.
    """
    tokens = re.findall(r"[a-z]+", question.lower())

    has_pan = any(_token_looks_like_pan(t) for t in tokens)
    if not has_pan:
        return False

    has_intent = any(_fuzzy_correct_word(t, _FUZZY_INTENT_WORDS) for t in tokens)
    has_action = any(_fuzzy_correct_word(t, _FUZZY_ACTION_WORDS) for t in tokens)
    return has_intent and has_action


def detect_service(question: str) -> str | None:
    q = question.strip()
    if _is_informational(q):
        return None

    # Pass 1: exact regex
    for service_id, pattern in _SERVICE_PATTERNS:
        if pattern.search(q):
            return service_id

    # Pass 2: fuzzy fallback for pan_apply_indian only
    if _fuzzy_detect_pan_apply(q):
        return "pan_apply_indian"

    return None


def get_service(service_id: str) -> dict:
    return SERVICES.get(service_id, {})