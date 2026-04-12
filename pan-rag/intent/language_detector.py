# intent/language_detector.py

# Tamil unicode range detector
def detect_language(text: str) -> str:
    """Detect language from user input."""
    
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