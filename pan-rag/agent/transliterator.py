"""
agent/transliterator.py

Detects and converts Tanglish (Tamil written in English) to proper Tamil script.
Used for field update detection when users type Tamil using English keyboard.

Examples:
  "naa kudiiruppua nilai update pannaum" → "நான் குடியிருப்பு நிலை புதுப்பிக்க வேண்டும்"
  "en peyar maatru" → "என் பெயர் மாற்று"
"""

import re
from typing import Optional


# ── Common Tanglish patterns for field names ──────────────────────────────────
_TANGLISH_FIELD_MAP = {
    # Name related
    r"\b(peyar|per|name)\b": "பெயர்",
    r"\b(ennodiya|ennoda)\s+(peyar|per)\b": "என் பெயர்",
    r"\b(en peyar|yen peyar|my name)\b": "என் பெயர்",
    r"\b(muzhu peyar|full name)\b": "முழு பெயர்",
    
    # Mother's name
    r"\b(thaai|thai|thay|amma|mother)\b": "தாய்",
    r"\b(thaai peyar|thai peyar|amma peyar|mother name)\b": "தாயின் பெயர்",
    
    # Email
    r"\b(email|mail|minanjal|minnanjal)\b": "மின்னஞ்சல்",
    r"\b(en email|my email)\b": "என் மின்னஞ்சல்",
    
    # Salary/Income
    r"\b(sambalam|salary|income)\b": "சம்பளம்",
    r"\b(varumanam|varuvaai)\b": "வருமானம்",
    r"\b(aandu varumanam|annual income)\b": "ஆண்டு வருமானம்",
    r"\b(en sambalam|my salary)\b": "என் சம்பளம்",
    
    # Submission mode
    r"\b(samarpippu murai|submission mode)\b": "சமர்ப்பிப்பு முறை",
    r"\b(samarpikum murai|submit mode)\b": "சமர்ப்பிக்கும் முறை",
    
    # Delivery mode
    r"\b(viniyoga murai|delivery mode)\b": "விநியோக முறை",
    r"\b(pan viniyogam|pan delivery)\b": "பான் விநியோகம்",
    
    # Aadhaar photo
    r"\b(aadhaar pugaippadam|aadhar photo)\b": "ஆதார் புகைப்படம்",
    r"\b(pugaippadam|photo)\b": "புகைப்படம்",
    
    # Source of income
    r"\b(varumaana aadharam|income source)\b": "வருமான ஆதாரம்",
    r"\b(varumanam vagai|income type)\b": "வருமானம் வகை",
    
    # Address
    r"\b(mugavari|address)\b": "முகவரி",
    r"\b(thodarpu mugavari|communication address)\b": "தொடர்பு முகவரி",
    
    # Residential status
    r"\b(kudiiruppu nilai|kudiruppu nilai|residential status)\b": "குடியிருப்பு நிலை",
    r"\b(vasippida nilai|residence status)\b": "வசிப்பிட நிலை",
    
    # Representative
    r"\b(pradhinidhi|prathinithy|representative)\b": "பிரதிநிதி",
    r"\b(pradhinidhi mathipeedaalar|representative assessee)\b": "பிரதிநிதி மதிப்பீட்டாளர்",
}


# ── Common Tanglish patterns for change intent ────────────────────────────────
_TANGLISH_INTENT_MAP = {
    r"\b(maatru|maatra|change|marru)\b": "மாற்று",
    r"\b(maatravum|change please)\b": "மாற்றவும்",
    r"\b(pudhuppi|pudhupi|update)\b": "புதுப்பி",
    r"\b(pudhuppikka|puduppika|to update)\b": "புதுப்பிக்க",
    r"\b(thiruththu|thiruth|edit|correct)\b": "திருத்து",
    r"\b(thiruththavum|thirutthavum|edit please)\b": "திருத்தவும்",
    r"\b(sari sei|fix)\b": "சரி செய்",
    r"\b(naan virumpukiren|i want|want)\b": "நான் விரும்புகிறேன்",
    r"\b(enakku vendum|i need|need)\b": "எனக்கு வேண்டும்",
    r"\b(pannaum|pannanum|pannanum|panna vendum)\b": "செய்ய வேண்டும்",
}


# ── Common Tanglish possessive/pronouns ───────────────────────────────────────
_TANGLISH_COMMON_MAP = {
    r"\b(naan|naa|i am)\b": "நான்",
    r"\b(en|yen|my)\b": "என்",
    r"\b(unga|ungal|your)\b": "உங்கள்",
    r"\b(endru|enru|is|as)\b": "என்று",
    r"\b(mattrum|matrum|and)\b": "மற்றும்",
}


def detect_tanglish(text: str) -> bool:
    """
    Detect if the text contains Tanglish (Tamil written in English).
    
    Returns True if common Tanglish patterns are found.
    """
    text_lower = text.lower()
    
    # Check for common Tanglish patterns
    tanglish_indicators = [
        r"\b(peyar|per|sambalam|mugavari|thaai|amma)\b",  # Tamil field names (per = name)
        r"\b(maatru|pudhuppi|thiruththu)\b",  # Change verbs
        r"\b(ennodiya|ennoda|naan|naa|en|yen)\b.*\b(peyar|per|sambalam|email)\b",  # possessive + field
        r"\b(kudiiruppu|viniyoga|samarpippu)\b",  # Complex field names
        r"\b(pannaum|pannanum|pnnanum|pananum|vendum)\b",  # Modal verbs (incl. typos)
    ]
    
    for pattern in tanglish_indicators:
        if re.search(pattern, text_lower):
            return True
    
    return False


def transliterate_tanglish(text: str) -> str:
    """
    Convert Tanglish (Tamil in English) to Tamil script.
    
    Args:
        text: Input text that may contain Tanglish
        
    Returns:
        Text with Tanglish converted to Tamil script
        
    Examples:
        "naa kudiiruppu nilai update pannaum"
        → "நான் குடியிருப்பு நிலை புதுப்பிக்க வேண்டும்"
        
        "en peyar maatru"
        → "என் பெயர் மாற்று"
    """
    if not detect_tanglish(text):
        return text
    
    result = text
    
    # Apply field name translations (longest first to avoid partial matches)
    for pattern, tamil in sorted(_TANGLISH_FIELD_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        result = re.sub(pattern, tamil, result, flags=re.IGNORECASE)
    
    # Apply intent verb translations
    for pattern, tamil in _TANGLISH_INTENT_MAP.items():
        result = re.sub(pattern, tamil, result, flags=re.IGNORECASE)
    
    # Apply common words
    for pattern, tamil in _TANGLISH_COMMON_MAP.items():
        result = re.sub(pattern, tamil, result, flags=re.IGNORECASE)
    
    return result


def is_mixed_language(text: str) -> bool:
    """
    Check if text contains both English/Tanglish and Tamil script.
    """
    has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))  # Tamil Unicode range
    has_english = bool(re.search(r'[a-zA-Z]', text))
    return has_tamil and has_english


def normalize_for_field_detection(text: str, language: str = "en") -> str:
    """
    Normalize text for field detection in receptionist.
    
    If language is Tamil and text contains Tanglish, convert it to Tamil script
    so the existing Tamil patterns in receptionist.py can match.
    
    Args:
        text: User input
        language: Detected language code ("en", "ta", "hi")
        
    Returns:
        Normalized text ready for field detection
    """
    # If Tamil mode and Tanglish detected, transliterate
    if language == "ta" and detect_tanglish(text):
        print(f"[transliterator] Detected Tanglish: {text}")
        transliterated = transliterate_tanglish(text)
        print(f"[transliterator] Converted to Tamil: {transliterated}")
        return transliterated
    
    return text


# ── Advanced: Use LLM for complex transliteration ─────────────────────────────

def llm_transliterate(text: str) -> Optional[str]:
    """
    Use LLM to transliterate complex Tanglish that regex can't handle.
    
    This is a fallback for complex sentences that need contextual understanding.
    Uses the NVIDIA NIM LLM to convert Tanglish to proper Tamil.
    
    Returns None if LLM is unavailable or fails.
    """
    try:
        import requests
        import os
        from dotenv import load_dotenv
        from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

        load_dotenv()

        if not LLM_API_KEY:
            return None

        prompt = f"""Convert this Tanglish (Tamil written in English) to proper Tamil script:

Input: "{text}"

Rules:
1. Convert Tamil words written in English to Tamil script
2. Keep English words like "PAN", "Aadhaar", "email" as-is
3. Maintain the same meaning and structure
4. Output only the converted text, nothing else

Output:"""

        response = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 100,
                "temperature": 0.3,
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            converted = result["choices"][0]["message"]["content"].strip()
            # Remove quotes if LLM added them
            converted = converted.strip('"\'')
            return converted
        
        return None
        
    except Exception as e:
        print(f"[transliterator] LLM transliteration failed: {e}")
        return None


def smart_transliterate(text: str, use_llm: bool = False) -> str:
    """
    Smart transliteration with optional LLM fallback.
    
    Args:
        text: Input text
        use_llm: Whether to use LLM for complex cases (default: False for speed)
        
    Returns:
        Transliterated text
    """
    # Try regex-based transliteration first (fast)
    result = transliterate_tanglish(text)
    
    # If result still has significant Tanglish and LLM is enabled, try LLM
    if use_llm and detect_tanglish(result):
        llm_result = llm_transliterate(text)
        if llm_result:
            return llm_result
    
    return result
