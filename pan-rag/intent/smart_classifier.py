"""
intent/smart_classifier.py

LLM-based intent classification + user data extraction.
Replaces the brittle regex-based checks for:
  - name/data providing ("my name is X", "call me X", Tanglish variants)
  - info queries ("who am i", "do you remember my name", "what salary did i give")
  - flow answers (applicant type, submission mode choices, etc.)
  - off-topic / casual chat during a flow

Single Groq call per message (~200-400ms on llama-3.1-8b-instant).
Falls back to "unknown" on any error so the existing logic handles it.
"""

import os
import json
import re
import threading
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ── Groq key pool (reuse same pool as generation/llm.py) ─────────────────────
_KEYS: list[str] = [
    k for k in [
        os.getenv("GROQ_API_KEY1", ""),
        os.getenv("GROQ_API_KEY2", ""),
        os.getenv("GROQ_API_KEY3", ""),
        os.getenv("GROQ_API_KEY4", ""),
        os.getenv("GROQ_API_KEY5", ""),
    ] if k
]
_key_idx = 0
_key_lock = threading.Lock()

def _get_key() -> Optional[str]:
    return _KEYS[_key_idx] if _KEYS else None

def _rotate_key():
    global _key_idx
    with _key_lock:
        _key_idx = (_key_idx + 1) % len(_KEYS) if _KEYS else 0


# ── Classification prompt ─────────────────────────────────────────────────────
_SYSTEM = """You are a message classifier for a PAN card application chatbot.

Classify the user message and extract any user data in it.

Return ONLY valid JSON with this exact structure:
{
  "intent": "<one of the intents below>",
  "data": {
    "full_name": "<extracted name or null>",
    "email": "<extracted email or null>",
    "salary": "<extracted income as string or null>",
    "mother_name": "<extracted mother name or null>",
    "grandfather_name": "<extracted grandfather name or null>",
    "pan_number": "<extracted PAN number or null>"
  },
  "query_field": "<if intent is info_query, which field: name|email|salary|mother_name|all|other>"
}

INTENTS:
- "data_provide"     : User is giving their personal information (name, email, salary, mother name, etc.)
- "info_query"       : User is asking what data you have about them ("who am i", "do you remember my name", "what salary did i give", "tell me my details")
- "flow_answer"      : User is directly answering the current application flow question (applicant type, submission mode, delivery mode, yes/no choices, document confirmations)
- "flow_continue"    : User wants to continue/proceed ("yes", "ok", "next", "continue", "proceed", "ready")
- "flow_cancel"      : User wants to cancel or stop the application
- "pan_question"     : User is asking a general PAN-related question (fees, documents needed, eligibility, etc.)
- "off_topic"        : User is talking about something completely unrelated to PAN (weather, food, jokes, etc.)
- "greeting"         : Simple greeting (hi, hello, good morning)
- "unknown"          : Cannot be classified clearly

RULES:
- "my name is X" → intent: data_provide, data.full_name: "X"
- "I'm Deva" → intent: data_provide, data.full_name: "Deva" (only if X looks like a proper name)
- "who am i", "do you remember my name", "what's my name", "tell who am i" → intent: info_query, query_field: "name"
- "what salary did I give", "do you have my income" → intent: info_query, query_field: "salary"
- "show me all my details", "what do you know about me" → intent: info_query, query_field: "all"
- "Indian Citizen", "Foreign Citizen" → intent: flow_answer (likely answering applicant type)
- "Aadhaar-based", "physical copy", "yes", "no" → intent: flow_answer
- Distinguish data_provide from flow_answer: if user says "my name is X" it's data_provide even if name step is active
- For data extraction: only extract data that is EXPLICITLY stated. Never infer or guess.
- Names must look like real names (2+ chars, no action words like "ready", "done", "pan", "apply")
- CONTEXT-AWARE step=details_collection: If the current step is details_collection and the message
  is a short comma/and-separated list like "govindhan, 5 lakhs" or "ravi kumar, 3 lakh", treat it
  as intent: flow_answer (positional answer for the step), NOT data_provide. Do NOT extract
  names from such messages as full_name or grandfather_name — the step handler does positional mapping.
- Never extract an email address as a name field.
"""

_NAME_REJECT = {
    "ready", "done", "fine", "good", "ok", "okay", "here", "hello", "not",
    "pan", "registration", "apply", "application", "sure", "going", "trying",
    "planning", "working", "looking", "waiting", "interested", "available",
    "unknown", "null", "none", "n/a",
}


def classify(message: str, current_step: str = None, language: str = "en") -> dict:
    """
    Classify a user message and extract any user data.

    Returns:
        {
          "intent": str,           # one of the intents above
          "data": dict,            # extracted fields (all None if nothing found)
          "query_field": str|None, # for info_query: which field they're asking about
          "error": bool            # True if LLM call failed (fallback to old logic)
        }
    """
    key = _get_key()
    if not key:
        return _fallback(message)

    context = ""
    if current_step:
        context = f"\nCurrent application step: {current_step}"

    try:
        import requests
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user",   "content": f"Message: {message}{context}"},
                ],
                "max_tokens": 200,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=8,
        )

        if resp.status_code in (429, 401):
            _rotate_key()
            return _fallback(message)

        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()

        # Parse JSON — be lenient
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # Try extracting JSON from response if wrapped in markdown
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                result = json.loads(m.group(0))
            else:
                return _fallback(message)

        intent = result.get("intent", "unknown")
        data   = result.get("data", {}) or {}
        query_field = result.get("query_field")

        # Sanitize extracted data
        clean_data = {}
        for field, val in data.items():
            if not val or val in ("null", "none", "n/a", "N/A", "None", "Null"):
                clean_data[field] = None
                continue
            val = str(val).strip()
            # Reject invalid names
            if field in ("full_name", "mother_name", "grandfather_name"):
                words = set(val.lower().split())
                if words.intersection(_NAME_REJECT) or len(val) < 2:
                    clean_data[field] = None
                    continue
            clean_data[field] = val

        return {
            "intent": intent,
            "data": clean_data,
            "query_field": query_field,
            "error": False,
        }

    except Exception as e:
        print(f"[smart_classifier] Error: {e}")
        return _fallback(message)


def _fallback(message: str) -> dict:
    """
    Minimal regex fallback when LLM is unavailable.
    Only catches the most obvious patterns.
    """
    m = message.lower().strip()
    data = {}

    # Name providing
    name_match = re.search(
        r"\b(?:my\s+(?:full\s+)?name\s+is|i'm|call\s+me)\s+([A-Za-z]{2,20}(?:\s+[A-Za-z]{2,20}){0,3})\s*$",
        message, re.IGNORECASE
    )
    if name_match:
        candidate = name_match.group(1).strip()
        if not set(candidate.lower().split()).intersection(_NAME_REJECT):
            data["full_name"] = candidate
            return {"intent": "data_provide", "data": data, "query_field": None, "error": True}

    # Info query
    if re.search(r"\bwho\s+am\s+i\b|\bmy\s+name\b|\bdo\s+you\s+(know|remember)\b", m):
        return {"intent": "info_query", "data": {}, "query_field": "name", "error": True}

    return {"intent": "unknown", "data": {}, "query_field": None, "error": True}
