# intent/language_detector.py
"""
Language detection for Tamil and Hindi (native script + transliteration).
Detects when users type Tamil/Hindi words in English OR native script and switches response language.
"""
import re
from typing import Tuple, Optional

# Try to import langdetect, but make it optional
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0  # Make detection deterministic
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    print("[language_detector] langdetect not available. Install with: pip install langdetect")

# ── Tamil transliteration keywords ───────────────────────────────────────────
TAMIL_KEYWORDS = {
    # Greetings
    'vanakkam', 'vanakam', 'vaṇakkam', 'vanakaam',
    'nandri', 'nanri', 'nandrigal',
    'poitu', 'poyitu', 'varen', 'vaaren',
    
    # Common words
    'enna', 'ena', 'epadi', 'eppadi', 'yeppadi', 'epdi', 'yepdi',
    'naan', 'nan', 'naanu', 'na',
    'ungal', 'unga', 'ungaḷ',
    'enna', 'yenna',
    'sari', 'seri', 'sariya', 'seriya', 'sariyana',
    'illa', 'illai', 'illaiye', 'ila',
    'aam', 'aama', 'aamam', 'ama',
    'ponga', 'pongal',
    'vaa', 'vaanga', 'vaanga', 'va',
    'irukka', 'irukkira', 'iruku', 'irukku', 'irukken', 'iruken',
    'da', 'di', 'pa', 'ma', 'ba',  # Tamil informal suffixes
    'sollu', 'sollum', 'sollunga', 'solren', 'sol',
    'pannunga', 'pannu', 'panna', 'pannalam', 'panlam',
    'paru', 'paaru', 'parunga', 'paruga',
    'vaanga', 'vanga', 'vaada', 'vada',
    'poi', 'po', 'ponga', 'poda',
    
    # Questions
    'yaar', 'yar', 'yaaru', 'yaru',
    'yenge', 'enga', 'yengae', 'enga',
    'yeppo', 'eppo', 'yeppothu', 'eppothu',
    'yeppadi', 'eppadi', 'yepdi', 'epdi',
    'yen', 'en', 'yean', 'yenna',
    'yevlo', 'evlo', 'evalo', 'yevalo',
    
    # PAN related (Tamil)
    'pan', 'card', 'kard', 'kaadu',
    'apply', 'appli',
    'venum', 'vendum', 'venuma', 'venam',
    'thevai', 'tevai', 'thevaiya', 'tevaiya',
}

# ── Hindi transliteration keywords ────────────────────────────────────────────
HINDI_KEYWORDS = {
    # Greetings
    'namaste', 'namaskar', 'namasthe', 'namaskaar',
    'dhanyavaad', 'dhanyavad', 'shukriya', 'shukria',
    'alvida', 'alwida',
    
    # Common words
    'haan', 'han', 'haa', 'ha',
    'nahi', 'nahin', 'nai', 'na',
    'kya', 'kia',
    'kaise', 'kese', 'kaisey',
    'kahan', 'kaha', 'kahaan',
    'kab', 'kub',
    'kyun', 'kyon', 'kyoon', 'kyu',
    'aap', 'aapka', 'aapki',
    'main', 'mein', 'mai',
    'mera', 'meri', 'mere',
    'theek', 'thik', 'theekh', 'thikh',
    'achha', 'acha', 'accha', 'achaa',
    'bahut', 'bohot', 'bahot',
    
    # Questions
    'kaun', 'kon', 'koun',
    'kaunsa', 'konsa', 'kaunsi', 'konsi',
    
    # PAN related (Hindi)
    'chahiye', 'chaiye', 'chahie',
    'karna', 'krna', 'karne',
    'milega', 'milega', 'milta',
}

# ── Language detection patterns ───────────────────────────────────────────────
def _detect_native_script(text: str) -> Optional[str]:
    """
    Detect Tamil or Hindi from native Unicode script ranges.
    
    Tamil: U+0B80 to U+0BFF
    Hindi (Devanagari): U+0900 to U+097F
    
    Returns 'ta', 'hi', or None
    """
    tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
    hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))
    
    total_chars = len(re.sub(r'\s+', '', text))  # Non-whitespace chars
    
    if total_chars == 0:
        return None
    
    tamil_ratio = tamil_chars / total_chars
    hindi_ratio = hindi_chars / total_chars
    
    # If >30% of text is in Tamil/Hindi script, it's that language
    if tamil_ratio > 0.3:
        return 'ta'
    elif hindi_ratio > 0.3:
        return 'hi'
    
    return None


def _detect_with_langdetect(text: str) -> Optional[str]:
    """
    Use langdetect library as fallback for better detection.
    Returns 'ta', 'hi', or None
    """
    if not LANGDETECT_AVAILABLE:
        return None
    
    try:
        detected = detect(text)
        # Map langdetect codes to our codes
        if detected == 'ta':
            return 'ta'
        elif detected == 'hi':
            return 'hi'
        else:
            return None
    except:
        return None


def detect_language(text: str, override: str = None) -> str:
    """
    Detect language from transliterated text.
    
    Args:
        text: User input text
        override: Optional language code to force ('en', 'ta', 'hi')
        
    Returns:
        language_code: 'ta' (Tamil), 'hi' (Hindi), 'en' (English)
    """
    # If override is provided, use it
    if override and override in ('en', 'ta', 'hi'):
        return override
    
    if not text:
        return 'en'
    
    # 1. First try native script detection (most reliable)
    native_lang = _detect_native_script(text)
    if native_lang:
        return native_lang
    
    # 2. Try langdetect library (good for longer texts)
    if len(text) > 20:
        lang_detect_result = _detect_with_langdetect(text)
        if lang_detect_result:
            return lang_detect_result
    
    # 3. Fall back to keyword matching (for transliterated text)
    # Normalize text
    text_lower = text.lower().strip()
    words = re.findall(r'\b\w+\b', text_lower)
    
    if not words:
        return 'en'
    
    # Count matches
    tamil_matches = sum(1 for word in words if word in TAMIL_KEYWORDS)
    hindi_matches = sum(1 for word in words if word in HINDI_KEYWORDS)
    total_words = len(words)
    
    # Calculate confidence
    tamil_confidence = tamil_matches / total_words if total_words > 0 else 0.0
    hindi_confidence = hindi_matches / total_words if total_words > 0 else 0.0
    
    # Determine language (require at least 20% match or 2 keywords)
    threshold = 0.2
    min_keywords = 2
    
    if tamil_matches >= min_keywords or tamil_confidence >= threshold:
        return 'ta'
    elif hindi_matches >= min_keywords or hindi_confidence >= threshold:
        return 'hi'
    else:
        return 'en'


def detect_language_with_confidence(text: str, override: str = None) -> Tuple[str, float]:
    """
    Detect language from transliterated text with confidence score.
    
    Args:
        text: User input text
        override: Optional language code to force ('en', 'ta', 'hi')
        
    Returns:
        Tuple of (language_code, confidence)
        - language_code: 'ta' (Tamil), 'hi' (Hindi), 'en' (English)
        - confidence: 0.0 to 1.0
    """
    # If override is provided, use it
    if override and override in ('en', 'ta', 'hi'):
        return (override, 1.0)
    
    if not text:
        return ('en', 1.0)
    
    # 1. First try native script detection (most reliable)
    native_lang = _detect_native_script(text)
    if native_lang:
        # Calculate confidence based on script ratio
        tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
        hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))
        total_chars = len(re.sub(r'\s+', '', text))
        
        if native_lang == 'ta':
            confidence = tamil_chars / total_chars if total_chars > 0 else 0.5
        else:  # 'hi'
            confidence = hindi_chars / total_chars if total_chars > 0 else 0.5
        
        return (native_lang, min(confidence, 1.0))
    
    # 2. Try langdetect library (good for longer texts)
    if len(text) > 20:
        lang_detect_result = _detect_with_langdetect(text)
        if lang_detect_result:
            return (lang_detect_result, 0.7)  # Medium-high confidence
    
    # 3. Fall back to keyword matching (for transliterated text)
    # Normalize text
    text_lower = text.lower().strip()
    words = re.findall(r'\b\w+\b', text_lower)
    
    if not words:
        return ('en', 1.0)
    
    # Count matches
    tamil_matches = sum(1 for word in words if word in TAMIL_KEYWORDS)
    hindi_matches = sum(1 for word in words if word in HINDI_KEYWORDS)
    total_words = len(words)
    
    # Calculate confidence
    tamil_confidence = tamil_matches / total_words if total_words > 0 else 0.0
    hindi_confidence = hindi_matches / total_words if total_words > 0 else 0.0
    
    # Determine language (require at least 20% match or 2 keywords)
    threshold = 0.2
    min_keywords = 2
    
    if tamil_matches >= min_keywords or tamil_confidence >= threshold:
        return ('ta', tamil_confidence)
    elif hindi_matches >= min_keywords or hindi_confidence >= threshold:
        return ('hi', hindi_confidence)
    else:
        return ('en', 1.0)


def get_language_name(code: str) -> str:
    """Get full language name from code."""
    return {
        'ta': 'Tamil',
        'hi': 'Hindi',
        'en': 'English',
    }.get(code, 'English')


# ── Test function ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    test_cases = [
        "vanakkam, enna pan card apply panna venum",
        "namaste, mujhe pan card chahiye",
        "hello, I want to apply for PAN card",
        "naan pan card apply panna venum",
        "main pan card ke liye apply karna chahta hoon",
        "epadi pan card apply pannurathu",
        "kaise pan card apply kare",
    ]
    
    print("Language Detection Tests:")
    print("=" * 60)
    for text in test_cases:
        # Test simple detection
        lang = detect_language(text)
        # Test with confidence
        lang_conf, conf = detect_language_with_confidence(text)
        print(f"Input: {text}")
        print(f"Detected: {get_language_name(lang)} ({lang})")
        print(f"With confidence: {get_language_name(lang_conf)} ({lang_conf}) - {conf:.2%}")
        print("-" * 60)
