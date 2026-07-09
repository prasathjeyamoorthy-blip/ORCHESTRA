"""
pan_intent_classifier.py
────────────────────────
Production-level classifier that detects PAN registration intent even when
the user doesn't know what PAN is or uses indirect/vague language.

Three-pass approach:
  Pass 1 — Fast regex: catches direct mentions (pan, tax id, etc.)
  Pass 2 — Semantic signals: catches indirect descriptions without PAN keywords
  Pass 3 — LLM fallback: for genuinely ambiguous cases, ask the LLM to classify

Examples of indirect queries this handles:
  "I need a tax identity number"
  "how do I get a government ID for filing taxes"
  "my employer is asking for some tax document"
  "I want to open a bank account but they need some ID"
  "I'm starting a job and HR asked for a number"
  "what do I need to invest in mutual funds"
  "I want to buy property, what documents do I need"
  "I'm a freelancer, what tax registration do I need"
"""

from __future__ import annotations
import re
from enum import Enum
from typing import Optional


class PANIntent(Enum):
    PAN_APPLY_NEW      = "pan_apply_new"       # wants a new PAN card
    PAN_CORRECTION     = "pan_correction"      # wants to correct/update PAN
    PAN_REPRINT        = "pan_reprint"         # lost/damaged PAN
    AADHAAR_LINK       = "aadhaar_link"        # wants to link Aadhaar-PAN
    PAN_VERIFY         = "pan_verify"          # wants to verify a PAN
    PAN_STATUS         = "pan_status"          # wants to track application
    PAN_INFO           = "pan_info"            # wants to know what PAN is
    NOT_PAN            = "not_pan"             # unrelated to PAN
    AMBIGUOUS          = "ambiguous"           # unclear, needs clarification


# ── Pass 1: Direct keyword patterns ──────────────────────────────────────────

_DIRECT_APPLY = re.compile(
    r"\b(apply|register|get|obtain|create|make|need|want|require|have)\b.{0,30}"
    r"\b(pan|pan\s*card|permanent\s*account|tax\s*id|tax\s*number|tax\s*card)\b"
    r"|\b(pan|pan\s*card)\b.{0,30}\b(apply|register|get|obtain|create|make)\b"
    r"|\bnew\s*(pan|pan\s*card)\b"
    r"|\bfirst\s*time\s*(pan|tax)\b"
    r"|\bform\s*49\s*a?\b",
    re.IGNORECASE
)

_DIRECT_CORRECTION = re.compile(
    r"\b(correct|correction|update|change|modify|fix|wrong|mistake|error|amend)\b"
    r".{0,40}\b(pan|pan\s*card)\b"
    r"|\b(pan|pan\s*card)\b.{0,40}"
    r"\b(correct|correction|update|change|modify|fix|wrong)\b"
    r"|\b(name\s+change|dob\s+change|address\s+change)\b.{0,20}\bpan\b",
    re.IGNORECASE
)

_DIRECT_REPRINT = re.compile(
    r"\b(lost|misplaced|damaged|stolen|reprint|duplicate|replace|replacement)\b"
    r".{0,30}\b(pan|pan\s*card)\b"
    r"|\b(pan|pan\s*card)\b.{0,30}"
    r"\b(lost|misplaced|damaged|stolen|reprint|duplicate)\b",
    re.IGNORECASE
)

_DIRECT_LINK = re.compile(
    r"\b(link|linking|connect|connecting|map|mapping|attach|attaching)\b"
    r".{0,30}\b(aadhaar|aadhar)\b.{0,30}\b(pan|pan\s*card)\b"
    r"|\b(aadhaar|aadhar)\b.{0,30}\b(pan|pan\s*card)\b.{0,30}"
    r"\b(link|linking|connect|map)\b"
    r"|\bpan.?aadhaar\b|\baadhaar.?pan\b",
    re.IGNORECASE
)

_DIRECT_VERIFY = re.compile(
    r"\b(verify|verification|check|validate|valid|authentic)\b"
    r".{0,30}\b(pan|pan\s*card|pan\s*number)\b",
    re.IGNORECASE
)

_DIRECT_STATUS = re.compile(
    r"\b(status|track|tracking|where|when|how\s*long)\b"
    r".{0,30}\b(pan|pan\s*card|application)\b"
    r"|\b(pan|pan\s*card)\b.{0,30}\b(status|track|delivered|dispatch)\b",
    re.IGNORECASE
)

_DIRECT_INFO = re.compile(
    r"\bwhat\s+is\s+(a\s+)?(pan|pan\s*card|permanent\s*account)\b"
    r"|\bwhat\s+does\s+pan\s+stand\b"
    r"|\bwhy\s+(do\s+i\s+need|is)\s+(a\s+)?pan\b"
    r"|\bpan\s+card\s+(meaning|definition|use|purpose|importance)\b",
    re.IGNORECASE
)


# ── Pass 2: Semantic signal patterns (no PAN keyword needed) ──────────────────
# These catch users who describe their situation without knowing the term "PAN"

_SEMANTIC_SIGNALS: list[tuple[str, PANIntent, float]] = [
    # (pattern, intent, confidence_weight)

    # Tax identity / registration
    (r"\b(tax\s*(id|identification|number|registration|card|document))\b", PANIntent.PAN_APPLY_NEW, 0.9),
    (r"\b(income\s*tax\s*(number|id|registration|document))\b", PANIntent.PAN_APPLY_NEW, 0.9),
    (r"\b(government\s*(tax|id|identification)\s*(number|card|document))\b", PANIntent.PAN_APPLY_NEW, 0.85),
    (r"\b(unique\s*(tax|identification)\s*(number|id))\b", PANIntent.PAN_APPLY_NEW, 0.85),

    # Employment / HR triggers
    (r"\b(employer|hr|company|office|job|joining)\b.{0,40}\b(tax|id|number|document|form)\b", PANIntent.PAN_APPLY_NEW, 0.75),
    (r"\b(salary|payroll|form\s*16|tds\s*deduction)\b.{0,40}\b(need|require|submit|provide)\b", PANIntent.PAN_APPLY_NEW, 0.8),
    (r"\b(new\s*job|joining\s*company|starting\s*work)\b.{0,40}\b(document|id|number|form)\b", PANIntent.PAN_APPLY_NEW, 0.7),

    # Financial / banking triggers
    (r"\b(bank\s*account|open\s*account)\b.{0,40}\b(tax|id|number|document|kyc)\b", PANIntent.PAN_APPLY_NEW, 0.75),
    (r"\b(mutual\s*fund|stock|share|invest|demat|trading)\b.{0,40}\b(need|require|document|id|number)\b", PANIntent.PAN_APPLY_NEW, 0.8),
    (r"\b(property|real\s*estate|land|house)\b.{0,40}\b(buy|purchase|register)\b.{0,40}\b(document|id|number)\b", PANIntent.PAN_APPLY_NEW, 0.75),
    (r"\b(insurance|policy)\b.{0,40}\b(tax|id|number|document|kyc)\b", PANIntent.PAN_APPLY_NEW, 0.7),
    (r"\b(loan|credit\s*card|mortgage)\b.{0,40}\b(tax|id|number|document|kyc)\b", PANIntent.PAN_APPLY_NEW, 0.7),

    # Tax filing triggers
    (r"\b(file|filing|submit)\b.{0,30}\b(tax|itr|return|income)\b", PANIntent.PAN_APPLY_NEW, 0.75),
    (r"\b(income\s*tax\s*return|itr)\b.{0,30}\b(need|require|file|submit)\b", PANIntent.PAN_APPLY_NEW, 0.8),
    (r"\b(tax\s*refund)\b.{0,30}\b(get|claim|apply|receive)\b", PANIntent.PAN_APPLY_NEW, 0.75),

    # Freelancer / self-employed
    (r"\b(freelancer|freelance|self.?employed|consultant|contractor)\b.{0,40}\b(tax|id|register|document)\b", PANIntent.PAN_APPLY_NEW, 0.8),
    (r"\b(business|startup|company)\b.{0,30}\b(register|registration|tax|id)\b", PANIntent.PAN_APPLY_NEW, 0.7),

    # Foreign / NRI
    (r"\b(nri|non.?resident|overseas|abroad|foreign)\b.{0,40}\b(tax|id|india|document)\b", PANIntent.PAN_APPLY_NEW, 0.75),

    # Generic "I need an ID / document" with tax context
    (r"\b(need|want|require|get|obtain)\b.{0,30}\b(tax|income)\b.{0,30}\b(id|number|document|card|proof)\b", PANIntent.PAN_APPLY_NEW, 0.8),
    (r"\b(tax)\b.{0,20}\b(id|number|document|card|proof)\b.{0,30}\b(need|want|require|get|apply)\b", PANIntent.PAN_APPLY_NEW, 0.8),

    # Aadhaar linking without PAN keyword
    (r"\b(aadhaar|aadhar)\b.{0,40}\b(link|connect|map|attach|bind)\b", PANIntent.AADHAAR_LINK, 0.85),
    (r"\b(link|connect)\b.{0,20}\b(aadhaar|aadhar)\b", PANIntent.AADHAAR_LINK, 0.85),

    # TDS / TCS without PAN keyword
    (r"\b(tds|tcs|tax\s*deducted|tax\s*collected)\b.{0,40}\b(deduct|deduction|certificate|form\s*16)\b", PANIntent.PAN_APPLY_NEW, 0.7),
]


# ── Pass 3: LLM-based classifier for ambiguous cases ─────────────────────────

_LLM_CLASSIFY_PROMPT = """You are a PAN card service classifier. Given a user message, determine if the user needs a PAN card or PAN-related service.

PAN card is India's Permanent Account Number — a 10-character tax identity issued by the Income Tax Department. It is required for:
- Filing income tax returns
- Opening bank accounts
- Investing in stocks/mutual funds
- Buying property
- Getting a salary (TDS deduction)
- Starting a business

User message: "{question}"

Classify as ONE of:
- pan_apply_new: user needs a new PAN card (even if they don't know it's called PAN)
- pan_correction: user wants to correct/update their existing PAN
- pan_reprint: user lost/damaged their PAN card
- aadhaar_link: user wants to link Aadhaar with PAN
- pan_verify: user wants to verify a PAN number
- pan_status: user wants to track their PAN application
- pan_info: user wants to know what PAN is
- not_pan: completely unrelated to PAN services

Reply with ONLY the classification label, nothing else."""


def classify_pan_intent(
    question: str,
    session_history: list[dict] | None = None,
    use_llm_fallback: bool = True,
) -> tuple[PANIntent, float]:
    """
    Classify whether a user message indicates PAN-related intent.

    Returns:
        (PANIntent, confidence: 0.0-1.0)

    confidence >= 0.8 → act on it
    confidence 0.5-0.8 → ask clarifying question
    confidence < 0.5 → treat as NOT_PAN
    """
    q = question.strip()
    if not q:
        return PANIntent.NOT_PAN, 0.0

    # ── Pass 1: Direct keyword matching ──────────────────────────
    result = _pass1_direct(q)
    if result:
        return result, 0.95

    # ── Pass 2: Semantic signal matching ─────────────────────────
    result, confidence = _pass2_semantic(q)
    if confidence >= 0.7:
        return result, confidence

    # ── Context boost: if recent history mentions PAN/tax ─────────
    if session_history:
        context_boost = _context_boost(session_history)
        if context_boost > 0 and confidence > 0:
            boosted = min(confidence + context_boost, 0.95)
            return result, boosted

    # ── Pass 3: LLM fallback for ambiguous cases ──────────────────
    if use_llm_fallback and confidence >= 0.3:
        llm_result = _pass3_llm(q)
        if llm_result:
            return llm_result, 0.85

    return PANIntent.NOT_PAN, confidence


def _pass1_direct(q: str) -> Optional[PANIntent]:
    if _DIRECT_APPLY.search(q):     return PANIntent.PAN_APPLY_NEW
    if _DIRECT_CORRECTION.search(q): return PANIntent.PAN_CORRECTION
    if _DIRECT_REPRINT.search(q):   return PANIntent.PAN_REPRINT
    if _DIRECT_LINK.search(q):      return PANIntent.AADHAAR_LINK
    if _DIRECT_VERIFY.search(q):    return PANIntent.PAN_VERIFY
    if _DIRECT_STATUS.search(q):    return PANIntent.PAN_STATUS
    if _DIRECT_INFO.search(q):      return PANIntent.PAN_INFO
    return None


def _pass2_semantic(q: str) -> tuple[PANIntent, float]:
    best_intent = PANIntent.NOT_PAN
    best_score  = 0.0

    for pattern, intent, weight in _SEMANTIC_SIGNALS:
        if re.search(pattern, q, re.IGNORECASE):
            if weight > best_score:
                best_score  = weight
                best_intent = intent

    return best_intent, best_score


def _context_boost(history: list[dict]) -> float:
    """
    If recent conversation was about PAN/tax, boost confidence for
    follow-up messages that might be indirect.
    """
    _PAN_CONTEXT = re.compile(
        r"\b(pan|tax|aadhaar|income|tds|nsdl|form\s*49)\b", re.IGNORECASE
    )
    recent = history[-4:] if len(history) >= 4 else history
    pan_turns = sum(
        1 for turn in recent
        if _PAN_CONTEXT.search(turn.get("query", "") + turn.get("answer", ""))
    )
    if pan_turns >= 3: return 0.25
    if pan_turns >= 2: return 0.15
    if pan_turns >= 1: return 0.08
    return 0.0


def _pass3_llm(question: str) -> Optional[PANIntent]:
    """LLM-based classification for ambiguous cases."""
    try:
        import os
        from openai import OpenAI
        from config import LLM_API_KEY, LLM_BASE_URL, LLM_PROVIDER

        # Use a small/fast model for classification — just needs a label output
        _CLASSIFY_MODELS = {
            "groq":   os.getenv("GROQ_CLASSIFY_MODEL", "llama-3.1-8b-instant"),
            "nvidia": os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"),
        }
        model = _CLASSIFY_MODELS.get(LLM_PROVIDER, "llama-3.1-8b-instant")

        if not LLM_API_KEY:
            return None

        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _LLM_CLASSIFY_PROMPT.format(question=question)}],
            max_tokens=10,
            temperature=0,
        )
        label = resp.choices[0].message.content.strip().lower()
        _MAP = {
            "pan_apply_new":  PANIntent.PAN_APPLY_NEW,
            "pan_correction": PANIntent.PAN_CORRECTION,
            "pan_reprint":    PANIntent.PAN_REPRINT,
            "aadhaar_link":   PANIntent.AADHAAR_LINK,
            "pan_verify":     PANIntent.PAN_VERIFY,
            "pan_status":     PANIntent.PAN_STATUS,
            "pan_info":       PANIntent.PAN_INFO,
            "not_pan":        PANIntent.NOT_PAN,
        }
        return _MAP.get(label)
    except Exception as e:
        print(f"[PANClassifier] LLM fallback failed: {e}")
        return None


# ── Clarification generator ───────────────────────────────────────────────────

def get_clarification_prompt(question: str, intent: PANIntent, confidence: float) -> Optional[str]:
    """
    If confidence is medium (0.5-0.8), return a clarifying question
    instead of assuming the intent.
    """
    if confidence >= 0.8 or confidence < 0.5:
        return None

    if intent == PANIntent.PAN_APPLY_NEW:
        return (
            "It sounds like you might need a **PAN card** — India's Permanent Account Number, "
            "which is required for tax filing, banking, and investments.\n\n"
            "Is that what you're looking for? Just say **yes** and I'll guide you through the application."
        )
    if intent == PANIntent.AADHAAR_LINK:
        return (
            "Are you looking to **link your Aadhaar with your PAN card**? "
            "This is now mandatory for tax filing. Just confirm and I'll walk you through it."
        )
    return None
