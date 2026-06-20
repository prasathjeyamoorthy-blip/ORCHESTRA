"""
agent/translator.py

Post-translation layer for Tamil and Hindi output.

Primary engine  : IndicTrans2 (ai4bharat/indictrans2-en-indic-1B)
                  — open-source, state-of-the-art for Indian languages,
                    produces natural colloquial Tamil / Hindi.
Fallback engine : deep-translator (Google Translate) — used when
                  IndicTrans2 is not installed or fails.

Preserves:
  - PAN-specific document / portal names (PAN, Aadhaar, TAN, TDS, …)
  - Markdown formatting (**, ##, -, |, numbered lists)
  - Numbers, amounts (₹), dates
  - Placeholders like __PTERM_N__
"""

import re
import threading
from typing import Optional

# ── Terms that must NEVER be translated ──────────────────────────────────────
# These are official document / portal names — keep them in English always.
# Sorted longest-first so multi-word phrases match before single words.
_PRESERVE_TERMS = [
    # Multi-word document / form names
    "Form 49A", "Form 49AA", "Form 26AS",
    "e-KYC", "eKYC", "e-PAN", "ePAN",
    "PAN Card", "PAN card",
    "Aadhaar Card", "Aadhaar card",
    "Aadhaar-PAN", "Aadhaar PAN",
    "Income Tax Department",
    "Income Tax",
    # Portal / authority names
    "Protean", "NSDL", "UTIITSL",
    # Document / scheme acronyms
    "PAN", "Aadhaar", "Aadhar", "TAN", "TDS", "TCS",
    "ITR", "HUF", "NRI", "OCI", "PIO", "KYC", "GST",
    # Tech / process terms
    "OTP", "SMS", "PDF", "eSign", "e-Sign",
    "DigiLocker", "mAadhaar",
]

_PLACEHOLDER_RE = re.compile(r"__PTERM_\d+__")

# ── Markdown structural tokens — protect line-level markers ──────────────────
# We translate line content but keep **, ##, -, |, > intact.
_MD_LINE_RE = re.compile(
    r"^(\s*(?:#{1,6}\s|\*\*|[-•]\s|\d+\.\s|>\s|\|))(.*)",
    re.MULTILINE,
)


# ─────────────────────────────────────────────────────────────────────────────
# IndicTrans2 engine (lazy-loaded singleton)
# ─────────────────────────────────────────────────────────────────────────────

class _IndicTrans2Engine:
    """
    Wraps the ai4bharat IndicTrans2 model.
    Loaded once on first use (lazy init) to avoid startup cost.
    Thread-safe via a lock.
    """
    _instance: Optional["_IndicTrans2Engine"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._available = None   # None = not tried yet, True/False after attempt

    @classmethod
    def get(cls) -> "_IndicTrans2Engine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load(self):
        """Try to load IndicTrans2. Sets self._available."""
        if self._available is not None:
            return
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            import torch

            model_name = "ai4bharat/indictrans2-en-indic-1B"
            print(f"[translator] Loading IndicTrans2 model ({model_name}) …")
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name, trust_remote_code=True
            ).to(device)
            self._model.eval()
            self._device = device
            self._available = True
            print(f"[translator] IndicTrans2 ready on {device} ✅")
        except Exception as e:
            # Silently fall back to deep-translator (which works well for Tamil/Hindi)
            # To enable IndicTrans2: pip install transformers torch
            self._available = False

    # IndicTrans2 language codes
    _LANG_CODES = {
        "ta": "tam_Taml",   # Tamil
        "hi": "hin_Deva",   # Hindi
    }

    def translate(self, text: str, target_lang: str) -> Optional[str]:
        """
        Translate text to target_lang using IndicTrans2.
        Returns None if unavailable or on error.
        """
        self._load()
        if not self._available:
            return None

        tgt_code = self._LANG_CODES.get(target_lang)
        if not tgt_code:
            return None

        try:
            import torch
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(self._device)

            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    num_beams=4,
                    max_length=512,
                    forced_bos_token_id=self._tokenizer.convert_tokens_to_ids(tgt_code),
                )

            translated = self._tokenizer.batch_decode(outputs, skip_special_tokens=True)
            return translated[0] if translated else None
        except Exception as e:
            print(f"[translator] IndicTrans2 translate error: {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# Fallback: deep-translator (Google Translate)
# ─────────────────────────────────────────────────────────────────────────────

def _deep_translate(text: str, target_lang: str) -> str:
    """Fallback translation via deep-translator (Google Translate backend)."""
    lang_map = {"ta": "tamil", "hi": "hindi"}
    dt_lang = lang_map.get(target_lang)
    if not dt_lang:
        return text
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source="en", target=dt_lang).translate(text)
        return result or text
    except ImportError:
        print("[translator] deep-translator not installed. Run: pip install deep-translator")
        return text
    except Exception as e:
        print(f"[translator] deep-translator error: {e}")
        return text


# ─────────────────────────────────────────────────────────────────────────────
# Term protection helpers
# ─────────────────────────────────────────────────────────────────────────────

def _protect_terms(text: str) -> tuple[str, dict]:
    """Replace preserve-terms with numbered placeholders before translation."""
    placeholder_map: dict[str, str] = {}
    result = text
    idx = 0
    for term in sorted(_PRESERVE_TERMS, key=len, reverse=True):
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        if pattern.search(result):
            placeholder = f"__PTERM_{idx}__"
            m = pattern.search(result)
            placeholder_map[placeholder] = m.group(0)   # preserve original casing
            result = pattern.sub(placeholder, result)
            idx += 1
    return result, placeholder_map


def _restore_terms(text: str, placeholder_map: dict) -> str:
    for placeholder, original in placeholder_map.items():
        text = text.replace(placeholder, original)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Core translation dispatcher
# ─────────────────────────────────────────────────────────────────────────────

def _translate_chunk(text: str, target_lang: str) -> str:
    """
    Translate a single text chunk.
    Tries IndicTrans2 first; falls back to deep-translator.
    """
    if not text.strip():
        return text

    # Try IndicTrans2 (best quality for Indian languages)
    engine = _IndicTrans2Engine.get()
    result = engine.translate(text, target_lang)
    if result:
        return result

    # Fallback to deep-translator
    return _deep_translate(text, target_lang)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def translate_response(text: str, target_lang: str) -> str:
    """
    Translate an agent response to Tamil or Hindi.

    Strategy:
    1. Protect document/portal names with placeholders.
    2. Split on blank lines (paragraphs) to stay within model token limits.
    3. Translate each paragraph independently.
    4. Restore protected terms.

    Markdown structure (**, ##, -, |, >) is preserved because the LLM
    already outputs it and we only translate the text content.
    """
    if not text or target_lang == "en" or target_lang not in ("ta", "hi"):
        return text

    # Step 1 — protect terms
    protected, placeholder_map = _protect_terms(text)

    # Step 2 — split into paragraphs (blank-line separated)
    paragraphs = protected.split("\n\n")
    translated_parts: list[str] = []

    for para in paragraphs:
        if not para.strip():
            translated_parts.append(para)
            continue

        # Translate line by line within the paragraph to preserve markdown markers
        lines = para.split("\n")
        translated_lines: list[str] = []
        for line in lines:
            if not line.strip():
                translated_lines.append(line)
                continue

            # Detect markdown prefix (##, -, *, |, >, numbered list)
            md_match = re.match(
                r"^(\s*(?:#{1,6}\s+|\*\*|\*|[-•]\s+|\d+\.\s+|>\s+|\|))(.*)",
                line,
            )
            if md_match:
                prefix = md_match.group(1)
                content = md_match.group(2)
                # Only translate the content part, keep the prefix
                translated_content = _translate_chunk(content, target_lang) if content.strip() else content
                translated_lines.append(prefix + translated_content)
            else:
                translated_lines.append(_translate_chunk(line, target_lang))

        translated_parts.append("\n".join(translated_lines))

    result = "\n\n".join(translated_parts)

    # Step 3 — restore protected terms
    if placeholder_map:
        result = _restore_terms(result, placeholder_map)

    return result


def translate_followups(followups: list, target_lang: str) -> list:
    """
    Translate followup suggestion chips (short phrases).
    These are the button texts shown to users.
    """
    if target_lang == "en" or not followups:
        return followups
    
    print(f"[translator] Translating {len(followups)} followups to {target_lang}")
    translated = []
    for f in followups:
        translated_f = translate_response(f, target_lang)
        print(f"[translator]   '{f}' → '{translated_f}'")
        translated.append(translated_f)
    
    return translated


def translate_options(options: dict, target_lang: str) -> dict:
    """
    Translate guided-flow option choices (radio / checkbox labels).
    Keeps document names intact via the protect/restore mechanism.
    """
    if not options or target_lang == "en":
        return options

    result = dict(options)

    if "choices" in result and isinstance(result["choices"], list):
        result["choices"] = [
            translate_response(c, target_lang) for c in result["choices"]
        ]

    if "label" in result and isinstance(result["label"], str):
        result["label"] = translate_response(result["label"], target_lang)

    if "hint" in result and isinstance(result["hint"], str):
        result["hint"] = translate_response(result["hint"], target_lang)

    return result
