# generation/multilingual_templates.py
"""
Multilingual response templates for Tamil and Hindi.
Provides language-specific responses for common agent interactions.
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
    
    # Document related
    "documents_needed": "இதோ உங்களுக்கு தேவையான ஆவணங்கள்:",
    "documents_needed_transliterated": "Itho ungalukku thevaiyaana avanangal:",
    
    "ready_to_upload": "பதிவேற்ற தயாரா? **ஆம்** என்று பதிலளியுங்கள், நான் பதிவேற்ற பேனலைத் திறக்கிறேன்.",
    "ready_to_upload_transliterated": "Pathivettra thayaaraa? **Aam** endru pathilaḷiyungal, naan pathivettra panel-ai thirakkiren.",
    
    "upload_now": "சிறப்பு! பதிவேற்ற பேனல் இப்போது திறந்துள்ளது. உங்கள் ஆவணங்களை ஒவ்வொன்றாக பதிவேற்றவும்.",
    "upload_now_transliterated": "Sirappu! Pathivettra panel ippothu thiranthuḷḷathu. Ungal avanangalai ovvondraaga pathivetrravum.",
    
    "all_docs_received": "அனைத்து ஆவணங்களும் பெறப்பட்டன — நீங்கள் தயாராக இருக்கிறீர்கள்!",
    "all_docs_received_transliterated": "Anaithu avanangalum peṟappaṭṭana — neengal thayaaraaga irukkireergal!",
    
    # Document types
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

# ── Hindi Templates ───────────────────────────────────────────────────────────
HINDI_TEMPLATES = {
    "greeting": "नमस्ते! मैं आपका PAN कार्ड सहायक हूँ। मैं आपकी कैसे मदद कर सकता हूँ?",
    "greeting_transliterated": "Namaste! Main aapka PAN card sahayak hoon. Main aapki kaise madad kar sakta hoon?",
    
    "ask_name": "आपका पूरा नाम क्या है?",
    "ask_name_transliterated": "Aapka poora naam kya hai?",
    
    "ask_mother_name": "आपकी माता का पूरा नाम क्या है?",
    "ask_mother_name_transliterated": "Aapki mata ka poora naam kya hai?",
    
    "ask_email": "आपका ईमेल पता क्या है?",
    "ask_email_transliterated": "Aapka email pata kya hai?",
    
    "ask_salary": "आपकी वार्षिक आय क्या है?",
    "ask_salary_transliterated": "Aapki varshik aay kya hai?",
    
    "confirmation": "क्या मैंने सही समझा?",
    "confirmation_transliterated": "Kya maine sahi samjha?",
    
    "yes": "हाँ",
    "yes_transliterated": "Haan",
    
    "no": "नहीं",
    "no_transliterated": "Nahi",
    
    "thank_you": "धन्यवाद!",
    "thank_you_transliterated": "Dhanyavaad!",
    
    "proceed": "आगे बढ़ें",
    "proceed_transliterated": "Aage badhen",
    
    "change": "बदलें",
    "change_transliterated": "Badlen",
    
    "error": "माफ़ कीजिए, कुछ गलत हो गया।",
    "error_transliterated": "Maaf kijiye, kuch galat ho gaya.",
    
    "help": "मैं आपकी PAN कार्ड आवेदन, आधार लिंकिंग, और कई अन्य चीज़ों में मदद कर सकता हूँ।",
    "help_transliterated": "Main aapki PAN card aavedan, Aadhaar linking, aur kai anya cheezon mein madad kar sakta hoon.",
    
    # Document related
    "documents_needed": "यहाँ आपके लिए आवश्यक दस्तावेज़ हैं:",
    "documents_needed_transliterated": "Yahaan aapke liye aavashyak dastavez hain:",
    
    "ready_to_upload": "अपलोड करने के लिए तैयार हैं? **हाँ** का जवाब दें और मैं अपलोड पैनल खोलूंगा।",
    "ready_to_upload_transliterated": "Upload karne ke liye taiyaar hain? **Haan** ka javaab den aur main upload panel kholunga.",
    
    "upload_now": "बढ़िया! अपलोड पैनल अब खुला है। कृपया अपने दस्तावेज़ एक-एक करके अपलोड करें।",
    "upload_now_transliterated": "Badhiya! Upload panel ab khula hai. Kripya apne dastavez ek-ek karke upload karen.",
    
    "all_docs_received": "सभी दस्तावेज़ प्राप्त हो गए हैं — आप तैयार हैं!",
    "all_docs_received_transliterated": "Sabhi dastavez praapt ho gaye hain — aap taiyaar hain!",
    
    # Document types
    "aadhaar": "आधार कार्ड",
    "aadhaar_transliterated": "Aadhaar card",
    
    "photograph": "फोटोग्राफ",
    "photograph_transliterated": "Photograph",
    
    "identity_proof": "पहचान प्रमाण",
    "identity_proof_transliterated": "Pehchaan pramaan",
    
    "address_proof": "पता प्रमाण",
    "address_proof_transliterated": "Pata pramaan",
    
    "dob_proof": "जन्म तिथि प्रमाण",
    "dob_proof_transliterated": "Janm tithi pramaan",
    
    "optional": "वैकल्पिक",
    "optional_transliterated": "Vaikalpik",
    
    "accepted": "स्वीकृत",
    "accepted_transliterated": "Sweekriti",
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
    """
    Get template text in specified language.
    
    Args:
        key: Template key (e.g., 'greeting', 'ask_name')
        language: Language code ('en', 'ta', 'hi')
        use_transliteration: If True, use English transliteration for Tamil/Hindi
        
    Returns:
        Template text in specified language
    """
    if language == 'ta':
        templates = TAMIL_TEMPLATES
        suffix = '_transliterated' if use_transliteration else ''
    elif language == 'hi':
        templates = HINDI_TEMPLATES
        suffix = '_transliterated' if use_transliteration else ''
    else:
        return ENGLISH_TEMPLATES.get(key, '')
    
    # Try with transliteration suffix first, fallback to base key
    return templates.get(f"{key}{suffix}", templates.get(key, ENGLISH_TEMPLATES.get(key, '')))


def format_response(text: str, language: str = 'en', use_transliteration: bool = True) -> str:
    """
    Format a response in the specified language.
    
    Args:
        text: English text to translate/format
        language: Target language code
        use_transliteration: Use English transliteration
        
    Returns:
        Formatted text (currently returns original text, can be extended with translation API)
    """
    # For now, return original text
    # In future, integrate with translation API (Google Translate, Azure, etc.)
    return text


# ── Test function ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Multilingual Templates Test:")
    print("=" * 60)
    
    for lang in ['en', 'ta', 'hi']:
        print(f"\n{lang.upper()} Templates:")
        print("-" * 60)
        print(f"Greeting: {get_template('greeting', lang)}")
        print(f"Ask Name: {get_template('ask_name', lang)}")
        print(f"Thank You: {get_template('thank_you', lang)}")
