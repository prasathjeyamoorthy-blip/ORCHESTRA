# generation/tamil_complete_pack.py
"""
Complete Tamil Language Pack for PAN Application System
Every feature, flow, and prompt translated to Tamil.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# PAN APPLICATION FLOW - Complete Tamil Translations
# ═══════════════════════════════════════════════════════════════════════════════

TAMIL_COMPLETE = {
    
    # ─── GREETINGS & WELCOME ───────────────────────────────────────────────────
    "welcome": {
        "ta": "வணக்கம்! நான் உங்கள் PAN கார்டு உதவியாளர். உங்களுக்கு PAN பற்றி ஏதேனும் கேள்விகள் உள்ளதா அல்லது புதிய PAN விண்ணப்பிக்க விரும்புகிறீர்களா?",
        "en": "Hello! I'm your PAN card assistant. Do you have any questions about PAN or would you like to apply for a new PAN?"
    },
    
    "greeting": {
        "ta": "வணக்கம்!",
        "en": "Hello!"
    },
    
    "how_can_help": {
        "ta": "நான் உங்களுக்கு எப்படி உதவ முடியும்?",
        "en": "How can I help you?"
    },
    
    # ─── APPLICANT TYPE ────────────────────────────────────────────────────────
    "applicant_type_question": {
        "ta": "உங்கள் **PAN விண்ணப்பத்தை** ஆரம்பிக்கலாம்.\n\nஇந்த விருப்பங்களில் எது உங்களுக்கு பொருந்தும்?",
        "en": "Let's get your **PAN Application** sorted.\n\nWhich of these fits you?"
    },
    
    "applicant_type_options": {
        "option1": {
            "ta": "இந்திய குடிமகன்",
            "en": "Indian Citizen"
        },
        "option2": {
            "ta": "இந்திய நிறுவனம் / HUF / நிறுவனம்",
            "en": "Indian Company / HUF / Firm"
        },
        "option3": {
            "ta": "வெளிநாட்டு குடிமகன் / NRI / வெளிநாட்டு",
            "en": "Foreign Citizen / NRI / Overseas"
        }
    },
    
    # ─── SUBMISSION MODE ───────────────────────────────────────────────────────
    "submission_mode_question": {
        "ta": "**உங்கள் PAN விண்ணப்ப ஆவணங்களை எவ்வாறு சமர்ப்பிக்க விரும்புகிறீர்கள்?**",
        "en": "**How do you want to submit your PAN application documents?**"
    },
    
    "submission_mode_options": {
        "option1": {
            "ta": "ஆதார் அடிப்படையிலான ஆன்லைன் (eKYC)",
            "description_ta": "உங்கள் ஆதார் விவரங்களை eKYC க்காக பயன்படுத்துகிறது — பெயர், புகைப்படம், பிறந்த தேதி, பாலினம் & முகவரி.",
            "en": "Aadhaar-based Online (eKYC)",
            "description_en": "Uses your Aadhaar details for eKYC — Name, Photo, DOB, Gender & Address."
        },
        "option2": {
            "ta": "ஸ்கேன் செய்யப்பட்ட ஆவணங்களைப் பதிவேற்றவும் & eSign",
            "description_ta": "ஸ்கேன் செய்யப்பட்ட புகைப்படம், கையொப்பம் மற்றும் ஆதரவு ஆவணங்களை பதிவேற்றவும், பின்னர் eSign செய்யவும்.",
            "en": "Upload scanned docs & eSign",
            "description_en": "Upload scanned Photo, Signature and supporting documents, then eSign."
        },
        "option3": {
            "ta": "ஆன்லைனில் நிரப்பவும் + கூரியர் உடல் படிவம்",
            "description_ta": "படிவத்தை ஆன்லைனில் நிரப்பவும், அச்சிடவும், கையொப்பமிடவும் மற்றும் Protean இன் புனே அலுவலகத்திற்கு கூரியர்/வேக அஞ்சல் அனுப்பவும்.",
            "en": "Fill online + courier physical form",
            "description_en": "Fill the form online, print, sign and courier/speed-post to Protean's Pune office."
        }
    },
    
    # ─── DELIVERY MODE ─────────────────────────────────────────────────────────
    "delivery_mode_question": {
        "ta": "**உங்கள் PAN கார்டு எவ்வாறு டெலிவரி செய்ய வேண்டும்?**",
        "en": "**How do you want your PAN card to be delivered?**"
    },
    
    "delivery_mode_options": {
        "option1": {
            "ta": "வீட்டிற்கு நகல் + மின்னஞ்சலில் மென்மையான நகல் (கட்டணம் பொருந்தும்)",
            "en": "Physical copy to home + soft copy on email (Fees applicable)"
        },
        "option2": {
            "ta": "மின்னஞ்சலில் மென்மையான நகல் மட்டும் (கட்டணம் பொருந்தும்)",
            "en": "Only soft copy on email (Fees applicable)"
        }
    },
    
    # ─── AADHAAR PHOTO ─────────────────────────────────────────────────────────
    "aadhaar_photo_question": {
        "ta": "**என் PAN கார்டில் என் ஆதார் புகைப்படத்தை அச்சிட நான் ஒப்புக்கொள்கிறேன்.**\n\n> குறிப்பு: உங்கள் ஆதார் புகைப்படத்தைப் பயன்படுத்த விரும்பவில்லை என்றால், தனி புகைப்படத்துடன் PAN விண்ணப்பிக்கலாம்.",
        "en": "**I hereby agree to have my Aadhaar photo printed on my PAN Card.**\n\n> Note: If you do not wish to use your Aadhaar photo, you may apply for a PAN with a separate photograph."
    },
    
    "aadhaar_photo_options": {
        "yes": {
            "ta": "ஆம்",
            "en": "Yes"
        },
        "no": {
            "ta": "இல்லை",
            "en": "No"
        }
    },
    
    # ─── SOURCE OF INCOME ──────────────────────────────────────────────────────
    "source_of_income_question": {
        "ta": "**உங்கள் வருமான மூலத்தைத் தேர்ந்தெடுக்கவும்** (பொருந்தும் அனைத்தையும் தேர்ந்தெடுக்கவும்):",
        "en": "**Please select your Source of Income** (select all that apply):"
    },
    
    "source_of_income_options": {
        "salary": {
            "ta": "சம்பளம்",
            "en": "Salary"
        },
        "business": {
            "ta": "வணிகம் / தொழில் வருமானம்",
            "en": "Income from Business / Profession"
        },
        "house_property": {
            "ta": "வீடு சொத்து வருமானம்",
            "en": "Income from House property"
        },
        "other_sources": {
            "ta": "பிற ஆதாரங்களிலிருந்து வருமானம்",
            "en": "Income from Other sources"
        },
        "capital_gains": {
            "ta": "மூலதன ஆதாயங்கள்",
            "en": "Capital Gains"
        },
        "no_income": {
            "ta": "வருமானம் இல்லை",
            "en": "No income"
        }
    },
    
    # ─── ADDRESS FOR COMMUNICATION ─────────────────────────────────────────────
    "address_for_comm_question": {
        "ta": "**தொடர்புக்கான முகவரி** — தயவுசெய்து பொருந்தும் ஒன்றைத் தேர்ந்தெடுக்கவும்:",
        "en": "**Address for Communication** — Please tick as applicable:"
    },
    
    "address_for_comm_options": {
        "residence": {
            "ta": "வீடு",
            "en": "Residence"
        },
        "office": {
            "ta": "அலுவலகம்",
            "en": "Office"
        },
        "ra": {
            "ta": "பிரதிநிதி மதிப்பீட்டாளர் (RA)",
            "en": "Representative Assessee (RA)"
        }
    },
    
    "address_for_comm_hint": {
        "ta": "**eKYC (தனிநபர் மட்டும்) மூலம் காகிதமற்ற PAN விண்ணப்பத்திற்கான முக்கியமான வழிமுறைகள்:**\n1. ஆதார் அட்டையில் பயன்படுத்தப்படும் முகவரி PAN விண்ணப்பத்தில் வசிப்பிட முகவரியாக பயன்படுத்தப்படும் — தனியாக வசிப்பிட முகவரியை நிரப்ப வேண்டிய அவசியமில்லை.\n2. PAN கார்டு ஆதாரில் குறிப்பிடப்பட்ட முகவரியில் அனுப்பப்படும்.\n3. ஆதார் தரவுத்தளத்தின்படி முகவரியின் நீளம் வருமான வரி துறை குறிப்பிட்ட நீளத்தை மீறினால், நீங்கள் eKYC சேவையைப் பெற முடியாது.",
        "en": "**Important instructions for paperless PAN application through e-KYC (Only For Individual):**\n1. The address used in Aadhaar card would be used in PAN application as residence address — no need to fill residential address separately.\n2. PAN card will be dispatched at address mentioned in Aadhaar.\n3. If length of address as per Aadhaar database exceeds the length specified by Income Tax Department, you will not be able to avail e-KYC service."
    },
    
    # ─── RESIDENTIAL STATUS ────────────────────────────────────────────────────
    "residential_status_question": {
        "ta": "**உங்கள் குடியிருப்பு நிலை என்ன?**",
        "en": "**What is your Residential Status?**"
    },
    
    "residential_status_options": {
        "resident": {
            "ta": "குடியிருப்பவர்",
            "en": "Resident"
        },
        "non_resident": {
            "ta": "குடியிராதவர்",
            "en": "Non-resident"
        },
        "rnor": {
            "ta": "குடியிருப்பவர் ஆனால் சாதாரணமாக குடியிராதவர்",
            "en": "Resident but not ordinarily resident"
        }
    },
    
    # ─── REPRESENTATIVE ASSESSEE ───────────────────────────────────────────────
    "rep_assessee_question": {
        "ta": "**பிரதிநிதி மதிப்பீட்டாளரை நியமிக்கிறீர்களா?**\n\n> பிரதிநிதி மதிப்பீட்டாளர் என்பது மற்றொரு நபரின் சார்பாக வரி கடமைகளை நிர்வகிக்கும் ஒருவர் (எ.கா. சிறியவருக்கு பாதுகாவலர், அல்லது இறந்தவருக்கு சட்ட வாரிசு). மற்றொருவர் சார்பாக நீங்கள் விண்ணப்பிக்கும் பட்சத்தில் மட்டும் **ஆம்** என்பதைத் தேர்ந்தெடுக்கவும்.",
        "en": "**Appointing Representative Assessee?**\n\n> A Representative Assessee is someone who manages tax obligations on behalf of another person (e.g. a guardian for a minor, or a legal heir for a deceased person). Select **Yes** only if you are applying on behalf of someone else."
    },
    
    "rep_assessee_options": {
        "yes": {
            "ta": "ஆம்",
            "en": "Yes"
        },
        "no": {
            "ta": "இல்லை",
            "en": "No"
        }
    },
    
    # ─── PERSONAL DETAILS ──────────────────────────────────────────────────────
    "details_collection_intro": {
        "ta": "சிறப்பு! இப்போது உங்கள் விவரங்களைச் சேகரிப்போம்.\n\nஇனி எளிதாக இருக்கும் — உங்கள் **முழு பெயர், தாயின் பெயர், மின்னஞ்சல்** மற்றும் **ஆண்டு வருமானம்** என்ன என்று சொல்லுங்கள். எல்லாவற்றையும் ஒரே செய்தியில் பகிரலாம் அல்லது ஒவ்வொன்றாக பகிரலாம் — உங்கள் தேர்வு!",
        "en": "Great! Now let's collect your details.\n\nThis will be easy — just tell me your **full name, mother's name, email** and **annual income**. You can share everything in one message, or one-by-one — your choice!"
    },
    
    "ask_full_name": {
        "ta": "உங்கள் முழு பெயர் என்ன (ஆதாரில் உள்ளபடி)?",
        "en": "What is your full name (as per Aadhaar)?"
    },
    
    "ask_mother_name": {
        "ta": "உங்கள் தாயின் முழு பெயர் என்ன?",
        "en": "What is your mother's full name?"
    },
    
    "ask_email": {
        "ta": "உங்கள் மின்னஞ்சல் முகவரி என்ன?",
        "en": "What is your email address?"
    },
    
    "ask_salary": {
        "ta": "உங்கள் ஆண்டு வருமானம் / சம்பளம் என்ன?",
        "en": "What is your annual income / salary?"
    },
    
    # ─── CONFIRMATION ──────────────────────────────────────────────────────────
    "confirmation_intro": {
        "ta": "கிட்டத்தட்ட முடிந்துவிட்டது! இதோ உங்கள் விவரங்களின் சுருக்கம்:",
        "en": "Almost done! Here's a summary of your details:"
    },
    
    "confirmation_question": {
        "ta": "**எல்லாம் சரியாக இருக்கிறதா?**",
        "en": "**Does everything look correct?**"
    },
    
    "confirmation_options": {
        "yes": {
            "ta": "ஆம், தொடரவும்",
            "en": "Yes, proceed"
        },
        "no": {
            "ta": "இல்லை, மாற்றவும்",
            "en": "No, change something"
        }
    },
    
    # ─── DOCUMENTS ─────────────────────────────────────────────────────────────
    "documents_intro": {
        "ta": "அற்புதம்! கடைசி படி: **ஆவணங்கள்**.\n\nஇதோ உங்களுக்கு தேவையானவை:",
        "en": "Awesome! Last step: **Documents**.\n\nHere's what you need:"
    },
    
    "document_types": {
        "aadhaar": {
            "ta": "ஆதார் அட்டை",
            "description_ta": "முன் & பின் ஸ்கேன் அல்லது புகைப்படம்",
            "en": "Aadhaar Card",
            "description_en": "Front & back scan or photo"
        },
        "photograph": {
            "ta": "விண்ணப்பதாரர் புகைப்படம்",
            "description_ta": "பாஸ்போர்ட் அளவு, வெள்ளை பின்னணி",
            "en": "Applicant Photograph",
            "description_en": "Passport-size, white background"
        },
        "driving_license": {
            "ta": "ஓட்டுநர் உரிமம்",
            "description_ta": "செல்லுபடியாகும் உரிமம் — முன் பக்கம்",
            "en": "Driving License",
            "description_en": "Valid license — front side"
        }
    },
    
    "upload_instructions": {
        "ta": "📎 **paperclip பொத்தானைப்** பயன்படுத்தி உங்கள் கோப்புகளை இணைக்கவும் — நான் எல்லாவற்றையும் பிரித்தெடுப்பேன்.",
        "en": "Use the 📎 **paperclip button** to attach your files — I'll extract everything."
    },
    
    "document_received": {
        "ta": "பெறப்பட்டது ✓",
        "en": "Received ✓"
    },
    
    "all_documents_received": {
        "ta": "அனைத்து ஆவணங்களும் பெறப்பட்டன — நீங்கள் தயாராக இருக்கிறீர்கள்! 🎉",
        "en": "All documents received — you're all set! 🎉"
    },
    
    # ─── COMMON ACTIONS ────────────────────────────────────────────────────────
    "yes": {
        "ta": "ஆம்",
        "en": "Yes"
    },
    
    "no": {
        "ta": "இல்லை",
        "en": "No"
    },
    
    "proceed": {
        "ta": "தொடரவும்",
        "en": "Proceed"
    },
    
    "change": {
        "ta": "மாற்றவும்",
        "en": "Change"
    },
    
    "cancel": {
        "ta": "ரத்து செய்",
        "en": "Cancel"
    },
    
    "back": {
        "ta": "பின்னால்",
        "en": "Back"
    },
    
    "continue": {
        "ta": "தொடரவும்",
        "en": "Continue"
    },
    
    "submit": {
        "ta": "சமர்ப்பிக்கவும்",
        "en": "Submit"
    },
    
    # ─── ERRORS & VALIDATION ───────────────────────────────────────────────────
    "error_generic": {
        "ta": "மன்னிக்கவும், ஏதோ தவறு நடந்துவிட்டது. மீண்டும் முயற்சிக்கவும்.",
        "en": "Sorry, something went wrong. Please try again."
    },
    
    "error_invalid_email": {
        "ta": "தவறான மின்னஞ்சல் முகவரி. செல்லுபடியாகும் மின்னஞ்சலை உள்ளிடவும்.",
        "en": "Invalid email address. Please enter a valid email."
    },
    
    "error_missing_field": {
        "ta": "இந்த புலம் தேவை. தயவுசெய்து மதிப்பை வழங்கவும்.",
        "en": "This field is required. Please provide a value."
    },
    
    # ─── HELP & SUPPORT ────────────────────────────────────────────────────────
    "help_message": {
        "ta": "நான் உங்களுக்கு உதவ முடியும்:\n\n• புதிய PAN விண்ணப்பிக்க\n• PAN நிலையைச் சரிபார்க்க\n• ஆதாருடன் PAN இணைக்க\n• PAN விவரங்களைத் திருத்த\n• PAN ஐ மீண்டும் அச்சிட\n• மற்றும் பல!",
        "en": "I can help you:\n\n• Apply for new PAN\n• Check PAN status\n• Link PAN with Aadhaar\n• Correct PAN details\n• Reprint PAN\n• And more!"
    },
    
    "need_help": {
        "ta": "உதவி தேவையா?",
        "en": "Need help?"
    },
    
    # ─── FEES & PRICING ────────────────────────────────────────────────────────
    "fees_physical": {
        "ta": "| PAN கார்டு அனுப்புதல் | PAN விண்ணப்ப முறை | செயலாக்க கட்டணம் (GST உள்ளடக்கி) |\n|---|---|---|\n| இந்திய முகவரி | e-KYC & e-Sign / e-Sign ஸ்கேன் செய்யப்பட்டது | ₹ 101 |\n| இந்திய முகவரி | உடல் முறை | ₹ 107 |\n| வெளிநாட்டு முகவரி | e-Sign ஸ்கேன் செய்யப்பட்டது | ₹ 1,011 |\n| வெளிநாட்டு முகவரி | உடல் முறை | ₹ 1,017 |\n\n> உங்கள் தொடர்பு முகவரியில் **உடல் PAN கார்டு** + உங்கள் மின்னஞ்சலில் PDF இல் **e-PAN** பெறுவீர்கள்.",
        "en": "| PAN Card Dispatch | Mode of PAN Application | Processing Fee (incl. GST) |\n|---|---|---|\n| Indian address | e-KYC & e-Sign / e-Sign scanned | ₹ 101 |\n| Indian address | Physical Mode | ₹ 107 |\n| Foreign address | e-Sign scanned | ₹ 1,011 |\n| Foreign address | Physical Mode | ₹ 1,017 |\n\n> You will receive a **Physical PAN card** at your communication address + **e-PAN** in PDF to your email."
    },
    
    "fees_soft_only": {
        "ta": "| PAN விண்ணப்ப முறை | செயலாக்க கட்டணம் (GST உள்ளடக்கி) |\n|---|---|\n| e-KYC & e-Sign / e-Sign ஸ்கேன் செய்யப்பட்டது | ₹ 66 |\n| உடல் முறை | ₹ 72 |\n\n> உங்கள் மின்னஞ்சலுக்கு **e-PAN** (PDF) மட்டும் அனுப்பப்படும். உடல் கார்டு அனுப்பப்படாது.",
        "en": "| Mode of PAN Application | Processing Fee (incl. GST) |\n|---|---|\n| e-KYC & e-Sign / e-Sign scanned | ₹ 66 |\n| Physical Mode | ₹ 72 |\n\n> Only **e-PAN** (PDF) will be sent to your email. No physical card will be dispatched."
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_tamil_text(key: str, fallback_to_english: bool = True) -> str:
    """
    Get Tamil text for a given key.
    
    Args:
        key: Text key (e.g., 'welcome', 'ask_full_name')
        fallback_to_english: Return English if Tamil not available
        
    Returns:
        Tamil text or English fallback
    """
    if key not in TAMIL_COMPLETE:
        return ""
    
    item = TAMIL_COMPLETE[key]
    if isinstance(item, dict):
        if "ta" in item:
            return item["ta"]
        elif fallback_to_english and "en" in item:
            return item["en"]
    
    return ""


def get_bilingual_text(key: str, show_english: bool = True) -> str:
    """
    Get both Tamil and English text.
    
    Args:
        key: Text key
        show_english: Whether to include English translation
        
    Returns:
        Tamil text with optional English below
    """
    if key not in TAMIL_COMPLETE:
        return ""
    
    item = TAMIL_COMPLETE[key]
    if isinstance(item, dict):
        tamil = item.get("ta", "")
        english = item.get("en", "")
        
        if show_english and tamil and english:
            return f"{tamil}\n\n*({english})*"
        return tamil or english
    
    return ""


def translate_options(options_dict: dict, language: str = "ta") -> list:
    """
    Translate option dict to list of strings in specified language.
    
    Args:
        options_dict: Dict of options with language keys
        language: Target language code
        
    Returns:
        List of translated option strings
    """
    result = []
    for key, value in options_dict.items():
        if isinstance(value, dict) and language in value:
            result.append(value[language])
        elif isinstance(value, str):
            result.append(value)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE USAGE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Tamil Complete Language Pack Test")
    print("=" * 70)
    
    # Test welcome message
    print("\n1. Welcome Message:")
    print(get_bilingual_text("welcome"))
    
    # Test applicant type
    print("\n2. Applicant Type Question:")
    print(get_bilingual_text("applicant_type_question"))
    print("\nOptions:")
    opts = TAMIL_COMPLETE["applicant_type_options"]
    for i, (key, val) in enumerate(opts.items(), 1):
        print(f"  {i}. {val['ta']} ({val['en']})")
    
    # Test submission mode
    print("\n3. Submission Mode:")
    print(get_tamil_text("submission_mode_question"))
    
    # Test personal details
    print("\n4. Personal Details:")
    print(get_tamil_text("ask_full_name"))
    print(get_tamil_text("ask_mother_name"))
    print(get_tamil_text("ask_email"))
    print(get_tamil_text("ask_salary"))
