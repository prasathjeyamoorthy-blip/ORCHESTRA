# generation/multilingual_templates.py
"""
Multilingual response templates for Tamil and English.
"""

# ── Tamil Templates ───────────────────────────────────────────────────────────
TAMIL_TEMPLATES = {
    "greeting": "வணக்கம்! நான் உங்கள் PAN கார்டு உதவியாளர். நான் உங்களுக்கு எப்படி உதவ முடியும்?",
    "greeting_transliterated": "Vanakkam! Naan ungal PAN card uthaviyaalar. Naan ungalukku eppadi uthava mudiyum?",
    "ask_name": "உங்கள் முழு பெயர் என்ன?",
    "ask_name_transliterated": "Ungal muzhu peyar enna?",
    "ask_mother_name": "உங்கள் தாயின் முழு பெயர் என்ன?",
    "ask_mother_name_transliterated": "Ungal thaayin muzhu peyar enna?",
    "ask_email": "உங்கள் மின்னஞ்சல் முகவரி என்ன?",
    "ask_email_transliterated": "Ungal minnanjal mugavari enna?",
    "ask_salary": "உங்கள் ஆண்டு வருமானம் என்ன?",
    "ask_salary_transliterated": "Ungal aandu varumanam enna?",
    "confirmation": "நான் சரியாகப் புரிந்துகொண்டேனா?",
    "confirmation_transliterated": "Naan sariyaaga purinthukondenaa?",
    "yes": "ஆம்",
    "yes_transliterated": "Aam",
    "no": "இல்லை",
    "no_transliterated": "Illai",
    "thank_you": "நன்றி!",
    "thank_you_transliterated": "Nandri!",
    "proceed": "தொடரவும்",
    "proceed_transliterated": "Thodaravum",
    "change": "மாற்றவும்",
    "change_transliterated": "Maatravum",
    "error": "மன்னிக்கவும், ஏதோ தவறு நடந்துவிட்டது.",
    "error_transliterated": "Mannikkavum, yetho thavaru nadanthuvittadhu.",
    "help": "நான் உங்களுக்கு PAN கார்டு விண்ணப்பம், ஆதார் இணைப்பு, மற்றும் பல விஷயங்களில் உதவ முடியும்.",
    "help_transliterated": "Naan ungalukku PAN card vinnappam, Aadhaar inaippu, matrum pala vishayangalil uthava mudiyum.",
    "documents_needed": "இதோ உங்களுக்கு தேவையான ஆவணங்கள்:",
    "documents_needed_transliterated": "Itho ungalukku thevaiyaana avanangal:",
    "ready_to_upload": "பதிவேற்ற தயாரா? **ஆம்** என்று பதிலளியுங்கள், நான் பதிவேற்ற பேனலைத் திறக்கிறேன்.",
    "ready_to_upload_transliterated": "Pathivettra thayaaraa? **Aam** endru pathilaḷiyungal, naan pathivettra panel-ai thirakkiren.",
    "upload_now": "சிறப்பு! பதிவேற்ற பேனல் இப்போது திறந்துள்ளது. உங்கள் ஆவணங்களை ஒவ்வொன்றாக பதிவேற்றவும்.",
    "upload_now_transliterated": "Sirappu! Pathivettra panel ippothu thiranthuḷḷathu. Ungal avanangalai ovvondraaga pathivetrravum.",
    "all_docs_received": "அனைத்து ஆவணங்களும் பெறப்பட்டன — நீங்கள் தயாராக இருக்கிறீர்கள்!",
    "all_docs_received_transliterated": "Anaithu avanangalum peṟappaṭṭana — neengal thayaaraaga irukkireergal!",
    "aadhaar": "ஆதார் அட்டை",
    "aadhaar_transliterated": "Aadhaar attai",
    "photograph": "புகைப்படம்",
    "photograph_transliterated": "Pugaippadam",
    "identity_proof": "அடையாள சான்று",
    "identity_proof_transliterated": "Adaiyaala saandru",
    "address_proof": "முகவரி சான்று",
    "address_proof_transliterated": "Mugavari saandru",
    "dob_proof": "பிறந்த தேதி சான்று",
    "dob_proof_transliterated": "Pirantha thethi saandru",
    "optional": "விருப்பமானது",
    "optional_transliterated": "viruppamanathu",
    "accepted": "ஏற்றுக்கொள்ளப்பட்டது",
    "accepted_transliterated": "Yetrukkollappattadhu",
}

# ── English Templates (default) ───────────────────────────────────────────────
ENGLISH_TEMPLATES = {
    "greeting": "Hello! I'm your PAN card assistant. How can I help you?",
    "ask_name": "What is your full name?",
    "ask_mother_name": "What is your mother's full name?",
    "ask_email": "What is your email address?",
    "ask_salary": "What is your annual income?",
    "confirmation": "Did I get that right?",
    "yes": "Yes",
    "no": "No",
    "thank_you": "Thank you!",
    "proceed": "Proceed",
    "change": "Change",
    "error": "Sorry, something went wrong.",
    "help": "I can help you with PAN card application, Aadhaar linking, and many other things.",
}

# ── Template getter ───────────────────────────────────────────────────────────
def get_template(key: str, language: str = 'en', use_transliteration: bool = True) -> str:
    """Get template text in specified language (en or ta)."""
    if language == 'ta':
        templates = TAMIL_TEMPLATES
        suffix = '_transliterated' if use_transliteration else ''
        return templates.get(f"{key}{suffix}", templates.get(key, ENGLISH_TEMPLATES.get(key, '')))
    return ENGLISH_TEMPLATES.get(key, '')


def format_response(text: str, language: str = 'en', use_transliteration: bool = True) -> str:
    """Format a response (currently returns original text)."""
    return text
