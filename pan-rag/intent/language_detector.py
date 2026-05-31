# intent/language_detector.py

SUPPORTED_LANGUAGES = {"en", "ta", "hi"}

def detect_language(text: str, override: str = None) -> str:
    """
    Detect language from user input.
    If override is provided (from frontend language switcher), use it directly.
    """
    # Frontend explicit override takes priority
    if override and override in SUPPORTED_LANGUAGES:
        return override

    tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    hindi_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')

    total = len(text.strip())
    if total == 0:
        return "en"

    if tamil_chars / total > 0.2:
        return "ta"
    if hindi_chars / total > 0.2:
        return "hi"

    return "en"


LANGUAGE_NAMES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
}
