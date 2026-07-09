# intent/language_detector.py
"""
Language detection — 3-tier pipeline:

  Tier 1: Unicode script check (instant, 100% accurate for native Tamil/Hindi)
  Tier 2: lingua library  (statistical model, no keyword lists, handles short text)
  Tier 3: Groq LLM        (fallback for ambiguous Tanglish — called async, result cached)

This replaces the old keyword-matching approach which caused false positives on
English words like "Non-resident", "en", "nan", etc.
"""

import re
import os
import threading
from typing import Tuple, Optional

# ── Tier 2: lingua (lazy singleton) ──────────────────────────────────────────
_lingua_detector = None
_lingua_lock = threading.Lock()

def _get_lingua():
    global _lingua_detector
    if _lingua_detector is None:
        with _lingua_lock:
            if _lingua_detector is None:
                try:
                    from lingua import Language, LanguageDetectorBuilder
                    _lingua_detector = (
                        LanguageDetectorBuilder
                        .from_languages(Language.ENGLISH, Language.TAMIL, Language.HINDI)
                        .with_minimum_relative_distance(0.25)  # confidence gate
                        .build()
                    )
                    print("[language_detector] lingua detector ready ✅")
                except Exception as e:
                    print(f"[language_detector] lingua unavailable: {e}")
                    _lingua_detector = False   # mark as tried-and-failed
    return _lingua_detector if _lingua_detector is not False else None


# ── Tier 1: Unicode script detection ─────────────────────────────────────────
def _detect_native_script(text: str) -> Optional[str]:
    """
    Detect Tamil or Hindi from native Unicode script ranges.
    Tamil: U+0B80–U+0BFF  |  Hindi/Devanagari: U+0900–U+097F
    Returns 'ta', 'hi', or None.
    """
    total_chars = len(re.sub(r'\s+', '', text))
    if total_chars == 0:
        return None

    tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
    hindi_chars  = len(re.findall(r'[\u0900-\u097F]', text))

    if tamil_chars / total_chars > 0.3:
        return 'ta'
    if hindi_chars / total_chars > 0.3:
        return 'hi'
    return None


# ── Tier 2: lingua statistical detection ─────────────────────────────────────
def _detect_with_lingua(text: str) -> Optional[str]:
    """
    Use the lingua library to detect language.
    Returns 'ta', 'hi', or None (None = English or uncertain).
    Minimum relative distance of 0.25 acts as a confidence gate.
    """
    detector = _get_lingua()
    if detector is None:
        return None
    try:
        from lingua import Language
        result = detector.detect_language_of(text)
        if result == Language.TAMIL:
            return 'ta'
        if result == Language.HINDI:
            return 'hi'
        # ENGLISH or None → return None so caller defaults to English
        return None
    except Exception as e:
        print(f"[language_detector] lingua error: {e}")
        return None


# ── Tier 3: Groq LLM fallback (for genuinely ambiguous Tanglish) ─────────────
def _detect_with_groq(text: str) -> Optional[str]:
    """
    Ask Groq 8B to classify the language. Only called when both Tier 1 and
    Tier 2 return None and the text is at least 10 chars long.
    Fast: ~300ms on llama-3.1-8b-instant.
    """
    if len(text.strip()) < 10:
        return None
    try:
        # Load env if not already loaded (handles direct module import contexts)
        from dotenv import load_dotenv
        load_dotenv()

        api_keys = [
            os.getenv("GROQ_API_KEY1", ""),
            os.getenv("GROQ_API_KEY2", ""),
            os.getenv("GROQ_API_KEY3", ""),
        ]
        api_key = next((k for k in api_keys if k), None)
        if not api_key:
            return None

        import requests
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{
                    "role": "user",
                    "content": (
                        "Classify the language of this text. "
                        "Reply with exactly one word: ENGLISH, TAMIL, or HINDI.\n\n"
                        f"Text: {text[:200]}"
                    )
                }],
                "max_tokens": 5,
                "temperature": 0,
            },
            timeout=5,
        )
        if resp.status_code == 200:
            label = resp.json()["choices"][0]["message"]["content"].strip().upper()
            if "TAMIL" in label:
                return 'ta'
            if "HINDI" in label:
                return 'hi'
        return None
    except Exception as e:
        print(f"[language_detector] Groq fallback error: {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def detect_language(text: str, override: str = None) -> str:
    """
    Detect language using 3-tier pipeline.

    Args:
        text:     User input text
        override: Force a language code ('en', 'ta', 'hi') — always respected

    Returns:
        'ta' | 'hi' | 'en'
    """
    if override and override in ('en', 'ta', 'hi'):
        return override
    if not text or not text.strip():
        return 'en'

    # Tier 1: native script (fastest, zero false positives)
    native = _detect_native_script(text)
    if native:
        return native

    # Tier 2: lingua statistical model
    lingua_result = _detect_with_lingua(text)
    if lingua_result:
        return lingua_result

    # Tier 3: Groq LLM — only for ambiguous Tanglish (≥10 chars)
    if len(text.strip()) >= 10:
        groq_result = _detect_with_groq(text)
        if groq_result:
            return groq_result

    return 'en'


def detect_language_with_confidence(text: str, override: str = None) -> Tuple[str, float]:
    """
    Same pipeline but returns (language_code, confidence).

    Confidence levels:
      - Native script:  0.95  (very high — script range is unambiguous)
      - lingua:         0.80  (high — statistical model with distance gate)
      - Groq LLM:       0.90  (high — LLM understands Tanglish context)
      - Default English: 1.0  (certain — nothing triggered a switch)
    """
    if override and override in ('en', 'ta', 'hi'):
        return (override, 1.0)
    if not text or not text.strip():
        return ('en', 1.0)

    # Tier 1
    native = _detect_native_script(text)
    if native:
        # Refine confidence by script density
        total_chars = len(re.sub(r'\s+', '', text))
        tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
        hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))
        density = (tamil_chars if native == 'ta' else hindi_chars) / total_chars
        return (native, min(0.5 + density * 0.5, 0.99))

    # Tier 2
    lingua_result = _detect_with_lingua(text)
    if lingua_result:
        return (lingua_result, 0.80)

    # Tier 3
    if len(text.strip()) >= 10:
        groq_result = _detect_with_groq(text)
        if groq_result:
            return (groq_result, 0.90)

    return ('en', 1.0)


def get_language_name(code: str) -> str:
    return {'ta': 'Tamil', 'hi': 'Hindi', 'en': 'English'}.get(code, 'English')


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    tests = [
        ("vanakkam, enna pan card apply panna venum",   "ta"),
        ("namaste, mujhe pan card chahiye",             "hi"),
        ("hello, I want to apply for PAN card",         "en"),
        ("Non-resident",                                "en"),
        ("Yes",                                         "en"),
        ("naan pan card apply panna venum",             "ta"),
        ("நான் PAN கார்டு வேண்டும்",                    "ta"),
        ("मुझे PAN card चाहिए",                         "hi"),
    ]
    print("Language Detection Tests (3-tier pipeline)")
    print("=" * 60)
    for text, expected in tests:
        lang, conf = detect_language_with_confidence(text)
        status = "✅" if lang == expected else "❌"
        print(f"{status} [{expected}→{lang} {conf:.0%}] {text[:50]}")
