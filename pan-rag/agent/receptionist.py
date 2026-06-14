# agent/receptionist.py
import re
from agent.service_flows import detect_service, get_service, SERVICES
from agent.flow_manager import FlowManager
from agent.user_profile import prefill_flow_from_profile, save_flow_to_profile
from agent.document_access import request_document_access, verify_document_access
from intent.language_detector import detect_language_with_confidence, get_language_name
from generation.multilingual_templates import get_template


# ── Off-topic detector ────────────────────────────────────────────
_OFF_TOPIC_PATTERN = re.compile(
    r"^(why|what|how\s+does|how\s+is|what\s+is|what\s+are|"
    r"should\s+i|do\s+i\s+need|is\s+it|are\s+there|"
    r"tell\s+me|explain|describe|difference|benefit|reason|"
    r"purpose|importance|advantage|when\s+should|who\s+needs|"
    r"what\s+happens|what\s+if|how\s+long|how\s+much|"
    r"what\s+is\s+the\s+fee|i\s+want\s+to\s+know|"
    r"i\s+want\s+to\s+understand|curious|"
    r"i\s+have\s+(a\s+)?question|question|doubt|query|"
    r"can\s+i\s+ask|may\s+i\s+ask|one\s+question)",
    re.IGNORECASE
)

# ── Casual/unrelated conversation patterns ────────────────────────
_CASUAL_CHAT_PATTERN = re.compile(
    r"\b(coffee|tea|drink|food|eat|hungry|thirsty|weather|"
    r"hello|hi|hey|good\s+morning|good\s+evening|good\s+afternoon|"
    r"how\s+are\s+you|what'?s\s+up|wassup|sup|"
    r"joke|funny|laugh|story|game|play|"
    r"movie|music|song|video|watch|"
    r"love|hate|like|dislike|favorite|favourite|"
    r"sports|cricket|football|match|"
    r"do\s+you\s+(want|like|have|know)|"
    r"are\s+you\s+(a\s+)?(robot|bot|human|ai|assistant)|"
    r"who\s+(are|is)\s+you|what\s+(are|is)\s+you)\b",
    re.IGNORECASE
)

_CANCEL_PATTERN = re.compile(
    r"^(nah|nope|stop|cancel|quit|exit|nevermind|never mind|"
    r"forget it|forget this|leave it|not now|not interested|"
    r"i changed my mind|go back|abort|end|close|done for now|"
    r"skip|skip this|i don't want|i dont want|not anymore|"
    r"stop that|stop this|cancel that|cancel this|quit this)\b",
    re.IGNORECASE
)

def _is_cancellation(q: str) -> bool:
    q = q.strip()
    # Single bare "no" is NEVER a cancellation — it's a valid answer to yes/no questions
    if q.lower() in ("no", "n"):
        return False
    return bool(_CANCEL_PATTERN.match(q))

_UPLOAD_NOW_PATTERN = re.compile(
    r"(upload|submit|attach|send|provide|share|give).{0,40}(now|later|afterwards|after|soon|first|document|file|proof|aadhaar|photo)"
    r"|(later|afterwards|after\s+this|after\s+that|will\s+do\s+it|do\s+it\s+later).{0,30}(upload|submit|document|file)"
    r"|\b(i\s+will\s+upload|let\s+me\s+upload|i\s+want\s+to\s+upload|ready\s+to\s+upload|upload\s+now|upload\s+the\s+doc)",
    re.IGNORECASE
)

def _is_upload_now(q): return bool(_UPLOAD_NOW_PATTERN.search(q.strip()))

def _is_off_topic_during_flow(q):
    """
    Detect if user's message is off-topic during a guided flow.
    Returns True if the message is unrelated to PAN application process.
    """
    q = q.strip()
    
    # Never treat single-word flow answers as off-topic
    if len(q.split()) <= 2:
        return False
    
    # Check for casual/unrelated conversation
    if _CASUAL_CHAT_PATTERN.search(q):
        return True
    
    # Check for general questions
    if _OFF_TOPIC_PATTERN.match(q):
        return True
    
    # Long questions with question marks are likely off-topic
    if len(q) > 80 and '?' in q:
        return True
    
    return False


# ── Fee tables (rendered as markdown) ────────────────────────────

_FEE_PHYSICAL = """
| PAN Card Dispatch | Mode of PAN Application | Processing Fee (incl. GST) |
|---|---|---|
| Indian address | e-KYC & e-Sign / e-Sign scanned | ₹ 101 |
| Indian address | Physical Mode | ₹ 107 |
| Foreign address | e-Sign scanned | ₹ 1,011 |
| Foreign address | Physical Mode | ₹ 1,017 |

> You will receive a **Physical PAN card** at your communication address + **e-PAN** in PDF to your email.
"""

_FEE_SOFT = """
| Mode of PAN Application | Processing Fee (incl. GST) |
|---|---|
| e-KYC & e-Sign / e-Sign scanned | ₹ 66 |
| Physical Mode | ₹ 72 |

> Only **e-PAN** (PDF) will be sent to your email. No physical card will be dispatched.
"""

# ── Helper: Get saved PAN preferences from profile ──────────────────────────
def _get_saved_pan_preferences(user_id: str, current_state: dict) -> dict | None:
    """
    Check if user has saved PAN application preferences from a previous session.
    Returns dict with saved preferences or None if no preferences found.
    """
    try:
        profile = load_user_profile(user_id)
        if not profile:
            return None
        
        # Check if user has any PAN preferences saved
        saved_prefs = {}
        
        if profile.get("submission_mode"):
            saved_prefs["submission_mode"] = profile["submission_mode"]
        if profile.get("delivery_mode"):
            saved_prefs["delivery_mode"] = profile["delivery_mode"]
        if profile.get("aadhaar_photo") is not None:
            saved_prefs["aadhaar_photo"] = profile["aadhaar_photo"]
        if profile.get("source_of_income"):
            saved_prefs["source_of_income"] = profile["source_of_income"]
        if profile.get("address_for_comm"):
            saved_prefs["address_for_comm"] = profile["address_for_comm"]
        if profile.get("residential_status"):
            saved_prefs["residential_status"] = profile["residential_status"]
        if profile.get("rep_assessee") is not None:
            saved_prefs["rep_assessee"] = profile["rep_assessee"]
        
        # Only return if we have at least 3 preferences saved (meaningful previous application)
        if len(saved_prefs) >= 3:
            return saved_prefs
        
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load saved preferences: {e}")
        return None


def _build_preferences_reuse_prompt(saved_prefs: dict) -> str:
    """Build a friendly prompt showing saved preferences and asking if user wants to reuse them."""
    lines = [
        "Welcome back! I see you've applied for PAN before. 🎉",
        "",
        "**Your previous choices:**",
        "",
    ]
    
    # Format each saved preference
    if saved_prefs.get("submission_mode"):
        lines.append(f"📝 **Submission mode:** {saved_prefs['submission_mode']}")
    
    if saved_prefs.get("delivery_mode"):
        lines.append(f"📦 **Delivery mode:** {saved_prefs['delivery_mode']}")
    
    if saved_prefs.get("aadhaar_photo") is not None:
        aadhaar_choice = "Yes" if saved_prefs["aadhaar_photo"] else "No"
        lines.append(f"📸 **Aadhaar photo on PAN:** {aadhaar_choice}")
    
    if saved_prefs.get("source_of_income"):
        sources = saved_prefs["source_of_income"]
        if isinstance(sources, list):
            sources = ", ".join(sources)
        lines.append(f"💰 **Source of income:** {sources}")
    
    if saved_prefs.get("address_for_comm"):
        lines.append(f"📍 **Address for communication:** {saved_prefs['address_for_comm']}")
    
    if saved_prefs.get("residential_status"):
        lines.append(f"🏠 **Residential status:** {saved_prefs['residential_status']}")
    
    if saved_prefs.get("rep_assessee") is not None:
        rep_choice = "Yes" if saved_prefs["rep_assessee"] else "No"
        lines.append(f"👤 **Representative Assessee:** {rep_choice}")
    
    lines.extend([
        "",
        "**Would you like to use the same options for this application?**",
        "",
        "Reply **Yes** to use these options, or **No** to choose different options.",
    ])
    
    return "\n".join(lines)


def _build_individual_preferences_review_prompt(saved_answers: dict) -> str:
    """
    Build a prompt showing ALL saved optional question answers at once.
    User can review all and specify which ones to change.
    """
    lines = [
        "I see you've answered these questions before! 📋",
        "",
        "**Your previous answers:**",
        "",
    ]
    
    # Show all saved answers
    if saved_answers.get("submission_mode"):
        lines.append(f"1️⃣ **Submission mode:** {saved_answers['submission_mode']}")
    
    if saved_answers.get("delivery_mode"):
        lines.append(f"2️⃣ **Delivery mode:** {saved_answers['delivery_mode']}")
    
    if saved_answers.get("aadhaar_photo") is not None:
        aadhaar_choice = "Yes" if saved_answers["aadhaar_photo"] else "No"
        lines.append(f"3️⃣ **Aadhaar photo on PAN:** {aadhaar_choice}")
    
    if saved_answers.get("source_of_income"):
        sources = saved_answers["source_of_income"]
        if isinstance(sources, list):
            sources = ", ".join(sources)
        lines.append(f"4️⃣ **Source of income:** {sources}")
    
    if saved_answers.get("address_for_comm"):
        lines.append(f"5️⃣ **Address for communication:** {saved_answers['address_for_comm']}")
    
    if saved_answers.get("residential_status"):
        lines.append(f"6️⃣ **Residential status:** {saved_answers['residential_status']}")
    
    if saved_answers.get("rep_assessee") is not None:
        rep_choice = "Yes" if saved_answers["rep_assessee"] else "No"
        lines.append(f"7️⃣ **Representative Assessee:** {rep_choice}")
    
    lines.extend([
        "",
        "**Would you like to use all these answers, or change some?**",
        "",
        "• Reply **All same** to use all previous answers",
        "• Reply **Change [number(s)]** to modify specific answers (e.g., \"Change 1 and 3\" or \"Change 2,5,7\")",
        "• Reply **All new** to answer all questions again",
    ])
    
    return "\n".join(lines)


def _display_user_profile(user_id: str, flow: FlowManager, account_email: str = "", session_id: str = "", language: str = "en") -> dict:
    """
    Display all information collected about the user from profile, current flow, and recent conversations.
    """
    from agent.user_profile import get_user_profile
    from memory.memory_manager import MemoryManager

    ta = language == "ta"

    # Collect information from multiple sources
    profile = get_user_profile(user_id) if user_id else None
    flow_state = flow.state
    
    # Also check recent conversation history for mentioned details
    memory = MemoryManager()
    recent_context = memory.get_cached_context(session_id, user_id) if session_id else ""
    
    # Build the display
    header = "இதுவரை நான் உங்களைப் பற்றி அறிந்தவை: 📋" if ta else "Here's what I know about you so far: 📋"
    lines = [header, ""]
    has_info = False
    
    # Personal Details
    personal_details = []
    
    full_name = flow_state.get("full_name") or (profile.get("full_name") if profile else None)
    if full_name:
        lbl = "**முழு பெயர்:**" if ta else "**Full name:**"
        personal_details.append(f"{lbl} {full_name}")
        has_info = True

    grandfather_name = flow_state.get("grandfather_name") or (profile.get("grandfather_name") if profile else None)
    if grandfather_name:
        lbl = "**தாத்தாவின் பெயர்:**" if ta else "**Grandfather's name:**"
        personal_details.append(f"{lbl} {grandfather_name}")
        has_info = True

    mother_name = flow_state.get("mother_name") or (profile.get("mother_name") if profile else None)
    if mother_name:
        lbl = "**தாயின் பெயர்:**" if ta else "**Mother's name:**"
        personal_details.append(f"{lbl} {mother_name}")
        has_info = True
    
    email = flow_state.get("email") or (profile.get("email") if profile else None) or account_email
    if email:
        lbl = "**மின்னஞ்சல்:**" if ta else "**Email:**"
        personal_details.append(f"{lbl} {email}")
        has_info = True
    
    phone = flow_state.get("phone") or (profile.get("phone") if profile else None)
    if phone:
        lbl = "**தொலைபேசி:**" if ta else "**Phone:**"
        personal_details.append(f"{lbl} {phone}")
        has_info = True
    
    salary = flow_state.get("salary") or (profile.get("annual_income") if profile else None)
    if salary:
        lbl = "**ஆண்டு வருமானம்:**" if ta else "**Annual income:**"
        personal_details.append(f"{lbl} {salary}")
        has_info = True
    
    if personal_details:
        sec_hdr = "**தனிப்பட்ட விவரங்கள்:**" if ta else "**Personal Details:**"
        lines.append(sec_hdr)
        lines.extend(personal_details)
        lines.append("")
    
    # PAN Application Preferences
    pan_prefs = []
    
    pan_preferences = profile.get("pan_preferences", {}) if profile else {}
    if isinstance(pan_preferences, str):
        try:
            import json
            pan_preferences = json.loads(pan_preferences)
        except Exception:
            pan_preferences = {}
    
    submission_mode = flow_state.get("submission_mode") or pan_preferences.get("submission_mode")
    if submission_mode:
        lbl = "**சமர்ப்பிக்கும் முறை:**" if ta else "**Submission mode:**"
        pan_prefs.append(f"{lbl} {submission_mode}")
        has_info = True
    
    delivery_mode = flow_state.get("delivery_mode") or pan_preferences.get("delivery_mode")
    if delivery_mode:
        delivery_text = "Physical + e-PAN" if delivery_mode == "physical_and_soft" else "e-PAN only" if delivery_mode == "soft_only" else delivery_mode
        lbl = "**PAN விநியோகம்:**" if ta else "**PAN delivery:**"
        pan_prefs.append(f"{lbl} {delivery_text}")
        has_info = True
    
    aadhaar_photo = flow_state.get("aadhaar_photo")
    if aadhaar_photo is None and pan_preferences:
        aadhaar_photo = pan_preferences.get("aadhaar_photo")
    if aadhaar_photo is not None:
        lbl = "**ஆதார் புகைப்படம்:**" if ta else "**Aadhaar photo on PAN:**"
        val = ("ஆம்" if aadhaar_photo else "இல்லை") if ta else ("Yes" if aadhaar_photo else "No")
        pan_prefs.append(f"{lbl} {val}")
        has_info = True
    
    source_of_income = flow_state.get("source_of_income") or pan_preferences.get("source_of_income")
    if source_of_income:
        if isinstance(source_of_income, list):
            source_of_income = ", ".join(source_of_income)
        lbl = "**வருமான மூலம்:**" if ta else "**Source of income:**"
        pan_prefs.append(f"{lbl} {source_of_income}")
        has_info = True
    
    address_for_comm = flow_state.get("address_for_comm") or pan_preferences.get("address_for_comm")
    if address_for_comm:
        lbl = "**தொடர்பு முகவரி:**" if ta else "**Address for communication:**"
        pan_prefs.append(f"{lbl} {address_for_comm}")
        has_info = True
    
    residential_status = flow_state.get("residential_status") or pan_preferences.get("residential_status")
    if residential_status:
        lbl = "**குடியிருப்பு நிலை:**" if ta else "**Residential status:**"
        pan_prefs.append(f"{lbl} {residential_status}")
        has_info = True
    
    rep_assessee = flow_state.get("rep_assessee")
    if rep_assessee is None and pan_preferences:
        rep_assessee = pan_preferences.get("rep_assessee")
    if rep_assessee is not None:
        lbl = "**பிரதிநிதி நியமனம்:**" if ta else "**Representative Assessee:**"
        val = ("ஆம்" if rep_assessee else "இல்லை") if ta else ("Yes" if rep_assessee else "No")
        pan_prefs.append(f"{lbl} {val}")
        has_info = True
    
    if pan_prefs:
        sec_hdr = "**விண்ணப்ப விவரங்கள்:**" if ta else "**PAN Application Preferences:**"
        lines.append(sec_hdr)
        lines.extend(pan_prefs)
        lines.append("")
    
    # Check if there's an active or incomplete flow
    if flow.has_active_flow():
        current_step = flow.get_current_step()
        service_id = flow_state.get("service_id")
        if service_id:
            if ta:
                lines.append("**தற்போதைய விண்ணப்ப நிலை:**")
                lines.append(f"உங்கள் விண்ணப்பம் தொடர்கிறது: **{current_step}**")
            else:
                lines.append("**Current Application Status:**")
                lines.append(f"You have an in-progress application at step: **{current_step}**")
            lines.append("")
            has_info = True
    
    # If no information found
    if not has_info:
        if recent_context and len(recent_context) > 50:
            msg = ("முன்பு நாம் பேசியிருக்கிறோம், ஆனால் இன்னும் விவரங்கள் சேமிக்கப்படவில்லை. தொடர்ந்து பேசும்போது நினைவில் வைப்பேன்.\n\nPAN விண்ணப்பம் தொடங்கவா?"
                   if ta else
                   "I can see we've chatted before, but I don't have any saved details yet. As we continue our conversation and you share information, I'll remember it to help you better.\n\nWould you like to start a PAN application or ask me anything about PAN services?")
        else:
            msg = ("இன்னும் உங்களைப் பற்றி தகவல்கள் இல்லை. நீங்கள் பகிரும்போது நினைவில் வைப்பேன்.\n\nPAN விண்ணப்பம் தொடங்கவா?"
                   if ta else
                   "I don't have any information about you yet. As we chat and you share details, I'll remember them to make our conversations more helpful.\n\nWould you like to start a PAN application or ask me anything about PAN services?")
        return {
            "answer": msg,
            "sources": [],
            "followups": ["Apply for new PAN", "Check PAN status", "Link Aadhaar with PAN"],
            "guided": False,
        }
    
    # Add footer
    lines.append("---")
    if ta:
        lines.append("இந்த தகவல்கள் பாதுகாப்பாக சேமிக்கப்பட்டுள்ளன.")
        lines.append("\nதொடர்ந்து விண்ணப்பிக்கவா அல்லது புதுதாக தொடங்கவா?")
    else:
        lines.append("This information is saved securely and will be used to help you with PAN services.")
        lines.append("\nWould you like to continue with your application or start a new one?")
    
    followups = (["விண்ணப்பத்தை தொடரவும்", "புதிய விண்ணப்பம்", "PAN நிலையை சரிபார்க்கவும்"]
                 if ta else
                 ["Continue application", "Start new application", "Check PAN status"])
    return {
        "answer": "\n".join(lines),
        "sources": [],
        "followups": followups,
        "guided": False,
    }


# ── Public entry point ────────────────────────────────────────────
def handle_message(
    question: str,
    session_id: str,
    language: str = "en",
    rag_answer: str = None,
    user_context: str = None,
    account_email: str = "",
    user_id: str = None,
) -> dict | None:
    flow = FlowManager(session_id, user_id or "anonymous")
    
    # ── Language resolution ───────────────────────────────────────────────────
    # Priority: explicit UI selection > stored preference > detected
    # When the UI sends "en" explicitly we ALWAYS honour it — clearing any
    # previously stored ta/hi preference so the switch takes effect immediately.
    stored_pref = flow.state.get("preferred_language")

    if language in ("ta", "hi"):
        # Explicit non-English selection — respect it and save it
        print(f"[Language] Using explicit selection: {get_language_name(language)}")
        flow.state["preferred_language"] = language
        flow.save()
    elif language == "en":
        # Explicit English selection from the UI — always honour it and clear
        # any previously stored Tamil/Hindi preference so the switch takes effect.
        if stored_pref != "en":
            print(f"[Language] Switching to English — clearing stored preference '{stored_pref}'")
        flow.state["preferred_language"] = "en"
        flow.save()
        print(f"[Language] Using English: {get_language_name(language)}")
    else:
        # Detect from user's text
        detected_lang, confidence = detect_language_with_confidence(question)
        if confidence > 0.3:
            language = detected_lang
            flow.state["preferred_language"] = language
            flow.save()
            print(f"[Language] Detected {get_language_name(language)} (confidence: {confidence:.2%})")
        else:
            language = "en"
            print(f"[Language] Defaulting to English")
    
    # Always store current language in flow state for use by other functions
    flow.state["_current_language"] = language
    flow.save()
    
    # ── Extract and save name if user provides it in casual conversation ──
    # Patterns: "my name is X", "i am X", "i'm X", "call me X"
    _name_statement = re.compile(
        r"\b(my\s+name\s+is|i\s+am|i'm|call\s+me)\s+([A-Z][a-zA-Z\s]{1,30})\b",
        re.IGNORECASE
    )
    name_match = _name_statement.search(question)
    if name_match:
        provided_name = name_match.group(2).strip()
        # Save to flow state and profile if valid (not a common word)
        _common_words = {"hello", "here", "ready", "done", "fine", "good", "ok", "okay"}
        if provided_name.lower() not in _common_words and len(provided_name) >= 2:
            if not flow.state.get("full_name"):
                flow.state["full_name"] = provided_name
                flow.save()
                print(f"[receptionist] Extracted and saved name: {provided_name}")
                # Save to Supabase profile
                if user_id and user_id != "anonymous":
                    from agent.user_profile import save_user_profile
                    save_user_profile(user_id, {"full_name": provided_name})
    
    # ── ALWAYS prefill from user_context if provided (most up-to-date source) ──────
    # Node sends this on EVERY request with latest profile data from Supabase
    if user_context and user_id:
        print(f"[DEBUG] Prefilling from user_context for user {user_id}")
        _prefill_from_user_context(flow, user_context)
        flow.save()
        print(f"[DEBUG] After user_context prefill: full_name={flow.state.get('full_name')}, mother_name={flow.state.get('mother_name')}, salary={flow.state.get('salary')}")
    
    # ── Prefill flow from user profile EVERY TIME there's no active flow ──────
    # This ensures profile data is loaded in new sessions or after flow completion
    if user_id and not flow.has_active_flow():
        # Only prefill if not already done in this session
        if not flow.state.get("_profile_loaded"):
            print(f"[DEBUG] Prefilling profile for user {user_id} in session {session_id}")
            flow.state = prefill_flow_from_profile(user_id, flow.state)
            flow.state["_profile_loaded"] = True
            flow.save()
            print(f"[DEBUG] Profile prefilled: full_name={flow.state.get('full_name')}, mother_name={flow.state.get('mother_name')}")
        else:
            print(f"[DEBUG] Profile already loaded for this session")
    elif user_id and flow.has_active_flow():
        print(f"[DEBUG] Active flow exists, skipping profile prefill")

    # ── Inject account email into flow state ─────────────────────
    # Priority: explicit account_email param > parse from user_context
    if account_email and not flow.state.get("_account_email"):
        flow.state["_account_email"] = account_email.lower().strip()
        flow.save()
    elif user_context and not flow.state.get("_account_email"):
        _email_in_ctx = re.search(r"- Email:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", user_context)
        if _email_in_ctx:
            flow.state["_account_email"] = _email_in_ctx.group(1).lower()
            flow.save()

    # ── Handle "show me what you know about me" query ────────────
    # Matches English and Tamil (romanized) patterns
    _show_profile = re.compile(
        r"\b(show|tell|what|display|list)\s+(me\s+)?(what|everything|all|info|information|details|data)\s+"
        r"(you\s+)?(know|have|collected|saved|stored|remember)\s+(about\s+me|on\s+me|for\s+me)"
        # "what are the personal details i gave you"
        r"|\b(personal\s+details?|details?\s+(i\s+gave|you\s+have|you\s+stored|you\s+collected))\b"
        # Tamil romanized patterns: "enna details koduthen", "na enna details lam koduthen"
        r"|\b(enna|yenna)\s+(details?|info|thakaval|thevayal|visarangal)\s*(lam|ellam|all)?\s*"
        r"(koduthen|solren|sonnein|share\s*panninen|kuduthen|seithen|ketkiren)\b"
        r"|\b(naan|naa)\s+(enna|yenna)\s+(details?|thakaval|visarangal)\s*(koduthen|solren|seithen)\b"
        r"|\b(enna|yenna)\s+(details?|info)\s+(irukku|iruku|irukkira)\b",
        re.IGNORECASE
    )
    if _show_profile.search(question):
        return _display_user_profile(user_id, flow, account_email, session_id)
    
    # ── Handle direct questions about saved information ──────────
    # e.g., "what is my name", "what is my mother name", "what are the personal details i gave you"
    _direct_info_query = re.compile(
        # English: "what is my ...", "what are my ...", "tell me my ...", "show me my ..."
        r"\b(what|whats|tell\s+me|show\s+me|display)\s+(is|are|'?s)?\s*(my|the)\s+"
        r"(name|full\s+name|mother|grandfather|email|salary|income|personal\s+details?|details?\s+i\s+gave)"
        # Loose: "personal details i gave", "details you have", "what details do you have on me"
        r"|\b(personal\s+details?|details?\s+(i\s+gave|you\s+have|you\s+stored|you\s+know))"
        r"|\b(what\s+details?|which\s+details?)\s+(do\s+you\s+have|did\s+i\s+give|have\s+you\s+(got|collected|stored))",
        re.IGNORECASE
    )
    if _direct_info_query.search(question):
        from agent.user_profile import get_user_profile
        profile = get_user_profile(user_id) if user_id and user_id != "anonymous" else None

        lower_q = question.lower()

        # ── "what are the personal details i gave you" → show full profile ──
        if re.search(r"personal\s+details?|details?\s+i\s+gave|details?\s+(you\s+)?(have|stored|know|collected)", lower_q, re.IGNORECASE):
            return _display_user_profile(user_id, flow, account_email, session_id)

        # ── specific field queries ───────────────────────────────────────────
        def _ta(en, ta, hi=""):
            if language == "ta": return ta
            if language == "hi" and hi: return hi
            return en

        if re.search(r"\bgrandfather\b", lower_q):
            grandfather_name = flow.state.get("grandfather_name") or (profile.get("grandfather_name") if profile else None)
            if grandfather_name:
                return {
                    "answer": _ta(f"Your grandfather's name is **{grandfather_name}**.",
                                  f"உங்கள் தாத்தாவின் பெயர் **{grandfather_name}**.",
                                  f"आपके दादा का नाम **{grandfather_name}** है।"),
                    "sources": [], "followups": ["Show me what you know about me", "Apply for new PAN"], "guided": False,
                }
            else:
                return {
                    "answer": _ta("I don't have your grandfather's name on record yet. Would you like to provide it?",
                                  "தாத்தாவின் பெயர் இன்னும் பதிவில்லை. வழங்க விரும்புகிறீர்களா?",
                                  "दादा का नाम अभी रिकॉर्ड में नहीं है। क्या आप देना चाहते हैं?"),
                    "sources": [], "followups": ["Show me what you know about me", "Continue with PAN application"], "guided": False,
                }

        if re.search(r"\bmother\b", lower_q):
            mother_name = flow.state.get("mother_name") or (profile.get("mother_name") if profile else None)
            if not mother_name and user_context:
                match = re.search(r"-\s*Mother'?s?\s+[Nn]ame:\s*(.+)", user_context, re.IGNORECASE)
                if match:
                    mother_name = match.group(1).strip()
            if mother_name:
                return {
                    "answer": _ta(f"Your mother's name is **{mother_name}**.",
                                  f"உங்கள் தாயின் பெயர் **{mother_name}**.",
                                  f"आपकी माँ का नाम **{mother_name}** है।"),
                    "sources": [], "followups": ["Show me what you know about me", "Apply for new PAN"], "guided": False,
                }
            else:
                return {
                    "answer": _ta("I don't have your mother's name on record yet. Would you like to provide it?",
                                  "தாயின் பெயர் இன்னும் பதிவில்லை. வழங்க விரும்புகிறீர்களா?",
                                  "माँ का नाम अभी रिकॉर्ड में नहीं है। क्या आप देना चाहते हैं?"),
                    "sources": [], "followups": ["Show me what you know about me", "Continue with PAN application"], "guided": False,
                }

        if re.search(r"\bemail\b", lower_q):
            email = flow.state.get("email") or (profile.get("email") if profile else None) or account_email
            if not email and user_context:
                match = re.search(r"-\s*Email:\s*(.+)", user_context, re.IGNORECASE)
                if match:
                    email = match.group(1).strip()
            if email:
                return {
                    "answer": _ta(f"Your email is **{email}**.",
                                  f"உங்கள் மின்னஞ்சல்: **{email}**.",
                                  f"आपका ईमेल **{email}** है।"),
                    "sources": [], "followups": ["Show me what you know about me", "Apply for new PAN"], "guided": False,
                }

        if re.search(r"\b(salary|income)\b", lower_q):
            salary = flow.state.get("salary") or (profile.get("annual_income") if profile else None)
            if not salary and user_context:
                match = re.search(r"-\s*Annual\s+income:\s*(.+)", user_context, re.IGNORECASE)
                if match:
                    salary = match.group(1).strip()
            if salary:
                return {
                    "answer": _ta(f"Your annual income is **{salary}**.",
                                  f"உங்கள் ஆண்டு வருமானம்: **{salary}**.",
                                  f"आपकी वार्षिक आय **{salary}** है।"),
                    "sources": [], "followups": ["Show me what you know about me", "Apply for new PAN"], "guided": False,
                }

        if re.search(r"\b(name|full\s+name)\b", lower_q) and not re.search(r"\bmother\b|\bgrandfather\b", lower_q):
            full_name = flow.state.get("full_name") or (profile.get("full_name") if profile else None)
            if not full_name and user_context:
                match = re.search(r"-\s*(?:Full\s+)?[Nn]ame:\s*(.+)", user_context, re.IGNORECASE)
                if match:
                    full_name = match.group(1).strip()
                    # Save it to flow state and profile if not already there
                    if not flow.state.get("full_name"):
                        flow.state["full_name"] = full_name
                        flow.save()
                        if user_id and user_id != "anonymous":
                            from agent.user_profile import save_user_profile
                            save_user_profile(user_id, {"full_name": full_name})
            if full_name:
                return {
                    "answer": _ta(f"Your full name is **{full_name}**.",
                                  f"உங்கள் முழு பெயர்: **{full_name}**.",
                                  f"आपका पूरा नाम **{full_name}** है।"),
                    "sources": [], "followups": ["Show me what you know about me", "Apply for new PAN"], "guided": False,
                }
            else:
                return {
                    "answer": _ta("I don't have your name on record yet. Would you like to provide it?",
                                  "பெயர் இன்னும் பதிவில்லை. வழங்க விரும்புகிறீர்களா?",
                                  "नाम अभी रिकॉर्ड में नहीं है। क्या आप देना चाहते हैं?"),
                    "sources": [], "followups": ["Show me what you know about me", "Continue with PAN application"], "guided": False,
                }

        # Couldn't narrow it down — show the full profile
        return _display_user_profile(user_id, flow, account_email, session_id)

    if flow.has_active_flow():
        # Steps where "no" / "nope" is a valid answer, not a cancellation
        _YES_NO_STEPS = {"aadhaar_photo", "rep_assessee", "confirmation"}
        current_step = flow.get_current_step()

        if _is_cancellation(question) and current_step not in _YES_NO_STEPS:
            flow.state["service_id"] = None
            flow.state["complete"] = True
            flow.save()
            return {
                "answer"    : "No problem! I've stopped the application process. Feel free to ask me anything else about PAN services whenever you're ready.",
                "sources"   : [],
                "followups" : [],
                "guided"    : False,
                "close_form": True,
            }

        if _is_upload_now(question) and not _is_off_topic_during_flow(question):
            # Don't intercept if user is answering a form step — the word "upload"
            # may be part of a choice like "Upload scanned docs & eSign"
            current_step = flow.get_current_step()
            _FORM_STEPS = {"submission_mode", "delivery_mode", "aadhaar_photo",
                           "source_of_income", "address_for_comm", "residential_status",
                           "rep_assessee", "details_collection", "confirmation"}
            if current_step not in _FORM_STEPS:
                service = get_service(flow.state.get("service_id", ""))
                if service.get("documents"):
                    return {
                        "answer"     : "Sure! Use the 📎 paperclip button to attach your files — I'll extract everything.",
                        "sources"    : [],
                        "followups"  : [],
                        "guided"     : True,
                        "open_upload": False,
                    }

        if _is_off_topic_during_flow(question):
            return None

        return _continue_flow(flow, question, language, user_id)

    service_id = detect_service(question)
    if service_id:
        # ── Prefill from profile and smart-start the flow ──────────────────
        if user_id and service_id == "pan_apply_indian":
            # Start the flow first (sets service_id, current_step, etc.)
            flow.start_flow(service_id)
            
            # ALWAYS load profile and prefill when starting PAN application
            # (even if _profile_loaded is True from a previous casual chat)
            print(f"[DEBUG] ========== STARTING PAN APPLICATION ==========")
            print(f"[DEBUG] User ID: {user_id}")
            print(f"[DEBUG] Session ID: {session_id}")
            print(f"[DEBUG] Flow state BEFORE prefill: {list(flow.state.keys())}")
            print(f"[DEBUG] applicant_type BEFORE: {flow.state.get('applicant_type')}")
            print(f"[DEBUG] submission_mode BEFORE: {flow.state.get('submission_mode')}")
            print(f"[DEBUG] full_name BEFORE: {flow.state.get('full_name')}")
            
            print(f"[DEBUG] Loading profile for user {user_id}")
            flow.state = prefill_flow_from_profile(user_id, flow.state)
            print(f"[DEBUG] After prefill_flow_from_profile:")
            print(f"[DEBUG]   applicant_type: {flow.state.get('applicant_type')}")
            print(f"[DEBUG]   submission_mode: {flow.state.get('submission_mode')}")
            print(f"[DEBUG]   full_name: {flow.state.get('full_name')}")
            print(f"[DEBUG]   mother_name: {flow.state.get('mother_name')}")
            print(f"[DEBUG]   salary: {flow.state.get('salary')}")
            
            flow.state["_profile_loaded"] = True

            # Also parse user_context (Node sends this every request — more up-to-date)
            if user_context:
                print(f"[DEBUG] Prefilling from user_context...")
                print(f"[DEBUG] user_context preview: {user_context[:300]}...")
                _prefill_from_user_context(flow, user_context)
                print(f"[DEBUG] After _prefill_from_user_context:")
                print(f"[DEBUG]   applicant_type: {flow.state.get('applicant_type')}")
                print(f"[DEBUG]   submission_mode: {flow.state.get('submission_mode')}")
                print(f"[DEBUG]   full_name: {flow.state.get('full_name')}")
                print(f"[DEBUG]   mother_name: {flow.state.get('mother_name')}")
                print(f"[DEBUG]   salary: {flow.state.get('salary')}")

            # Save the state after prefilling
            flow.save()
            print(f"[DEBUG] Flow state saved")

            # Fast-forward past all steps that are already answered
            print(f"[DEBUG] Calling _smart_advance_to_first_missing...")
            result = _smart_advance_to_first_missing(flow, language, user_id)
            if result:
                print(f"[DEBUG] _smart_advance_to_first_missing returned a question")
                print(f"[DEBUG] Current step: {flow.get_current_step()}")
                print(f"[DEBUG] ========== END PAN APPLICATION START ==========")
                return result
            # All steps answered — go straight to confirmation
            print(f"[DEBUG] All steps answered, going to confirmation")
            print(f"[DEBUG] ========== END PAN APPLICATION START ==========")
            return _build_confirmation(flow)

        flow.start_flow(service_id)
        return _start_flow_response(flow, language)

    return None


def _prefill_from_user_context(flow: FlowManager, user_context: str):
    """
    Parse the =VERIFIED USER FACTS= block Node sends in user_context and
    prefill flow state fields that are still empty.
    This is the most up-to-date source — Node builds it from Supabase + Redis.
    """
    if not user_context:
        return

    import re as _re

    # Map context keys → flow state keys
    _FIELD_PATTERNS = {
        "full_name":         _re.compile(r"-\s*(?:Full\s+)?[Nn]ame:\s*(.+)", _re.IGNORECASE),
        "mother_name":       _re.compile(r"-\s*Mother'?s?\s+[Nn]ame:\s*(.+)", _re.IGNORECASE),
        "email":             _re.compile(r"-\s*Email:\s*(.+)", _re.IGNORECASE),
        "salary":            _re.compile(r"-\s*Annual\s+income:\s*(.+)", _re.IGNORECASE),
        "submission_mode":   _re.compile(r"-\s*Submission\s+mode:\s*(.+)", _re.IGNORECASE),
        "delivery_mode":     _re.compile(r"-\s*PAN\s+delivery:\s*(.+)", _re.IGNORECASE),
        "source_of_income":  _re.compile(r"-\s*Source\s+of\s+income:\s*(.+)", _re.IGNORECASE),
        "address_for_comm":  _re.compile(r"-\s*Address\s+for\s+communication:\s*(.+)", _re.IGNORECASE),
        "residential_status":_re.compile(r"-\s*Residential\s+status:\s*(.+)", _re.IGNORECASE),
        "applicant_type":    _re.compile(r"-\s*Applicant\s+type:\s*(.+)", _re.IGNORECASE),
    }

    # Boolean fields stored as "Yes"/"No" text
    _BOOL_PATTERNS = {
        "aadhaar_photo":  _re.compile(r"-\s*Aadhaar\s+[Pp]hoto\s+on\s+PAN:\s*(.+)", _re.IGNORECASE),
        "rep_assessee":   _re.compile(r"-\s*Representative\s+Assessee:\s*(.+)", _re.IGNORECASE),
    }

    for field, pat in _FIELD_PATTERNS.items():
        if flow.state.get(field):
            continue   # already set — don't overwrite
        m = pat.search(user_context)
        if m:
            val = m.group(1).strip()
            if val and val != "—":
                flow.state[field] = val

    for field, pat in _BOOL_PATTERNS.items():
        if flow.state.get(field) is not None:
            continue   # already set (False is valid)
        m = pat.search(user_context)
        if m:
            val = m.group(1).strip().lower()
            if val in ("yes", "true", "1"):
                flow.state[field] = True
            elif val in ("no", "false", "0"):
                flow.state[field] = False

    # Normalise delivery_mode to internal codes
    dm = flow.state.get("delivery_mode", "")
    if dm and "physical" in dm.lower():
        flow.state["delivery_mode"] = "physical_and_soft"
    elif dm and ("soft" in dm.lower() or "e-pan" in dm.lower() or "epan" in dm.lower()):
        flow.state["delivery_mode"] = "soft_only"

    # Normalise applicant_type to internal codes
    at = flow.state.get("applicant_type", "")
    if at:
        at_lower = at.lower()
        if "indian" in at_lower and ("citizen" in at_lower or "individual" in at_lower):
            flow.state["applicant_type"] = "indian_citizen"
        elif "company" in at_lower or "huf" in at_lower or "firm" in at_lower:
            flow.state["applicant_type"] = "indian_entity"
        elif "foreign" in at_lower or "nri" in at_lower or "overseas" in at_lower:
            flow.state["applicant_type"] = "foreign"


def _smart_advance_to_first_missing(flow: FlowManager, language: str, user_id: str = None) -> dict | None:
    """
    After prefilling from profile, fast-forward the flow past all steps
    that already have answers. Returns the first question that still needs
    an answer, or None if everything is already filled (go to confirmation).

    Step → field mapping for pan_apply_indian:
      applicant_type   → flow.state["applicant_type"]
      submission_mode  → flow.state["submission_mode"]
      delivery_mode    → flow.state["delivery_mode"]
      aadhaar_photo    → flow.state["aadhaar_photo"]   (bool, so check is not None)
      source_of_income → flow.state["source_of_income"]
      address_for_comm → flow.state["address_for_comm"]
      residential_status → flow.state["residential_status"]
      rep_assessee     → flow.state["rep_assessee"]    (bool, so check is not None)
      details_collection → full_name + mother_name + email + salary
      confirmation     → always ask (user must confirm)
    """
    from agent.service_flows import get_service

    service = get_service(flow.state["service_id"])
    steps = service["steps"]
    
    print(f"[DEBUG] _smart_advance_to_first_missing: Checking {len(steps)} steps")

    def _step_answered(step: str) -> bool:
        s = flow.state
        if step == "applicant_type":
            answered = bool(s.get("applicant_type"))
            print(f"[DEBUG]   applicant_type: {s.get('applicant_type')} -> answered={answered}")
            return answered
        if step == "submission_mode":
            answered = bool(s.get("submission_mode"))
            print(f"[DEBUG]   submission_mode: {s.get('submission_mode')} -> answered={answered}")
            return answered
        if step == "delivery_mode":
            answered = bool(s.get("delivery_mode"))
            print(f"[DEBUG]   delivery_mode: {s.get('delivery_mode')} -> answered={answered}")
            return answered
        if step == "aadhaar_photo":
            answered = s.get("aadhaar_photo") is not None
            print(f"[DEBUG]   aadhaar_photo: {s.get('aadhaar_photo')} -> answered={answered}")
            return answered
        if step == "source_of_income":
            answered = bool(s.get("source_of_income"))
            print(f"[DEBUG]   source_of_income: {s.get('source_of_income')} -> answered={answered}")
            return answered
        if step == "address_for_comm":
            answered = bool(s.get("address_for_comm"))
            print(f"[DEBUG]   address_for_comm: {s.get('address_for_comm')} -> answered={answered}")
            return answered
        if step == "residential_status":
            answered = bool(s.get("residential_status"))
            print(f"[DEBUG]   residential_status: {s.get('residential_status')} -> answered={answered}")
            return answered
        if step == "rep_assessee":
            answered = s.get("rep_assessee") is not None
            print(f"[DEBUG]   rep_assessee: {s.get('rep_assessee')} -> answered={answered}")
            return answered
        if step == "details_collection":
            missing = _missing_details(flow)
            answered = len(missing) == 0
            print(f"[DEBUG]   details_collection: missing={missing} -> answered={answered}")
            return answered
        # confirmation, documents, summary — never skip
        print(f"[DEBUG]   {step}: never skip")
        return False

    # Walk through steps and skip answered ones
    for step in steps:
        print(f"[DEBUG] Checking step: {step}")
        if step in ("confirmation", "documents", "summary"):
            # Always stop here — user must confirm/upload
            flow.state["current_step"] = step
            flow.save()
            print(f"[DEBUG] Stopping at {step} (always ask)")
            if step == "confirmation":
                return _build_confirmation(flow)
            return _ask_step(flow)

        if not _step_answered(step):
            # This step needs an answer — set it as current and ask
            flow.state["current_step"] = step
            flow.save()
            print(f"[DEBUG] First missing step: {step}")
            return _ask_step(flow)
        else:
            print(f"[DEBUG] Step {step} already answered, skipping")

    # All steps answered — go to confirmation
    flow.state["current_step"] = "confirmation"
    flow.save()
    print(f"[DEBUG] All steps answered, returning None (caller will show confirmation)")
    return None   # caller will call _build_confirmation


def _start_flow_response(flow: FlowManager, language: str) -> dict:
    step = flow.get_current_step()
    service = get_service(flow.state["service_id"])
    name = service["name"]
    ta = language == "ta"
    hi = language == "hi"

    if step == "applicant_type":
        opts = {
            "type": "radio", "label": "Applicant type", "field": "applicant_type",
            "choices": ["Indian Citizen", "Indian Company / HUF / Firm", "Foreign Citizen / NRI / Overseas"],
        }
        if ta:
            answer = f"**{name}** தொடங்குவோம்.\n\nநீங்கள் யார்?"
        elif hi:
            answer = f"**{name}** शुरू करते हैं।\n\nआप कौन हैं?"
        else:
            answer = f"Let's get your **{name}** sorted.\n\nWhich of these fits you?"
        return {
            "answer"  : answer,
            "sources" : [], "followups": [], "guided": True, "step": step, "options": opts,
        }

    return _ask_step(flow, language)


def _ask_next_pending_question(flow: FlowManager) -> dict:
    """
    Ask the next question from the _questions_to_ask list.
    This is used when user wants to change specific questions after bulk review.
    """
    questions_to_ask = flow.state.get("_questions_to_ask", [])
    if not questions_to_ask:
        # No more questions, go to details_collection
        flow.state["current_step"] = "details_collection"
        flow.save()
        _lang = flow.state.get("_current_language", "en")
        _details = _ask_details_collection(flow)
        _intro = ("சரி! இப்போது உங்கள் விவரங்களை சேகரிக்கலாம்.\n\n" if _lang == "ta"
                  else "ठीक है! अब आपके विवरण एकत्र करते हैं।\n\n" if _lang == "hi"
                  else "Great! Now let's collect your details.\n\n")
        return {
            "answer": _intro + _details["answer"],
            "sources": [], "followups": [], "guided": True, "step": "details_collection",
        }
    
    # Get the next question to ask
    next_question = questions_to_ask[0]
    
    # Set current step to this question
    flow.state["current_step"] = next_question
    flow.save()
    
    # Return the question prompt
    return _ask_step(flow)


def _advance_after_answer(flow: FlowManager, user_id: str = None) -> dict:
    """
    Helper to advance to next question after user answers.
    Handles both normal flow and selective question mode (after bulk review).
    Auto-saves preferences to profile.
    """
    # Auto-save preferences to profile after each answer
    if user_id:
        try:
            save_flow_to_profile(user_id, flow.state)
            print(f"[DEBUG] Auto-saved preferences to profile for user {user_id}")
        except Exception as e:
            print(f"[ERROR] Failed to auto-save preferences: {e}")
    
    # Check if we're in selective question mode (after bulk review)
    if flow.state.get("_questions_to_ask"):
        questions_to_ask = flow.state["_questions_to_ask"]
        if questions_to_ask:
            questions_to_ask.pop(0)  # Remove current question
            flow.state["_questions_to_ask"] = questions_to_ask
            flow.save()
            
            if questions_to_ask:
                return _ask_next_pending_question(flow)
            else:
                # All questions answered, move to details_collection
                flow.state["current_step"] = "details_collection"
                flow.save()
                return {
                    "answer": "Great! Now let's collect your details.\n\n" + _ask_details_collection(flow)["answer"],
                    "sources": [],
                    "followups": [],
                    "guided": True,
                    "step": "details_collection",
                }
    else:
        # Normal flow
        flow.advance_step()
        flow.save()
        return _ask_step(flow)


def _ask_step(flow: FlowManager, language: str = 'en') -> dict:
    """Return the question + options for the current step."""
    step = flow.get_current_step()
    ta = language == "ta"
    hi = language == "hi"

    # ── applicant_type ────────────────────────────────────────────
    if step == "applicant_type":
        opts = {
            "type": "radio", "label": "Applicant type", "field": "applicant_type",
            "choices": ["Indian Citizen", "Indian Company / HUF / Firm", "Foreign Citizen / NRI / Overseas"],
        }
        service = get_service(flow.state.get("service_id", ""))
        name = service.get("name", "PAN Application")
        if ta:
            answer = f"**{name}** தொடங்குவோம்.\n\nநீங்கள் யார்?"
        elif hi:
            answer = f"**{name}** शुरू करते हैं।\n\nआप कौन हैं?"
        else:
            answer = f"Let's get your **{name}** sorted.\n\nWhich of these fits you?"
        return {
            "answer": answer,
            "sources": [], "followups": [], "guided": True, "step": step, "options": opts,
        }

    # ── NEW: Check if we should show bulk review of all saved optional answers ──────
    # Only show this ONCE when entering the optional questions section (submission_mode is first)
    if step == "submission_mode" and not flow.state.get("_reviewed_saved_answers"):
        # Collect all saved answers for optional questions
        saved_answers = {}
        optional_questions = ["submission_mode", "delivery_mode", "aadhaar_photo", 
                             "source_of_income", "address_for_comm", "residential_status", "rep_assessee"]
        
        for q in optional_questions:
            saved_val = flow.state.get(f"_saved_{q}")
            if saved_val is not None:
                saved_answers[q] = saved_val
        
        # If user has 2+ saved answers, show bulk review prompt
        if len(saved_answers) >= 2:
            flow.state["_pending_bulk_review"] = True
            flow.state["_bulk_saved_answers"] = saved_answers
            flow.state["_reviewed_saved_answers"] = True  # Mark as reviewed so we don't ask again
            flow.save()
            
            return {
                "answer": _build_individual_preferences_review_prompt(saved_answers),
                "sources": [],
                "followups": ["All same", "All new", "Change some"],
                "guided": True,
                "step": "bulk_review_check",
            }
        else:
            # Not enough saved answers, proceed normally
            flow.state["_reviewed_saved_answers"] = True
            flow.save()

    if step == "submission_mode":
        opts = {
            "type": "radio", "label": "Submission mode", "field": "submission_mode",
            "choices": [
                "Aadhaar-based Online (eKYC)",
                "Upload scanned docs & eSign",
                "Fill online + courier physical form",
            ],
            "descriptions": [
                "Uses your Aadhaar details for eKYC — Name, Photo, DOB, Gender & Address.",
                "Upload scanned Photo, Signature and supporting documents, then eSign.",
                "Fill the form online, print, sign and courier/speed-post to Protean's Pune office.",
            ],
        }
        return {"answer": "**How do you want to submit your PAN application documents?**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    elif step == "delivery_mode":
        opts = {
            "type": "radio", "label": "PAN delivery", "field": "delivery_mode",
            "choices": [
                "Physical copy to home + soft copy on email (Fees applicable)",
                "Only soft copy on email (Fees applicable)",
            ],
        }
        return {"answer": "**How do you want your PAN card to be delivered?**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    elif step == "aadhaar_photo":
        opts = {
            "type": "radio", "label": "Aadhaar photo consent", "field": "aadhaar_photo",
            "choices": ["Yes", "No"],
        }
        return {
            "answer": "**I hereby agree to have my Aadhaar photo printed on my PAN Card.**\n\n> Note: If you do not wish to use your Aadhaar photo, you may apply for a PAN with a separate photograph.",
            "sources": [], "followups": [], "guided": True, "step": step, "options": opts,
        }

    elif step == "source_of_income":
        opts = {
            "type": "radio", "label": "Source of Income", "field": "source_of_income",
            "choices": ["Salary", "Income from Business / Profession", "Income from House property",
                        "Income from Other sources", "Capital Gains", "No income"],
        }
        return {"answer": "**Please select your Source of Income:**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    elif step == "address_for_comm":
        opts = {
            "type": "radio", "label": "Address for Communication", "field": "address_for_comm",
            "choices": ["Residence", "Office", "Representative Assessee (RA)"],
            "hint": "**Important instructions for paperless PAN application through e-KYC (Only For Individual):**\n1. The address used in Aadhaar card would be used in PAN application as residence address — no need to fill residential address separately.\n2. PAN card will be dispatched at address mentioned in Aadhaar.\n3. If length of address as per Aadhaar database exceeds the length specified by Income Tax Department, you will not be able to avail e-KYC service.",
        }
        return {"answer": "**Address for Communication** — Please tick as applicable:", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    elif step == "residential_status":
        opts = {
            "type": "radio", "label": "Residential Status", "field": "residential_status",
            "choices": ["Resident", "Non-resident", "Resident but not ordinarily resident"],
        }
        return {"answer": "**What is your Residential Status?**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    elif step == "rep_assessee":
        opts = {
            "type": "radio", "label": "Representative Assessee", "field": "rep_assessee",
            "choices": ["Yes", "No"],
        }
        return {
            "answer": "**Appointing Representative Assessee?**\n\n> A Representative Assessee is someone who manages tax obligations on behalf of another person (e.g. a guardian for a minor, or a legal heir for a deceased person). Select **Yes** only if you are applying on behalf of someone else.",
            "sources": [], "followups": [], "guided": True, "step": step, "options": opts,
        }

    elif step == "details_collection":
        return _ask_details_collection(flow)

    elif step == "confirmation":
        return _build_confirmation(flow)

    elif step == "documents":
        return {"answer": _ask_for_documents(flow), "sources": [], "followups": [], "guided": True, "step": step}

    elif step == "pan_number":
        _lang = flow.state.get("_current_language", "en")
        _msg = ("உங்கள் **PAN எண்** (10 எழுத்துகள், எ.கா. **ABCDE1234F**) முதலில் தேவை." if _lang == "ta"
                else "आपका **PAN नंबर** (10 अक्षर, जैसे **ABCDE1234F**) पहले चाहिए।" if _lang == "hi"
                else "I'll need your existing **PAN number** first (10-character code, e.g. **ABCDE1234F**).")
        return {"answer": _msg, "sources": [], "followups": [], "guided": True, "step": step}

    elif step == "aadhaar_number":
        _lang = flow.state.get("_current_language", "en")
        _msg = ("இப்போது உங்கள் **ஆதார் எண்** (12 இலக்கங்கள்) தேவை." if _lang == "ta"
                else "अब आपका **आधार नंबर** (12 अंक) चाहिए।" if _lang == "hi"
                else "Now I need your **Aadhaar number** (12 digits).")
        return {"answer": _msg, "sources": [], "followups": [], "guided": True, "step": step}

    _lang = flow.state.get("_current_language", "en")
    _msg = ("தொடர்வோம் — அடுத்த விவரத்தை வழங்கவும்." if _lang == "ta"
            else "जारी रखते हैं — अगली जानकारी दें।" if _lang == "hi"
            else "Let's continue — please provide the next detail.")
    return {"answer": _msg, "sources": [], "followups": [], "guided": True, "step": step}


def _continue_flow(flow: FlowManager, user_input: str, language: str, user_id: str = None) -> dict:
    step = flow.get_current_step()
    inp  = user_input.strip()
    
    # ── TANGLISH DETECTION & CONVERSION ───────────────────────────────────────
    # If Tamil mode, check for Tanglish (Tamil written in English) and convert
    if language == "ta":
        from agent.transliterator import normalize_for_field_detection
        inp = normalize_for_field_detection(inp, language)
        print(f"[DEBUG] After Tanglish normalization: {inp}")

    # ── INLINE FIELD UPDATE INTERCEPT (any step) ──────────────────────────────
    # Catches messages from the confirmation-panel's inline edit buttons, e.g.
    #   "change Source of Income to Capital Gains, Income from Business / Profession"
    #   "change Aadhaar Photo on PAN to Yes"
    #   "change Annual Income to 50000"
    # Also handles batched save-all messages joined by " | ", e.g.
    #   "change Source of Income to Salary | change Aadhaar Photo on PAN to No | ..."
    # These always use the exact English field label sent by FieldEditor in App.jsx.
    # We intercept before step-specific logic so the current step doesn't interfere.
    _INLINE_EDIT_RE = re.compile(
        r"^change\s+(Source of Income|Submission Mode|PAN Delivery|Aadhaar Photo on PAN"
        r"|Address for Communication|Residential Status|Representative Assessee"
        r"|Full Name \(as in Aadhaar\)|Full Name|Grandfather'?s Name|Mother'?s Name|Annual Income|Email)\s+to\s+(.+)$",
        re.IGNORECASE,
    )
    _LABEL_TO_KEY = {
        "source of income":          "source_of_income",
        "submission mode":           "submission_mode",
        "pan delivery":              "delivery_mode",
        "aadhaar photo on pan":      "aadhaar_photo",
        "address for communication": "address_for_comm",
        "residential status":        "residential_status",
        "representative assessee":   "rep_assessee",
        "full name (as in aadhaar)": "full_name",
        "full name":                 "full_name",
        "grandfather's name":        "grandfather_name",
        "grandfather name":          "grandfather_name",
        "mother's name":             "mother_name",
        "mother name":               "mother_name",
        "annual income":             "salary",
        "email":                     "email",
    }

    # Check if this is a batched save-all message ("change X to Y | change A to B | ...")
    _parts = [p.strip() for p in inp.split(" | ") if p.strip()]
    _all_inline = _parts and all(_INLINE_EDIT_RE.match(p) for p in _parts)

    # Also handle single inline edit
    _single_inline = not _all_inline and _INLINE_EDIT_RE.match(inp)

    if _all_inline or _single_inline:
        items = _parts if _all_inline else [inp]
        any_updated = False
        for item in items:
            m = _INLINE_EDIT_RE.match(item)
            if not m:
                continue
            _field_label = m.group(1).strip()
            _field_value = m.group(2).strip()
            _field_key = _LABEL_TO_KEY.get(_field_label.lower())
            if _field_key:
                print(f"[DEBUG] Inline edit intercept: {_field_key} = {_field_value!r}")
                _apply_field_update(flow, _field_key, _field_value, _field_value)
                any_updated = True

        if any_updated:
            flow.state["pending_modification"] = None
            # Do NOT mark details_confirmed yet — user must still click "Confirm" in the UI.
            # Always return to the confirmation panel so the user can review the updated values
            # and either keep editing (Save Changes) or proceed (Confirm → documents).
            flow.save()
            try:
                if user_id:
                    save_flow_to_profile(user_id, flow.state)
            except Exception:
                pass
            confirmation = _build_confirmation(flow)
            current_language = flow.state.get("_current_language", language)
            # Prepend a short acknowledgement in the right language
            if current_language == "ta":
                ack = "✓ விவரங்கள் புதுப்பிக்கப்பட்டன. மீண்டும் சரிபார்த்து உறுதிப்படுத்தவும்.\n\n"
            elif current_language == "hi":
                ack = "✓ विवरण अपडेट किए गए। कृपया समीक्षा करें और पुष्टि करें।\n\n"
            else:
                ack = "✓ Details updated. Review below and confirm when ready.\n\n"
            confirmation["answer"] = ack + confirmation["answer"]
            return confirmation

    # ── GLOBAL MID-FLOW UPDATE INTERCEPT ──────────────────────────────────────
    # Handles field update requests at any collection step, with a sequential queue.
    # "update address for communication and pan delivery"
    #   → shows address options → user picks → shows pan delivery options → user picks → resumes
    _COLLECTION_STEPS = {
        "submission_mode", "delivery_mode", "aadhaar_photo", "source_of_income",
        "address_for_comm", "residential_status", "rep_assessee",
        "details_collection", "documents", "confirmation",
    }

    def _field_is_set(field: str) -> bool:
        v = flow.state.get(field)
        return v is not None

    # Field keyword patterns for detecting mentioned-but-no-value fields
    # English + Tamil patterns
    _FIELD_KEYWORDS = {
        "full_name":          r"\b(full\s+name|my\s+name|name\s+on\s+aadhaar|^name$|பெயர்|முழு\s*பெயர்|என்\s*பெயர்)\b",
        "mother_name":        r"\b(mother|mom|mum|தாய்|அம்மா|தாயின்\s*பெயர்)\b",
        "email":              r"\b(email|mail|gmail|மின்னஞ்சல்|மெயில்)\b",
        "salary":             r"\b(salary|annual\s+income|சம்பளம்|வருமானம்|ஆண்டு\s*வருமானம்)\b",
        "submission_mode":    r"\b(submission\s+mode|submit\s+mode|சமர்ப்பிப்பு\s*முறை|சமர்ப்பிக்கும்\s*முறை)\b",
        "delivery_mode":      r"\b(pan\s+delivery|delivery\s+mode|card\s+delivery|விநியோக\s*முறை|பான்\s*விநியோகம்)\b",
        "aadhaar_photo":      r"\b(aadhaar\s+photo|photo\s+on\s+pan|ஆதார்\s*புகைப்படம்|புகைப்படம்)\b",
        "source_of_income":   r"\b(source\s+of\s+income|income\s+source|வருமான\s*ஆதாரம்|வருமானம்\s*வகை)\b",
        "address_for_comm":   r"\b(address\s+for\s+comm(unication)?|communication\s+address|தொடர்பு\s*முகவரி|முகவரி)\b",
        "residential_status": r"\b(residential\s+status|residency|குடியிருப்பு\s*நிலை|வசிப்பிட\s*நிலை)\b",
        "rep_assessee":       r"\b(representative\s+assessee|rep\s+assessee|பிரதிநிதி|பிரதிநிதி\s*மதிப்பீட்டாளர்)\b",
    }
    _ALL_TRACKED = list(_FIELD_KEYWORDS.keys())

    def _build_queue_from_message(inp: str, fields_already_updated: set) -> list:
        """Return ordered list of fields mentioned in the message that have no inline value."""
        queue = []
        for f in _ALL_TRACKED:
            if f in fields_already_updated:
                continue
            pat = _FIELD_KEYWORDS.get(f)
            if pat and re.search(pat, inp, re.IGNORECASE) and _field_is_set(f):
                queue.append(f)
        return queue

    # ── Handle active queue — user is answering one field at a time ───────────
    if flow.state.get("_mid_flow_queue"):
        queue = flow.state["_mid_flow_queue"]
        current_field = queue[0]

        # Check for affirmative — skip this field and continue
        _yes_re = re.compile(
            r"^(yes|y|yeah|yep|yup|sure|ok|okay|proceed|skip|continue|next"
            r"|done|all\s+set|good\s+to\s+go|move\s+on).*$",
            re.IGNORECASE
        )
        if _yes_re.match(inp):
            # Pop current field and move to next
            queue.pop(0)
            flow.state["_mid_flow_queue"] = queue
            flow.save()
        else:
            # Apply the user's answer to the current field
            _apply_field_update(flow, current_field, inp, user_input)
            queue.pop(0)
            flow.state["_mid_flow_queue"] = queue
            flow.save()

        # If more fields in queue, ask the next one
        if queue:
            next_field = queue[0]
            field_prompt = _ask_for_field(flow, next_field)
            label = current_field.replace('_', ' ').title()
            _lang = flow.state.get("_current_language", language)
            _ack = (f"✓ **{label}** புதுப்பிக்கப்பட்டது.\n\n" if _lang == "ta"
                    else f"✓ **{label}** अपडेट हो गया।\n\n" if _lang == "hi"
                    else f"✓ **{label}** updated.\n\n")
            field_prompt["answer"] = _ack + field_prompt["answer"]
            return field_prompt

        # Queue exhausted — resume normal flow
        resp = _ask_step(flow)
        if resp:
            _ack = ("✓ அனைத்து புதுப்பிப்புகளும் பயன்படுத்தப்பட்டன. தொடர்கிறோம்.\n\n" if language == "ta"
                    else "✓ सभी अपडेट लागू हो गए। जारी है।\n\n" if language == "hi"
                    else "✓ All updates applied. Continuing from where we left off.\n\n")
            resp["answer"] = _ack + resp["answer"]
        return resp or _build_confirmation(flow)

    # ── New update request — build the queue ─────────────────────────────────
    if step in _COLLECTION_STEPS:
        # English + Tamil change intent patterns
        # Tamil: மாற்று (change), புதுப்பி (update), திருத்து (edit/correct)
        _change_intent = re.search(
            r"\b(change|update|modify|edit|fix|correct|i\s+want\s+to|can\s+i|let\s+me|"
            r"மாற்று|மாற்றவும்|புதுப்பி|புதுப்பிக்க|திருத்து|திருத்தவும்|சரி\s*செய்|"
            r"நான்\s+விரும்புகிறேன்|எனக்கு\s+வேண்டும்)\b",
            inp, re.IGNORECASE
        )

        # ── Case 1: Explicit change intent ────────────────────────────────────
        if _change_intent:
            # Apply all inline value updates (fields with values in the message)
            state_before = {k: flow.state.get(k) for k in _ALL_TRACKED}
            updates_made = _extract_multiple_field_updates(flow, inp, user_input)
            if updates_made:
                flow.save()
            state_after  = {k: flow.state.get(k) for k in _ALL_TRACKED}
            fields_updated = {k for k in _ALL_TRACKED if state_before[k] != state_after[k]}

            # Build queue of fields mentioned but without values
            queue = _build_queue_from_message(inp, fields_updated)

            if queue:
                # Start the queue
                flow.state["_mid_flow_queue"] = queue
                flow.save()
                first_field = queue[0]
                field_prompt = _ask_for_field(flow, first_field)
                if updates_made:
                    resp = _ask_step(flow)
                    base = resp["answer"] if resp else ""
                    prefix = "✓ Updated inline fields. " + (base + "\n\n---\n\n" if base else "")
                    field_prompt["answer"] = prefix + field_prompt["answer"]
                return field_prompt

            # No queued fields — just inline updates, resume
            if updates_made:
                resp = _ask_step(flow)
                if resp:
                    _ack = ("✓ புதுப்பிக்கப்பட்டது. தொடர்கிறோம்.\n\n" if language == "ta"
                            else "✓ अपडेट हो गया। जारी है।\n\n" if language == "hi"
                            else "✓ Updated. Continuing from where we left off.\n\n")
                    resp["answer"] = _ack + resp["answer"]
                return resp or _build_confirmation(flow)

            # No inline updates either — single field ask
            field = _detect_modification_field(inp)
            if field and _field_is_set(field):
                flow.state["_mid_flow_queue"] = [field]
                flow.save()
                return _ask_for_field(flow, field)

        # ── Case 2: Bare field label ───────────────────────────────────────────
        else:
            # English + Tamil bare labels
            _BARE_LABELS = {
                # English
                "submission mode", "pan delivery", "aadhaar photo on pan",
                "source of income", "address for communication",
                "residential status", "representative assessee",
                "full name", "annual income", "mother name", "mothers name", "email",
                "name", "salary",
                # Tamil
                "சமர்ப்பிப்பு முறை", "பான் விநியோகம்", "ஆதார் புகைப்படம்",
                "வருமான ஆதாரம்", "தொடர்பு முகவரி",
                "குடியிருப்பு நிலை", "பிரதிநிதி மதிப்பீட்டாளர்",
                "முழு பெயர்", "ஆண்டு வருமானம்", "தாயின் பெயர்", "மின்னஞ்சல்",
                "பெயர்", "சம்பளம்",
            }
            bare = inp.strip().lower()
            if bare in _BARE_LABELS:
                field = _detect_modification_field(inp)
                if field and _field_is_set(field):
                    flow.state["_mid_flow_queue"] = [field]
                    flow.save()
                    return _ask_for_field(flow, field)

            # ── Case 3: Inline multi-field with no "change" keyword ───────────
            # English + Tamil inline patterns
            # Tamil patterns: என் பெயர் (my name), பெயர் (name is), etc.
            # Also catches Tanglish: "ennodiya per X", "en per X", "amma per X"
            elif re.search(
                r"\b(my\s+name|name\s+is|name\s+to|salary\s+is|salary\s+to"
                r"|mother\s+name|email\s+is|email\s+to|"
                r"என்\s*பெயர்|பெயர்.*என்று|சம்பளம்.*என்று|தாயின்\s*பெயர்|மின்னஞ்சல்.*என்று|"
                r"(?:ennodiya|ennoda|en|naan|naanu)\s+(?:peyar|per)\b|"
                r"(?:amma|thaayin|thaay)\s+(?:peyar|per)\b)\b",
                inp, re.IGNORECASE
            ):
                updates_made = _extract_multiple_field_updates(flow, inp, user_input)
                if updates_made:
                    flow.save()
                    resp = _ask_step(flow)
                    if resp:
                        _ack = ("✓ புதுப்பிக்கப்பட்டது. தொடர்கிறோம்.\n\n" if language == "ta"
                                else "✓ अपडेट हो गया। जारी है।\n\n" if language == "hi"
                                else "✓ Updated. Continuing from where we left off.\n\n")
                        resp["answer"] = _ack + resp["answer"]
                    return resp or _build_confirmation(flow)

    # ── Universal field-update fallback — any step, any format ───────────────
    # If nothing above matched but _extract_multiple_field_updates finds something,
    # apply it and resume the current step. Catches Tanglish like "ennodiya per X"
    # that slip through the intent/bare-label/inline checks above.
    if step in _COLLECTION_STEPS:
        _fallback_updates = _extract_multiple_field_updates(flow, inp, user_input)
        if _fallback_updates:
            flow.save()
            resp = _ask_step(flow)
            if resp:
                _ack = ("✓ புதுப்பிக்கப்பட்டது. தொடர்கிறோம்.\n\n" if language == "ta"
                        else "✓ अपडेट हो गया। जारी है।\n\n" if language == "hi"
                        else "✓ Updated. Continuing.\n\n")
                resp["answer"] = _ack + resp["answer"]
            return resp or _build_confirmation(flow)

    # ── Legacy single-field handler (backward compat) ─────────────────────────
    if flow.state.get("_mid_flow_pending_field"):
        field = flow.state["_mid_flow_pending_field"]
        _yes_re = re.compile(
            r"^(yes|y|yeah|yep|yup|sure|ok|okay|proceed|skip|continue|next"
            r"|done|all\s+set|good\s+to\s+go|move\s+on).*$", re.IGNORECASE
        )
        if not _yes_re.match(inp):
            _apply_field_update(flow, field, inp, user_input)
        flow.state["_mid_flow_pending_field"] = None
        flow.state["_mid_flow_return_step"] = None
        flow.save()
        resp = _ask_step(flow)
        if resp:
            _lbl = field.replace('_', ' ').title()
            _ack = (f"✓ **{_lbl}** புதுப்பிக்கப்பட்டது. தொடர்கிறோம்.\n\n" if language == "ta"
                    else f"✓ **{_lbl}** अपडेट हो गया। जारी है।\n\n" if language == "hi"
                    else f"✓ **{_lbl}** updated. Continuing.\n\n")
            resp["answer"] = _ack + resp["answer"]
        return resp if resp else _build_confirmation(flow)

    # ── Handle preferences reuse check ────────────────────────────
    if flow.state.get("_pending_preferences_reuse"):
        _yes = re.compile(r"\b(yes|yeah|yep|yup|sure|ok|okay|correct|right|same|use\s+same|continue|proceed)\b", re.IGNORECASE)
        _no  = re.compile(r"\b(no|nope|nah|different|change|new|choose\s+again)\b", re.IGNORECASE)
        
        if _yes.match(inp):
            # User wants to reuse saved preferences
            saved_prefs = flow.state.get("_saved_preferences", {})
            
            # Apply saved preferences to flow state
            for key, value in saved_prefs.items():
                flow.state[key] = value
            
            # Clear the pending flag
            flow.state["_pending_preferences_reuse"] = False
            flow.state["_saved_preferences"] = None
            
            # Start the flow and skip to details_collection
            flow.start_flow(flow.state.get("service_id", "pan_new"))
            
            # Skip all the preference questions and go straight to details collection
            flow.state["current_step"] = "details_collection"
            flow.save()
            
            return {
                "answer": "Great! I'll use your previous choices. Now let's collect your details.\n\n" + _ask_details_collection(flow)["answer"],
                "sources": [],
                "followups": [],
                "guided": True,
                "step": "details_collection",
            }
        
        elif _no.match(inp):
            # User wants to choose new preferences
            flow.state["_pending_preferences_reuse"] = False
            flow.state["_saved_preferences"] = None
            
            # Start the flow normally
            flow.start_flow(flow.state.get("service_id", "pan_new"))
            flow.save()
            
            return _start_flow_response(flow, language)
        
        else:
            # User didn't give a clear yes/no, ask again
            return {
                "answer": "I didn't quite catch that. Would you like to use the same options as your previous application?\n\nReply **Yes** to use the same options, or **No** to choose different options.",
                "sources": [],
                "followups": ["Yes, use same options", "No, I'll choose again"],
                "guided": True,
                "step": "preferences_reuse_check",
            }
    
    # ── Handle bulk review of saved optional answers ────────────────────────────
    if flow.state.get("_pending_bulk_review"):
        saved_answers = flow.state.get("_bulk_saved_answers", {})
        
        # Parse user response
        _all_same = re.compile(r"\b(all\s+same|use\s+all|keep\s+all|same|yes|all)\b", re.IGNORECASE)
        _all_new = re.compile(r"\b(all\s+new|new|start\s+over|choose\s+again|no)\b", re.IGNORECASE)
        _change_some = re.compile(r"\b(change|modify|update)\b", re.IGNORECASE)
        
        if _all_same.match(inp):
            # User wants to use ALL saved answers
            for key, value in saved_answers.items():
                flow.state[key] = value
            
            flow.state["_pending_bulk_review"] = False
            flow.state["_bulk_saved_answers"] = None
            
            # Skip all optional questions and go to details_collection
            flow.state["current_step"] = "details_collection"
            flow.save()
            
            return {
                "answer": "Perfect! I'll use all your previous answers. Now let's collect your details.\n\n" + _ask_details_collection(flow)["answer"],
                "sources": [],
                "followups": [],
                "guided": True,
                "step": "details_collection",
            }
        
        elif _all_new.match(inp):
            # User wants to answer ALL questions again
            flow.state["_pending_bulk_review"] = False
            flow.state["_bulk_saved_answers"] = None
            flow.save()
            
            return _ask_step(flow)
        
        elif _change_some.search(inp):
            # User wants to change specific questions
            # Extract numbers from input (e.g., "change 1 and 3" or "change 2,5,7")
            numbers = re.findall(r'\b([1-7])\b', inp)
            
            if numbers:
                # Map numbers to question keys
                question_map = {
                    "1": "submission_mode",
                    "2": "delivery_mode",
                    "3": "aadhaar_photo",
                    "4": "source_of_income",
                    "5": "address_for_comm",
                    "6": "residential_status",
                    "7": "rep_assessee",
                }
                
                # Mark which questions to skip (keep saved answer)
                questions_to_change = set()
                for num in numbers:
                    q_key = question_map.get(num)
                    if q_key:
                        questions_to_change.add(q_key)
                
                # Apply saved answers for questions NOT being changed
                for key, value in saved_answers.items():
                    if key not in questions_to_change:
                        flow.state[key] = value
                
                # Mark which questions need to be asked
                flow.state["_questions_to_ask"] = list(questions_to_change)
                flow.state["_pending_bulk_review"] = False
                flow.state["_bulk_saved_answers"] = None
                flow.save()
                
                # Start asking the questions that need to be changed
                return _ask_next_pending_question(flow)
            else:
                # No numbers found, ask for clarification
                return {
                    "answer": "Please specify which questions you'd like to change by number.\n\nFor example:\n• \"Change 1 and 3\"\n• \"Change 2,5,7\"\n• Or reply **All same** to keep everything, or **All new** to answer all again.",
                    "sources": [],
                    "followups": ["All same", "All new", "Change 1 and 3"],
                    "guided": True,
                    "step": "bulk_review_check",
                }
        else:
            # Unclear response, ask again
            return {
                "answer": "I didn't quite catch that. Would you like to:\n\n• **All same** - Use all previous answers\n• **Change [numbers]** - Modify specific answers (e.g., \"Change 1 and 3\")\n• **All new** - Answer all questions again",
                "sources": [],
                "followups": ["All same", "All new", "Change some"],
                "guided": True,
                "step": "bulk_review_check",
            }
    
    # ── Handle asking specific questions after bulk review ────────────────────────
    if flow.state.get("_questions_to_ask"):
        questions_to_ask = flow.state["_questions_to_ask"]
        current_question = questions_to_ask[0]
        
        # Check if we're waiting for an answer to the current question
        if not flow.state.get(current_question):
            # Still waiting for answer, process the input
            # (This will be handled by the normal flow logic below)
            pass
        else:
            # Current question answered, remove from list and move to next
            questions_to_ask.pop(0)
            flow.state["_questions_to_ask"] = questions_to_ask
            flow.save()
            
            if questions_to_ask:
                # More questions to ask
                return _ask_next_pending_question(flow)
            else:
                # All questions answered, move to details_collection
                flow.state["current_step"] = "details_collection"
                flow.save()
                return {
                    "answer": "Great! Now let's collect your details.\n\n" + _ask_details_collection(flow)["answer"],
                    "sources": [],
                    "followups": [],
                    "guided": True,
                    "step": "details_collection",
                }

    # ── Applicant type ───────────────────────────────────────────
    if step == "applicant_type":
        # Match keywords within full Tamil/Hindi/English sentences
        # Tamil: "இந்திய குடிமகன்", "இந்திய காம்pany / HUF / நிறுவனம்", "வெளிநாட்டு குடிமகன் / NRI / வெளிநாடு"
        
        inp_lower = inp.lower()
        
        # Check for Indian Citizen (most common, check first)
        if re.search(r"(இந்திய\s*குடிமகன்|indian\s*citizen|குடிமகன்|भारतीय\s*नागरिक)", inp_lower, re.IGNORECASE):
            flow.state["applicant_type"] = "indian_citizen"
            flow.advance_step()
            flow.save()
            return _ask_step(flow)
        
        # Check for Foreign/NRI/Overseas
        elif re.search(r"(வெளிநாட்டு|வெளிநாடு|foreign|nri|overseas|विदेशी|प्रवासी)", inp_lower, re.IGNORECASE):
            flow.state["service_id"] = None
            flow.state["complete"] = True
            flow.save()
            return None
        
        # Check for Company/Entity
        elif re.search(r"(நிறுவனம்|காம்pany|company|huf|firm|कंपनी)", inp_lower, re.IGNORECASE):
            flow.state["service_id"] = None
            flow.state["complete"] = True
            flow.save()
            return None
        
        # Fallback: number choice
        elif inp.strip() in ("1", "2", "3"):
            if inp.strip() == "1":
                flow.state["applicant_type"] = "indian_citizen"
                flow.advance_step()
                flow.save()
                return _ask_step(flow)
            else:
                flow.state["service_id"] = None
                flow.state["complete"] = True
                flow.save()
                return None
        
        else:
            opts = {"type": "radio", "label": "Applicant type", "field": "applicant_type",
                    "choices": ["Indian Citizen", "Indian Company / HUF / Firm", "Foreign Citizen / NRI / Overseas"]}
            return {"answer": "Could you pick one of these?", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Submission mode (Q2) ─────────────────────────────────────
    elif step == "submission_mode":
        # Match keywords within full Tamil/Hindi/English sentences
        # Tamil option 1: "Aadhaar-அடிப்படையிலான ஆன்லைன் (eKYC)"
        # Tamil option 2: "ஸ்கேன் செய்யப்பட்ட ஆவணங்களைப் பதிவேற்றவும் & eSign"
        # Tamil option 3: "ஆன்லைன் + கூரியர் உடல் படிவத்தை நிரப்பவும்"
        
        inp_lower = inp.lower()
        inp_stripped = inp.strip()
        
        # FIRST: Check for EXACT match with option labels (when user clicks in UI)
        option_map = {
            "aadhaar-based online (ekyc)": "Aadhaar-based Online (eKYC)",
            "upload scanned docs & esign": "Upload scanned docs & eSign",
            "fill online + courier physical form": "Fill online + courier physical form",
        }
        
        exact_match = option_map.get(inp_lower)
        if exact_match:
            print(f"[DEBUG submission_mode] Exact match found: {exact_match}")
            flow.state["submission_mode"] = exact_match
            flow.state["_saved_submission_mode"] = exact_match
            flow.save()
            print(f"[DEBUG submission_mode] Saved to flow.state: {flow.state['submission_mode']}")
            return _advance_after_answer(flow, user_id)
        
        # Option 1: Aadhaar-based eKYC
        if re.search(r"(aadhaar|ஆதார்|आधार|ekyc|அடிப்படையிலான)", inp_lower, re.IGNORECASE) and not re.search(r"(courier|கூரியர்|upload|பதிவேற்|scan|ஸ்கேன்)", inp_lower, re.IGNORECASE):
            flow.state["submission_mode"] = "Aadhaar-based Online (eKYC)"
            flow.state["_saved_submission_mode"] = "Aadhaar-based Online (eKYC)"
            flow.save()
            return _advance_after_answer(flow, user_id)
        
        # Option 2: Upload scanned docs & eSign
        elif re.search(r"(upload|scan|ஸ்கேன்|பதிவேற்|செய்யப்பட்ட|ஆவணங்கள்|esign|स्कैन|अपलोड)", inp_lower, re.IGNORECASE):
            flow.state["submission_mode"] = "Upload scanned docs & eSign"
            flow.state["_saved_submission_mode"] = "Upload scanned docs & eSign"
            flow.save()
            return _advance_after_answer(flow, user_id)
        
        # Option 3: Fill online + courier physical form
        elif re.search(r"(courier|கூரியர்|நிரப்|படிவம்|உடல்|physical|fill|कूरियर|फॉर्म)", inp_lower, re.IGNORECASE):
            flow.state["submission_mode"] = "Fill online + courier physical form"
            flow.state["_saved_submission_mode"] = "Fill online + courier physical form"
            flow.save()
            return _advance_after_answer(flow, user_id)
        
        # Fallback: number choice
        elif inp.strip() in ("1", "2", "3"):
            choices = ["Aadhaar-based Online (eKYC)", "Upload scanned docs & eSign", "Fill online + courier physical form"]
            flow.state["submission_mode"] = choices[int(inp.strip()) - 1]
            flow.state["_saved_submission_mode"] = flow.state["submission_mode"]
            flow.save()
            return _advance_after_answer(flow, user_id)
        
        else:
            # Get current language for bilingual options
            current_language = flow.state.get("_current_language", language)
            
            if current_language == "ta":
                # Tamil + English bilingual options
                opts = {"type": "radio", "label": "Submission mode", "field": "submission_mode",
                        "choices": [
                            "Aadhaar-based Online (eKYC) | ஆதார் அடிப்படையிலான ஆன்லைன்",
                            "Upload scanned docs & eSign | ஸ்கேன் செய்யப்பட்ட ஆவணங்களைப் பதிவேற்றவும் & eSign",
                            "Fill online + courier physical form | ஆன்லைனில் நிரப்பவும் + கூரியர் உடல் படிவம்"
                        ]}
                return {"answer": "**உங்கள் PAN விண்ணப்ப ஆவணங்களை எவ்வாறு சமர்ப்பிக்க விரும்புகிறீர்கள்?**\n\n*How do you want to submit your PAN application documents?*", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}
            else:
                opts = {"type": "radio", "label": "Submission mode", "field": "submission_mode",
                        "choices": ["Aadhaar-based Online (eKYC)", "Upload scanned docs & eSign", "Fill online + courier physical form"]}
                return {"answer": "**How do you want to submit your PAN application documents?**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Delivery mode (Q2b) ──────────────────────────────────────
    elif step == "delivery_mode":
        # Match English, Tamil, and Hindi keywords within the full response text
        # Tamil Option 1: "வீட்டிற்கு நகல் + மின்னஞ்சலில் மென்மையான நகல் (கட்டணம் பொருந்தும்)"
        # Tamil Option 2: "மின்னஞ்சலில் மென்மையான நகல் மட்டும் (கட்டணம் பொருந்தும்)"
        # English Option 1: "Physical copy to home + soft copy on email (Fees applicable)"
        # English Option 2: "Only soft copy on email (Fees applicable)"
        
        print(f"[DEBUG delivery_mode] Received input: {inp!r}")
        
        inp_lower = inp.lower()
        inp_stripped = inp.strip()
        
        # FIRST: Check for EXACT match with option labels (when user clicks in UI)
        option_map = {
            "physical copy to home + soft copy on email (fees applicable)": "physical_and_soft",
            "only soft copy on email (fees applicable)": "soft_only",
        }
        
        exact_match = option_map.get(inp_lower)
        if exact_match:
            print(f"[DEBUG delivery_mode] Exact match found: {exact_match}")
            flow.state["delivery_mode"] = exact_match
            if exact_match == "physical_and_soft":
                flow.state["_saved_delivery_mode"] = "Physical copy to home + soft copy on email (Fees applicable)"
                flow.save()
                next_q = _advance_after_answer(flow, user_id)
                next_q["answer"] = _FEE_PHYSICAL.strip() + "\n\n---\n\n" + next_q["answer"]
                return next_q
            else:
                flow.state["_saved_delivery_mode"] = "Only soft copy on email (Fees applicable)"
                flow.save()
                next_q = _advance_after_answer(flow, user_id)
                next_q["answer"] = _FEE_SOFT.strip() + "\n\n---\n\n" + next_q["answer"]
                return next_q
        
        # Key distinction: Option 1 has "வீட்டிற்கு" (home) OR "+", Option 2 has "மட்டும்" (only)
        has_home_or_plus = re.search(r"(வீடு|வீட்டிற்கு|home|physical|இல்லம்|घर|\+)", inp, re.IGNORECASE)
        has_only = re.search(r"(மட்டும்|only|केवल)", inp, re.IGNORECASE)
        
        print(f"[DEBUG delivery_mode] has_home_or_plus={bool(has_home_or_plus)}, has_only={bool(has_only)}")
        
        # If response contains "மட்டும்" (only), it's soft-only option (Option 2)
        if has_only:
            print(f"[DEBUG delivery_mode] Matched: soft_only (has 'மட்டும்')")
            flow.state["delivery_mode"] = "soft_only"
            flow.state["_saved_delivery_mode"] = "Only soft copy on email (Fees applicable)"
            flow.save()
            next_q = _advance_after_answer(flow, user_id)
            next_q["answer"] = _FEE_SOFT.strip() + "\n\n---\n\n" + next_q["answer"]
            return next_q
        # If response contains "வீட்டிற்கு" or "+", it's physical+soft option (Option 1)
        elif has_home_or_plus:
            print(f"[DEBUG delivery_mode] Matched: physical_and_soft (has 'வீட்டிற்கு' or '+')")
            flow.state["delivery_mode"] = "physical_and_soft"
            flow.state["_saved_delivery_mode"] = "Physical copy to home + soft copy on email (Fees applicable)"
            flow.save()
            next_q = _advance_after_answer(flow, user_id)
            next_q["answer"] = _FEE_PHYSICAL.strip() + "\n\n---\n\n" + next_q["answer"]
            return next_q
        # Fallback: number choice
        elif inp.strip() in ("1", "2"):
            print(f"[DEBUG delivery_mode] Matched: number choice {inp.strip()}")
            if inp.strip() == "1":
                flow.state["delivery_mode"] = "physical_and_soft"
                flow.state["_saved_delivery_mode"] = "Physical copy to home + soft copy on email (Fees applicable)"
                flow.save()
                next_q = _advance_after_answer(flow, user_id)
                next_q["answer"] = _FEE_PHYSICAL.strip() + "\n\n---\n\n" + next_q["answer"]
                return next_q
            else:
                flow.state["delivery_mode"] = "soft_only"
                flow.state["_saved_delivery_mode"] = "Only soft copy on email (Fees applicable)"
                flow.save()
                next_q = _advance_after_answer(flow, user_id)
                next_q["answer"] = _FEE_SOFT.strip() + "\n\n---\n\n" + next_q["answer"]
                return next_q
        else:
            print(f"[DEBUG delivery_mode] NO MATCH - returning options again")
            # Get current language for bilingual options
            current_language = flow.state.get("_current_language", language)
            
            if current_language == "ta":
                opts = {"type": "radio", "label": "PAN delivery", "field": "delivery_mode",
                        "choices": [
                            "Physical copy to home + soft copy on email (Fees applicable) | வீட்டிற்கு நகல் + மின்னஞ்சலில் மென்மையான நகல்",
                            "Only soft copy on email (Fees applicable) | மின்னஞ்சலில் மென்மையான நகல் மட்டும்"
                        ]}
                return {"answer": "**உங்கள் PAN கார்டு எவ்வாறு டெலிவரி செய்ய வேண்டும்?**\n\n*How do you want your PAN card to be delivered?*", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}
            else:
                opts = {"type": "radio", "label": "PAN delivery", "field": "delivery_mode",
                        "choices": ["Physical copy to home + soft copy on email (Fees applicable)", "Only soft copy on email (Fees applicable)"]}
                return {"answer": "**How do you want your PAN card to be delivered?**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Aadhaar photo consent (Q3) ───────────────────────────────
    elif step == "aadhaar_photo":
        # Match Yes/No in English, Tamil, and Hindi
        inp_lower = inp.lower()
        inp_stripped = inp.strip()
        
        # FIRST: Check for EXACT match with option labels
        option_map = {
            "yes": True,
            "no": False,
            "ஆம்": True,
            "இல்லை": False,
        }
        
        exact_match = option_map.get(inp_lower)
        if exact_match is not None:
            print(f"[DEBUG aadhaar_photo] Exact match found: {exact_match}")
            flow.state["aadhaar_photo"] = exact_match
            flow.state["_saved_aadhaar_photo"] = exact_match
            flow.save()
            return _advance_after_answer(flow, user_id)
        
        _yes = re.compile(r"^(yes|y|yeah|yep|agree|ok|okay|sure|aam|ஆம்|हाँ|हां)$", re.IGNORECASE)
        _no  = re.compile(r"^(no|nope|nah|disagree|decline|illa|illai|இல்லை|नहीं)$", re.IGNORECASE)
        if _yes.match(inp):
            flow.state["aadhaar_photo"] = True
            flow.state["_saved_aadhaar_photo"] = True
            flow.save()
            return _advance_after_answer(flow, user_id)
        elif _no.match(inp):
            flow.state["aadhaar_photo"] = False
            flow.state["_saved_aadhaar_photo"] = False
            flow.save()
            return _advance_after_answer(flow, user_id)
        else:
            # Get current language for bilingual options
            current_language = flow.state.get("_current_language", language)
            
            if current_language == "ta":
                opts = {"type": "radio", "label": "Aadhaar photo consent", "field": "aadhaar_photo", 
                        "choices": ["Yes | ஆம்", "No | இல்லை"]}
                return {
                    "answer": "**என் PAN கார்டில் என் ஆதார் புகைப்படத்தை அச்சிட நான் ஒப்புக்கொள்கிறேன்.**\n\n*I hereby agree to have my Aadhaar photo printed on my PAN Card.*\n\n> குறிப்பு: உங்கள் ஆதார் புகைப்படத்தைப் பயன்படுத்த விரும்பவில்லை என்றால், தனி புகைப்படத்துடன் PAN விண்ணப்பிக்கலாம்.\n\n> *Note: If you do not wish to use your Aadhaar photo, you may apply for a PAN with a separate photograph.*",
                    "sources": [], "followups": [], "guided": True, "step": step, "options": opts
                }
            else:
                opts = {"type": "radio", "label": "Aadhaar photo consent", "field": "aadhaar_photo", "choices": ["Yes", "No"]}
                return {"answer": "**I hereby agree to have my Aadhaar photo printed on my PAN Card.**\n\n> Note: If you do not wish to use your Aadhaar photo, you may apply for a PAN with a separate photograph.", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Source of income (Q4) ────────────────────────────────────
    elif step == "source_of_income":
        # Match English, Tamil, and Hindi keywords (without word boundaries for Tamil)
        # Tamil translations: சம்பளம், தொழில், வணிகம், வீட்டு சொத்து, பிற மூலங்கள், மூலதன ஆதாயம், வருமானம் இல்லை
        
        print(f"[DEBUG source_of_income] Received input: {inp!r}")
        
        _SOI = [
            (re.compile(r"(salary|salaried|1|சம்பளம்|वेतन|तनख्वाह)", re.IGNORECASE), "Salary"),
            (re.compile(r"(business|profession|self.?employed|freelanc|2|வணிகம்|தொழில்|வியாபாரம்|व्यवसाय|व्यापार|पेशा)", re.IGNORECASE), "Income from Business / Profession"),
            (re.compile(r"(house\s+property|rental|rent|3|வீட்டு|சொத்து|வாடகை|संपत्ति|किराया|मकान)", re.IGNORECASE), "Income from House property"),
            (re.compile(r"(other\s+sources?|4|பிற|மூலங்கள்|अन्य|स्रोत)", re.IGNORECASE), "Income from Other sources"),
            (re.compile(r"(capital\s+gains?|5|மூலதன|ஆதாயம்|ஆதாயங்கள்|पूंजीगत|लाभ|पूंजी)", re.IGNORECASE), "Capital Gains"),
            (re.compile(r"(no\s+income|unemployed|student|homemaker|housewife|retired|fresher|6|வருமானம்\s*இல்லை|இல்லை|மாணவர்|வேலை\s*இல்லை|गृहिणी|छात्र|कोई\s*आय\s*नहीं)", re.IGNORECASE), "No income"),
        ]
        matched = []
        for pat, label in _SOI:
            if pat.search(inp):
                matched.append(label)
                print(f"[DEBUG source_of_income] Matched: {label}")
        
        if matched:
            print(f"[DEBUG source_of_income] All matched: {matched}")
            flow.state["source_of_income"] = ", ".join(matched)
            flow.state["_saved_source_of_income"] = matched  # Save as list
            flow.save()
            return _advance_after_answer(flow, user_id)
        else:
            print(f"[DEBUG source_of_income] NO MATCH - returning options")
        
        # Get current language for bilingual options
        current_language = flow.state.get("_current_language", language)
        
        if current_language == "ta":
            opts = {"type": "radio", "label": "Source of Income", "field": "source_of_income",
                    "choices": [
                        "Salary | சம்பளம்",
                        "Income from Business / Profession | வணிகம் / தொழில் வருமானம்",
                        "Income from House property | வீட்டு சொத்து வருமானம்",
                        "Income from Other sources | பிற ஆதாரங்களிலிருந்து வருமானம்",
                        "Capital Gains | மூலதன ஆதாயங்கள்",
                        "No income | வருமானம் இல்லை"
                    ]}
            return {"answer": "**உங்கள் வருமான மூலத்தைத் தேர்ந்தெடுக்கவும்:**\n\n*Please select your Source of Income:*", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}
        else:
            opts = {"type": "radio", "label": "Source of Income", "field": "source_of_income",
                    "choices": ["Salary", "Income from Business / Profession", "Income from House property",
                                "Income from Other sources", "Capital Gains", "No income"]}
            return {"answer": "**Please select your Source of Income:**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Address for communication (Q5) ───────────────────────────
    elif step == "address_for_comm":
        # Match keywords within full Tamil/Hindi/English sentences
        inp_lower = inp.lower()
        inp_stripped = inp.strip()
        
        # FIRST: Check for EXACT match with option labels
        option_map = {
            "residence": "Residence",
            "office": "Office",
            "representative assessee (ra)": "Representative Assessee (RA)",
            "வீடு": "Residence",
            "அலுவலகம்": "Office",
        }
        
        exact_match = option_map.get(inp_lower)
        if exact_match:
            print(f"[DEBUG address_for_comm] Exact match found: {exact_match}")
            flow.state["address_for_comm"] = exact_match
            flow.state["_saved_address_for_comm"] = exact_match
            flow.save()
            return _advance_after_answer(flow, user_id)
        
        # Check for keywords in the response
        if re.search(r"(குடியிருப்பு|வீடு|இல்லம்|residence|home|निवास|घर)", inp_lower, re.IGNORECASE):
            flow.state["address_for_comm"] = "Residence"
            flow.state["_saved_address_for_comm"] = "Residence"
            flow.save()
            return _advance_after_answer(flow, user_id)
        elif re.search(r"(அலுவலகம்|வேலை|office|work|कार्यालय|दफ्तर)", inp_lower, re.IGNORECASE):
            flow.state["address_for_comm"] = "Office"
            flow.state["_saved_address_for_comm"] = "Office"
            flow.save()
            return _advance_after_answer(flow, user_id)
        elif re.search(r"(பிரதிநிதி|representative|प्रतिनिधि)", inp_lower, re.IGNORECASE):
            flow.state["address_for_comm"] = "Representative Assessee (RA)"
            flow.state["_saved_address_for_comm"] = "Representative Assessee (RA)"
            flow.save()
            return _advance_after_answer(flow, user_id)
        elif inp.strip() in ("1", "2", "3"):
            choices = ["Residence", "Office", "Representative Assessee (RA)"]
            flow.state["address_for_comm"] = choices[int(inp.strip()) - 1]
            flow.state["_saved_address_for_comm"] = flow.state["address_for_comm"]
            flow.save()
            return _advance_after_answer(flow, user_id)
        else:
            # Get current language for bilingual options
            current_language = flow.state.get("_current_language", language)
            
            if current_language == "ta":
                hint = "**காகிதமற்ற PAN விண்ணப்பத்திற்கான முக்கிய வழிமுறைகள் (eKYC):**\n1. ஆதார் அட்டையில் உள்ள முகவரி வசிப்பிட முகவரியாக பயன்படுத்தப்படும்.\n2. PAN கார்டு ஆதார் முகவரிக்கு அனுப்பப்படும்.\n3. ஆதார் முகவரி நீளம் வரி துறை வரம்பை மீறினால், eKYC கிடைக்காது.\n\n*Important instructions for e-KYC (Individual): Address from Aadhaar will be used as residence address.*"
                opts = {"type": "radio", "label": "Address for Communication", "field": "address_for_comm",
                        "choices": ["Residence | வீடு", "Office | அலுவலகம்", "Representative Assessee (RA) | பிரதிநிதி மதிப்பீட்டாளர்"], "hint": hint}
                return {"answer": "**தொடர்புக்கான முகவரி** — தயவுசெய்து பொருந்தும் ஒன்றைத் தேர்ந்தெடுக்கவும்:\n\n*Address for Communication — Please tick as applicable:*", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}
            else:
                hint = "**Important instructions for e-KYC (Individual):**\n1. Address from Aadhaar card will be used as residence address.\n2. PAN card dispatched to Aadhaar address.\n3. If Aadhaar address exceeds IT Dept length limit, e-KYC won't be available."
                opts = {"type": "radio", "label": "Address for Communication", "field": "address_for_comm",
                        "choices": ["Residence", "Office", "Representative Assessee (RA)"], "hint": hint}
                return {"answer": "**Address for Communication** — Please tick as applicable:", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Residential status (Q6) ──────────────────────────────────
    elif step == "residential_status":
        # Match keywords within full Tamil/Hindi/English sentences
        # Tamil translations: "குடியிருப்பாளர்", "குடியுரிமை இல்லாதவர்", "குடியிருப்பாளர் ஆனால் சாதாரணமாக வசிப்பவர் அல்ல"
        inp_lower = inp.lower()
        inp_stripped = inp.strip()
        
        print(f"[DEBUG residential_status] Received input: {inp!r}")
        
        # FIRST: Check for EXACT match with option labels
        option_map = {
            "resident": "Resident",
            "non-resident": "Non-resident",
            "resident but not ordinarily resident": "Resident but not ordinarily resident",
            "குடியிருப்பாளர்": "Resident",
            "குடியுரிமை இல்லாதவர்": "Non-resident",
        }
        
        exact_match = option_map.get(inp_lower)
        if exact_match:
            print(f"[DEBUG residential_status] Exact match found: {exact_match}")
            flow.state["residential_status"] = exact_match
            flow.state["_saved_residential_status"] = exact_match
            flow.save()
            return _advance_after_answer(flow, user_id)
        
        # Check for "resident but not ordinarily resident" first (most specific)
        # Tamil: "குடியிருப்பாளர் ஆனால் சாதாரணமாக வசிப்பவர் அல்ல" contains "ஆனால்" (but) and "சாதாரணமாக" (ordinarily)
        if re.search(r"(ஆனால்|சாதாரணமாக|வசிப்பவர்|not\s*ordinarily|rnor|सामान्य\s*निवासी\s*नहीं)", inp, re.IGNORECASE):
            print(f"[DEBUG residential_status] Matched: Resident but not ordinarily resident")
            flow.state["residential_status"] = "Resident but not ordinarily resident"
            flow.state["_saved_residential_status"] = "Resident but not ordinarily resident"
            flow.save()
            return _advance_after_answer(flow, user_id)
        # Check for non-resident
        # Tamil: "குடியுரிமை இல்லாதவர்" contains "இல்லாதவர்" (without) or "குடியுரிமை" (citizenship)
        elif re.search(r"(இல்லாதவர்|வெளிநாட்டவர்|வெளிநாட்டு|non.?resident|nri|अनिवासी|गैर)", inp, re.IGNORECASE):
            print(f"[DEBUG residential_status] Matched: Non-resident")
            flow.state["residential_status"] = "Non-resident"
            flow.state["_saved_residential_status"] = "Non-resident"
            flow.save()
            return _advance_after_answer(flow, user_id)
        # Check for resident (check last as it's least specific)
        # Tamil: "குடியிருப்பாளர்" contains "குடியிருப்பாளர்" or "குடிமகன்"
        elif re.search(r"(குடியிருப்பாளர்|குடிமகன்|resident|निवासी|स्थायी)", inp, re.IGNORECASE):
            print(f"[DEBUG residential_status] Matched: Resident")
            flow.state["residential_status"] = "Resident"
            flow.state["_saved_residential_status"] = "Resident"
            flow.save()
            return _advance_after_answer(flow, user_id)
        # Fallback: number choice
        elif inp.strip() in ("1", "2", "3"):
            choices = ["Resident", "Non-resident", "Resident but not ordinarily resident"]
            flow.state["residential_status"] = choices[int(inp.strip()) - 1]
            flow.state["_saved_residential_status"] = flow.state["residential_status"]
            flow.save()
            print(f"[DEBUG residential_status] Matched: number choice {inp.strip()}")
            return _advance_after_answer(flow, user_id)
        else:
            print(f"[DEBUG residential_status] NO MATCH - returning options")
            # Get current language for bilingual options
            current_language = flow.state.get("_current_language", language)
            
            if current_language == "ta":
                opts = {"type": "radio", "label": "Residential Status", "field": "residential_status",
                        "choices": [
                            "Resident | குடியிருப்பாளர்",
                            "Non-resident | குடியுரிமை இல்லாதவர்",
                            "Resident but not ordinarily resident | குடியிருப்பாளர் ஆனால் சாதாரணமாக வசிப்பவர் அல்ல"
                        ]}
                return {"answer": "**உங்கள் குடியிருப்பு நிலை என்ன?**\n\n*What is your Residential Status?*", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}
            else:
                opts = {"type": "radio", "label": "Residential Status", "field": "residential_status",
                        "choices": ["Resident", "Non-resident", "Resident but not ordinarily resident"]}
                return {"answer": "**What is your Residential Status?**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Representative Assessee (Q7) ─────────────────────────────
    elif step == "rep_assessee":
        # Match Yes/No in English, Tamil, and Hindi
        inp_lower = inp.lower()
        inp_stripped = inp.strip()
        
        # FIRST: Check for EXACT match with option labels
        option_map = {
            "yes": True,
            "no": False,
            "ஆம்": True,
            "இல்லை": False,
        }
        
        exact_match = option_map.get(inp_lower)
        if exact_match is not None:
            print(f"[DEBUG rep_assessee] Exact match found: {exact_match}")
            flow.state["rep_assessee"] = exact_match
            flow.state["_saved_rep_assessee"] = exact_match
            flow.save()
            return _advance_after_answer(flow, user_id)
        
        _yes = re.compile(r"^(yes|y|yeah|yep|yup|sure|ok|okay|aam|ஆம்|हाँ|हां)$", re.IGNORECASE)
        _no  = re.compile(r"^(no|nope|nah|n|illa|illai|இல்லை|नहीं)$", re.IGNORECASE)
        if _yes.match(inp):
            flow.state["rep_assessee"] = True
            flow.state["_saved_rep_assessee"] = True
            flow.save()
            return _advance_after_answer(flow, user_id)
        elif _no.match(inp):
            flow.state["rep_assessee"] = False
            flow.state["_saved_rep_assessee"] = False
            flow.save()
            return _advance_after_answer(flow, user_id)
        else:
            # Get current language for bilingual options
            current_language = flow.state.get("_current_language", language)
            
            if current_language == "ta":
                opts = {"type": "radio", "label": "Representative Assessee", "field": "rep_assessee",
                        "choices": ["Yes | ஆம்", "No | இல்லை"]}
                return {
                    "answer": "**பிரதிநிதி மதிப்பீட்டாளரை நியமிக்கிறீர்களா?**\n\n*Appointing Representative Assessee?*\n\n> பிரதிநிதி மதிப்பீட்டாளர் என்பது மற்றொரு நபரின் சார்பாக வரி கடமைகளை நிர்வகிக்கும் ஒருவர் (எ.கா. சிறியவருக்கு பாதுகாவலர், அல்லது இறந்தவருக்கு சட்ட வாரிசு). மற்றொருவர் சார்பாக நீங்கள் விண்ணப்பிக்கும் பட்சத்தில் மட்டும் **ஆம்** என்பதைத் தேர்ந்தெடுக்கவும்.\n\n> *A Representative Assessee manages tax obligations on behalf of another person (e.g. guardian for a minor, or legal heir for deceased). Select **Yes** only if applying on behalf of someone else.*",
                    "sources": [], "followups": [], "guided": True, "step": step, "options": opts
                }
            else:
                opts = {"type": "radio", "label": "Representative Assessee", "field": "rep_assessee",
                        "choices": ["Yes", "No"]}
                return {
                    "answer": "**Appointing Representative Assessee?**\n\n> A Representative Assessee is someone who manages tax obligations on behalf of another person (e.g. a guardian for a minor, or a legal heir for a deceased person). Select **Yes** only if you are applying on behalf of someone else.",
                    "sources": [], "followups": [], "guided": True, "step": step, "options": opts
                }

    # ── Details collection (Q8) ───────────────────────────────────
    elif step == "details_collection":
        # ── FIRST: Check for cancellation/restart intent BEFORE any email logic ──
        if re.search(r"\b(apply|start|begin|new|pan|cancel|stop|quit|restart)\b", inp.lower()):
            flow.state["service_id"] = None
            flow.state["complete"] = True
            flow.save()
            if language == "ta":
                msg = "சரி! தற்போதைய விண்ணப்பத்தை நிறுத்தினேன். எப்போது வேண்டுமானாலும் மீண்டும் தொடங்கலாம்."
            elif language == "hi":
                msg = "ठीक है! मैंने आवेदन रद्द कर दिया। जब चाहें फिर से शुरू करें।"
            else:
                msg = "Got it! I've cancelled the current application. Feel free to start fresh whenever you're ready."
            return {
                "answer": msg,
                "sources": [], "followups": [], "guided": False, "close_form": True,
            }
        
        # ── Handle email_confirm response ─────────────────────────
        if flow.state.get("_email_confirm_asked") and not flow.state.get("email"):
            _use_acct = re.compile(r"^yes\b", re.IGNORECASE)
            _use_new  = re.compile(r"^no\b", re.IGNORECASE)

            if _use_acct.match(inp):
                flow.state["email"] = flow.state.get("_account_email", "")
                flow.state["email_source"] = "account"
                flow.state["_email_input_pending"] = False
                flow.save()
                missing = _missing_details(flow)
                if not missing:
                    flow.advance_step()
                    flow.save()
                    return _build_confirmation(flow)
                return _ask_details_collection(flow, language)
            elif _use_new.match(inp):
                flow.state["_email_input_pending"] = True
                flow.save()
                if language == "ta":
                    msg = "PAN கடிதப் பரிமாற்றத்திற்கு பயன்படுத்த விரும்பும் மின்னஞ்சல் முகவரியை உள்ளிடவும்:"
                elif language == "hi":
                    msg = "PAN पत्राचार के लिए जो ईमेल उपयोग करना चाहते हैं वह दर्ज करें:"
                else:
                    msg = "Please enter the email address you'd like to use for PAN correspondence:"
                return {
                    "answer": msg,
                    "sources": [], "followups": [], "guided": True,
                    "step": "details_collection",
                    "options": {"type": "email_input"},
                }
            elif flow.state.get("_email_input_pending"):
                email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", inp)
                if email_match:
                    flow.state["email"] = email_match.group(0).lower()
                    flow.state["email_source"] = "new"
                    flow.state["_email_input_pending"] = False
                    flow.save()
                    missing = _missing_details(flow)
                    if not missing:
                        flow.advance_step()
                        flow.save()
                        return _build_confirmation(flow)
                    return _ask_details_collection(flow, language)
                else:
                    if language == "ta":
                        msg = "சரியான மின்னஞ்சல் முகவரி இல்லை. மீண்டும் உள்ளிடவும் (எ.கா. yourname@example.com):"
                    elif language == "hi":
                        msg = "यह मान्य ईमेल नहीं है। कृपया सही ईमेल दर्ज करें (जैसे yourname@example.com):"
                    else:
                        msg = "That doesn't look like a valid email. Please enter a valid email address (e.g. yourname@example.com), or type **cancel** to start over:"
                    return {
                        "answer": msg,
                        "sources": [], "followups": [], "guided": True,
                        "step": "details_collection",
                        "options": {"type": "email_input"},
                    }

        # Try to extract whatever the user typed (name, mother, salary)
        _extract_details(flow, inp, user_input)
        flow.save()  # CRITICAL: Save after extraction!
        
        # Auto-save extracted details to profile (progressive save)
        if user_id and any([
            flow.state.get("full_name"),
            flow.state.get("mother_name"),
            flow.state.get("email"),
            flow.state.get("salary")
        ]):
            try:
                save_flow_to_profile(user_id, flow.state)
                print(f"[DEBUG] Auto-saved details to profile for user {user_id}")
            except Exception as e:
                print(f"[ERROR] Failed to auto-save profile: {e}")
        
        missing = _missing_details(flow)
        if not missing:
            # All details collected — move to confirmation
            flow.advance_step()
            flow.save()
            return _build_confirmation(flow)
        # Some fields still missing — ask for them
        return _ask_details_collection(flow, language)

    # ── Confirmation (Q9) ─────────────────────────────────────────
    elif step == "confirmation":
        # ── PRIORITY 0: Check for cancellation FIRST ──────────────────────
        if _is_cancellation(inp):
            flow.state["service_id"] = None
            flow.state["complete"] = True
            flow.state["pending_modification"] = None
            flow.save()
            return {
                "answer": "No problem! I've cancelled the application. Feel free to start fresh whenever you're ready.",
                "sources": [],
                "followups": ["Apply for new PAN", "Check PAN status", "Link Aadhaar with PAN"],
                "guided": False,
                "close_form": True,
            }
        
        _yes = re.compile(
            r"^(yes|y|yeah|yep|yup|sure|ok|okay|proceed|confirm|looks\s+good|correct|all\s+good|go\s+ahead"
            r"|yes,?\s*proceed|yeah\s+proceed|yes\s+please|all\s+set|next|done|good\s+to\s+go|let'?s\s+go"
            r"|move\s+on|continue|next\s+step|proceed\s+please|that'?s\s+(?:correct|right|good|fine)"
            r"|everything'?s?\s+(?:correct|right|good|fine|ok|okay)|looks\s+(?:correct|right|fine)"
            r"|ஆம்|ஆம்,?\s*தொடரவும்|हाँ|हां).*$",
            re.IGNORECASE
        )
        _no = re.compile(
            r"^(no|nope|nah|n|change|modify|update|edit|wrong|incorrect|fix"
            r"|no,?\s*i\s+need\s+to\s+change\s+something"
            r"|change\s+something"
            r"|i\s+want\s+to\s+change"
            r"|i\s+need\s+to\s+change"
            r"|i\s+wanna\s+change"
            r"|want\s+to\s+change"
            r"|need\s+to\s+change"
            r"|ஏதாவது\s+மாற்றவும்"
            r"|மாற்ற\s+வேண்டும்).*$",
            re.IGNORECASE
        )

        # ── PRIORITY 1: User is providing the new value for a pending field ────
        # This must be checked BEFORE _no.match() to avoid "No" being treated as "change something"
        if flow.state.get("pending_modification") and flow.state["pending_modification"] != "__awaiting__":
            field = flow.state["pending_modification"]

            # ── If user says yes/proceed while a field is pending, they're satisfied — advance ──
            if _yes.match(inp):
                flow.state["details_confirmed"] = True
                flow.state["pending_modification"] = None
                flow.advance_step(); flow.save()
                try:
                    if user_id:
                        save_flow_to_profile(user_id, flow.state)
                except Exception as e:
                    print(f"[ERROR] Failed to save profile: {e}")
                current_language = flow.state.get("_current_language", language)
                return _build_documents_response(flow, current_language)

            # ── If user is asking to change a DIFFERENT field, switch to it ──────────────
            # e.g. pending=address_for_comm but user says "i want to update pan delivery"
            requested_field = _detect_modification_field(inp)
            if requested_field and requested_field != field:
                # Check that the message looks like a field request, not a value
                # (has "change/update/want" prefix OR is just the field name)
                _is_field_request = re.search(
                    r"\b(change|update|modify|edit|fix|want\s+to\s+update|want\s+to\s+change"
                    r"|need\s+to\s+change|i\s+want|i\s+need|can\s+i\s+change)\b",
                    inp, re.IGNORECASE
                )
                # Also treat as field request if the entire input is just the field label
                _FIELD_LABELS = {
                    "submission mode", "pan delivery", "aadhaar photo on pan",
                    "source of income", "address for communication",
                    "residential status", "representative assessee",
                    "full name", "annual income", "mother name", "mothers name", "email",
                }
                _is_bare_label = inp.strip().lower() in _FIELD_LABELS
                if _is_field_request or _is_bare_label:
                    flow.state["pending_modification"] = requested_field
                    flow.save()
                    return _ask_for_field(flow, requested_field)

            print(f"[DEBUG] Applying field update: field={field}, inp={inp!r}, user_input={user_input!r}")
            print(f"[DEBUG] Before update: {field}={flow.state.get(field)}")
            _apply_field_update(flow, field, inp, user_input)
            print(f"[DEBUG] After update: {field}={flow.state.get(field)}")
            flow.state["pending_modification"] = None
            flow.save()
            print(f"[DEBUG] Saved flow state, building confirmation...")

            # ── For delivery_mode: show the fee table before the confirmation + re-show options ──
            if field == "delivery_mode":
                confirmation = _build_confirmation(flow)
                new_mode = flow.state.get("delivery_mode")
                if new_mode == "physical_and_soft":
                    fee_block = _FEE_PHYSICAL.strip()
                elif new_mode == "soft_only":
                    fee_block = _FEE_SOFT.strip()
                else:
                    fee_block = ""
                field_prompt = _ask_for_field(flow, field)
                combined = confirmation["answer"]
                if fee_block:
                    combined = fee_block + "\n\n---\n\n" + combined
                combined += "\n\n---\n\n" + field_prompt["answer"]
                # Keep pending so next radio click updates this field
                flow.state["pending_modification"] = field
                flow.save()
                return {
                    "answer": combined,
                    "sources": [],
                    "followups": [],
                    "guided": field_prompt.get("guided", True),
                    "step": "confirmation",
                    "options": field_prompt.get("options"),
                }

            # ── Build confirmation + re-show the field options so user can change again ──
            confirmation = _build_confirmation(flow)
            field_prompt = _ask_for_field(flow, field)

            # Fields with interactive options (radio/checkbox) — keep pending so next click updates
            _INTERACTIVE_FIELDS = {
                "submission_mode", "delivery_mode", "aadhaar_photo",
                "source_of_income", "address_for_comm", "residential_status", "rep_assessee",
            }
            if field in _INTERACTIVE_FIELDS and field_prompt.get("options"):
                flow.state["pending_modification"] = field
                flow.save()
            # Text fields (full_name, mother_name, email, salary): pending_modification stays None
            # — confirmation is shown and they can type a new value or proceed

            combined_answer = confirmation["answer"] + "\n\n---\n\n" + field_prompt["answer"]
            return {
                "answer": combined_answer,
                "sources": [],
                "followups": [],
                "guided": field_prompt.get("guided", True),
                "step": "confirmation",
                "options": field_prompt.get("options"),
            }

        # ── PRIORITY 2: User confirmed — advance and show document list immediately ──
        elif _yes.match(inp):
            flow.state["details_confirmed"] = True
            flow.state["pending_modification"] = None
            flow.advance_step(); flow.save()
            
            # ── Save confirmed details to user profile for future sessions ──
            try:
                if user_id:
                    save_flow_to_profile(user_id, flow.state)
                    print(f"[DEBUG] Saved profile for user {user_id}")
            except Exception as e:
                print(f"[ERROR] Failed to save profile: {e}")
            
            # Get current language from flow state
            current_language = flow.state.get("_current_language", language)
            return _build_documents_response(flow, current_language)

        # ── PRIORITY 2.5: User typed a field name or inline update without clicking "Change something" ──
        # e.g. "name to Ravi and salary to 5 lakh", "email to ravi@gmail.com", "Source of income", "residential status"
        elif not _yes.match(inp) and not _no.match(inp) and not flow.state.get("pending_modification"):
            # First try: extract inline value updates ("name to X", "salary 5 lakh", etc.)
            updates_made = _extract_multiple_field_updates(flow, inp, user_input)
            if updates_made:
                flow.state["pending_modification"] = None
                flow.save()
                return _build_confirmation(flow)

            # Second try: user named a field they want to change ("Source of income", "residential status", etc.)
            field = _detect_modification_field(inp)
            if field:
                flow.state["pending_modification"] = field
                flow.save()
                return _ask_for_field(flow, field)
            # Nothing matched — fall through to generic response

        # ── PRIORITY 3: User clicked "Change something" or said what to change ──
        elif _no.match(inp):
            # e.g., "change my name to John and mother name to Mary and salary to 5 lakh"
            updates_made = _extract_multiple_field_updates(flow, inp, user_input)
            
            if updates_made:
                # User provided multiple updates in one message - apply them and show confirmation
                flow.state["pending_modification"] = None
                flow.save()
                return _build_confirmation(flow)
            
            # Try to detect which field they want to change from this message
            field = _detect_modification_field(inp)
            if field:
                flow.state["pending_modification"] = field
                flow.save()
                return _ask_for_field(flow, field)
            else:
                # Ask what they want to change — show a menu of editable fields
                s = flow.state
                lines = ["Sure! Which detail would you like to change?\n"]
                if s.get("full_name"):        lines.append(f"- **Full name** — currently: *{s['full_name']}*")
                if s.get("grandfather_name"): lines.append(f"- **Grandfather's name** — currently: *{s['grandfather_name']}*")
                if s.get("mother_name"):      lines.append(f"- **Mother's name** — currently: *{s['mother_name']}*")
                if s.get("email"):        lines.append(f"- **Email** — currently: *{s['email']}*")
                if s.get("salary"):       lines.append(f"- **Annual income** — currently: *{s['salary']}*")
                lines.append(f"- **Submission mode** — currently: *{s.get('submission_mode', '—')}*")
                lines.append(f"- **PAN delivery** — currently: *{'Physical + e-PAN' if s.get('delivery_mode') == 'physical_and_soft' else 'e-PAN only' if s.get('delivery_mode') else '—'}*")
                lines.append(f"- **Aadhaar photo on PAN** — currently: *{'Yes' if s.get('aadhaar_photo') else 'No' if s.get('aadhaar_photo') is not None else '—'}*")
                lines.append(f"- **Source of income** — currently: *{s.get('source_of_income', '—')}*")
                lines.append(f"- **Address for communication** — currently: *{s.get('address_for_comm', '—')}*")
                lines.append(f"- **Residential status** — currently: *{s.get('residential_status', '—')}*")
                lines.append(f"- **Representative Assessee** — currently: *{'Yes' if s.get('rep_assessee') else 'No' if s.get('rep_assessee') is not None else '—'}*")
                lines.append("\nYou can update multiple fields at once — just say something like:")
                lines.append('*"name to John and salary to 5 lakh"*')
                lines.append('*"email to john@example.com and mother name to Mary"*')
                lines.append("Or tell me just one field: *\"change my name\"*")
                flow.state["pending_modification"] = "__awaiting__"
                flow.save()
                return {
                    "answer": "\n".join(lines),
                    "sources": [], "followups": [], "guided": False, "step": step,
                }

        # ── PRIORITY 4: User is responding to "what to change" prompt ──────────
        elif flow.state.get("pending_modification") == "__awaiting__":
            # ── Check for affirmative first — user changed their mind and wants to proceed ──
            if _yes.match(inp):
                flow.state["details_confirmed"] = True
                flow.state["pending_modification"] = None
                flow.advance_step(); flow.save()
                try:
                    if user_id:
                        save_flow_to_profile(user_id, flow.state)
                except Exception as e:
                    print(f"[ERROR] Failed to save profile: {e}")
                current_language = flow.state.get("_current_language", language)
                return _build_documents_response(flow, current_language)

            # Try to extract multiple field updates from a single message
            updates_made = _extract_multiple_field_updates(flow, inp, user_input)
            
            if updates_made:
                # User provided multiple updates in one message - apply them and show confirmation
                flow.state["pending_modification"] = None
                flow.save()
                return _build_confirmation(flow)
            
            # Try single field detection
            field = _detect_modification_field(inp)
            print(f"[DEBUG PRIORITY 4] Input: {inp!r}, Detected field: {field}")
            
            if field:
                # Check if user provided the value in the same message
                # e.g. "my name is Devaprasath J" or "my mother name is nabi"
                value_extracted = False
                
                if field == "full_name":
                    # Try to extract name from the message - handle any case
                    # Pattern 1: "name is X" or "my name is X"
                    name_match = re.search(r"(?:my\s+)?(?:full\s+)?name\s+is\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)", user_input, re.IGNORECASE)
                    if not name_match:
                        # Pattern 2: "my name X" (missing "is")
                        name_match = re.search(r"(?:my\s+)?(?:full\s+)?name\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?:\s*$|\s+and\b|\s*,)", user_input, re.IGNORECASE)
                    
                    if name_match:
                        candidate = name_match.group(1).strip()
                        print(f"[DEBUG] Extracted name candidate: {candidate!r}")
                        # Split and filter out common words
                        words = candidate.split()
                        filtered_words = [w for w in words if w.lower() not in ('my', 'name', 'is', 'the', 'full')]
                        if filtered_words:
                            candidate = ' '.join(filtered_words)  # Preserve original case
                            print(f"[DEBUG] Filtered name: {candidate!r}")
                            # Validate the cleaned name
                            if _is_valid_name(candidate):
                                flow.state["full_name"] = candidate
                                flow.state["pending_modification"] = None
                                flow.save()
                                print(f"[DEBUG] ✓ Updated full_name to: {candidate!r}")
                                return _build_confirmation(flow)
                            else:
                                print(f"[DEBUG] ✗ Name validation failed for: {candidate!r}")
                        else:
                            print(f"[DEBUG] ✗ All words filtered out")
                    else:
                        print(f"[DEBUG] ✗ No name pattern matched")
                        
                elif field == "mother_name":
                    # Try to extract mother's name - handle any case
                    # Pattern 1: "my mother name is X" or "mother name is X" or "mom name is X" or "her name is X"
                    mom_match = re.search(r"(?:my\s+|her\s+|his\s+)?(?:mother|mom)(?:'?s)?\s+name\s+is\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)", user_input, re.IGNORECASE)
                    if not mom_match:
                        # Pattern 2: "her name is X" (when context is about mother)
                        mom_match = re.search(r"(?:her|his)\s+name\s+is\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)", user_input, re.IGNORECASE)
                    if not mom_match:
                        # Pattern 3: "my mother name X" (missing "is")
                        mom_match = re.search(r"(?:my\s+|her\s+|his\s+)?(?:mother|mom)(?:'?s)?\s+name\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?:\s*$|\s+and\b|\s*,)", user_input, re.IGNORECASE)
                    
                    if mom_match:
                        candidate = mom_match.group(1).strip()
                        print(f"[DEBUG] Extracted mother name candidate: {candidate!r}")
                        # Split and filter out common words
                        words = candidate.split()
                        filtered_words = [w for w in words if w.lower() not in ('my', 'her', 'his', 'their', 'mother', 'mothers', 'mom', 'moms', 'name', 'is', 'the', 'no')]
                        if filtered_words:
                            candidate = ' '.join(filtered_words)  # Preserve original case
                            print(f"[DEBUG] Filtered mother name: {candidate!r}")
                            # Validate the cleaned name
                            if _is_valid_name(candidate):
                                flow.state["mother_name"] = candidate
                                flow.state["pending_modification"] = None
                                flow.save()
                                print(f"[DEBUG] ✓ Updated mother_name to: {candidate!r}")
                                return _build_confirmation(flow)
                            else:
                                print(f"[DEBUG] ✗ Mother name validation failed for: {candidate!r}")
                        else:
                            print(f"[DEBUG] ✗ All words filtered out for mother name")
                    else:
                        # No "mother" keyword — treat the whole input as the name
                        # (agent just asked "What is your mother's name?" and user typed it directly)
                        _FILTER = {'my', 'her', 'his', 'their', 'mother', "mother's", 'mothers', 'mom', "mom's",
                                   'name', 'is', 'the', 'full', 'change', 'update', 'to', 'it', 'no'}
                        words = user_input.strip().split()
                        filtered_words = [w for w in words if w.lower() not in _FILTER]
                        if filtered_words:
                            candidate = ' '.join(filtered_words)
                            print(f"[DEBUG] Mother name bare-input candidate: {candidate!r}")
                            if _is_valid_name(candidate):
                                flow.state["mother_name"] = candidate
                                flow.state["pending_modification"] = None
                                flow.save()
                                print(f"[DEBUG] ✓ Updated mother_name (bare) to: {candidate!r}")
                                return _build_confirmation(flow)
                            else:
                                print(f"[DEBUG] ✗ Mother name validation failed for bare input: {candidate!r}")
                        else:
                            print(f"[DEBUG] ✗ No mother name pattern matched")
                        
                elif field == "email":
                    # Try to extract email
                    email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", inp)
                    if email_match:
                        flow.state["email"] = email_match.group(0).lower()
                        flow.state["email_source"] = "new"
                        flow.state["pending_modification"] = None
                        flow.save()
                        print(f"[DEBUG] ✓ Updated email")
                        return _build_confirmation(flow)
                        
                elif field == "salary":
                    result = _parse_salary(user_input)
                    if result:
                        flow.state["salary"] = result
                        flow.state["pending_modification"] = None
                        flow.save()
                        print(f"[DEBUG] ✓ Updated salary to: {result!r}")
                        return _build_confirmation(flow)
                    else:
                        print(f"[DEBUG] ✗ Salary parsing failed for: {user_input!r}")

                elif field == "grandfather_name":
                    gf_match = re.search(
                        r"(?:my\s+)?(?:grandfather|grandpa|thatha|thaatha)(?:'?s)?\s+(?:name\s+)?(?:is|to|as|:?\s*)([a-zA-Z]+(?:\s+[a-zA-Z]+)*)",
                        user_input, re.IGNORECASE,
                    )
                    if gf_match:
                        candidate = gf_match.group(1).strip()
                    else:
                        _FILTER = {'my', 'grandfather', "grandfather's", 'grandpa', 'thatha', 'thaatha',
                                   'name', 'is', 'to', 'the', 'change', 'update', 'as', 'it'}
                        candidate = ' '.join(w for w in user_input.split() if w.lower() not in _FILTER).strip()
                    if candidate and _is_valid_name(candidate):
                        flow.state["grandfather_name"] = candidate
                        flow.state["pending_modification"] = None
                        flow.save()
                        print(f"[DEBUG] ✓ Updated grandfather_name to: {candidate!r}")
                        return _build_confirmation(flow)
                    else:
                        print(f"[DEBUG] ✗ Grandfather name parsing failed for: {user_input!r}")
                
                # If value not found in message, ask for it
                print(f"[DEBUG] Value not extracted inline, asking for field: {field}")
                flow.state["pending_modification"] = field
                flow.save()
                return _ask_for_field(flow, field)
            else:
                print(f"[DEBUG] No field detected from input")
                return {
                    "answer": "I didn't catch that. Which field would you like to change? (e.g. *\"name\"*, *\"email\"*, *\"salary\"*, *\"mother's name\"*)",
                    "sources": [], "followups": [], "guided": False, "step": step,
                }

        # Fallback — re-show confirmation
        return _build_confirmation(flow)

    # ── Documents ────────────────────────────────────────────────
    elif step == "documents":
        if _is_off_topic_during_flow(inp): return None
        language = flow.state.get("_current_language", "en")
        _confirm = re.compile(r"^(yes|y|yeah|yep|yup|sure|ok|okay|ready|let'?s\s+go|proceed|go\s+ahead|upload\s+now|aam|haan)$", re.IGNORECASE)
        if _confirm.match(inp):
            upload_msg = get_template("upload_now", language)
            return {"answer": upload_msg, "sources": [], "followups": [], "guided": True, "step": step, "open_upload": True}

        # ── Field update at documents step: user corrects a detail while uploading ──
        # "ennodiya per devaprasath", "my name is Ravi", "salary 5 lakh", etc.
        updates_made = _extract_multiple_field_updates(flow, inp, user_input)
        if updates_made:
            flow.save()
            try:
                if user_id:
                    save_flow_to_profile(user_id, flow.state)
            except Exception:
                pass
            resp = _build_documents_response(flow, language)
            if language == "ta":
                resp["answer"] = "✓ விவரங்கள் புதுப்பிக்கப்பட்டன.\n\n" + resp["answer"]
            elif language == "hi":
                resp["answer"] = "✓ विवरण अपडेट किए गए।\n\n" + resp["answer"]
            else:
                resp["answer"] = "✓ Details updated.\n\n" + resp["answer"]
            return resp

        ready_msg = get_template("ready_to_upload", language)
        return _build_documents_response(flow, language) | {"answer": ready_msg + "\n\n" + _ask_for_documents(flow, language)}

    # ── PAN number ───────────────────────────────────────────────
    elif step == "pan_number":
        pan = _extract_pan(inp)
        if pan:
            flow.state["pan_number"] = pan; flow.advance_step(); flow.save()
            next_step = flow.get_current_step()
            if next_step == "aadhaar_number":
                return {"answer": f"Got your PAN — **{pan}**.\n\nNow I need your **Aadhaar number** (12 digits).", "sources": [], "followups": [], "guided": True, "step": step}
            return _ask_step(flow)
        return {"answer": "That doesn't look like a valid PAN. It's a 10-character code like **ABCDE1234F** — please check and try again.", "sources": [], "followups": [], "guided": True, "step": step}

    # ── Aadhaar number ───────────────────────────────────────────
    elif step == "aadhaar_number":
        aadhaar = _extract_aadhaar(inp)
        if aadhaar:
            flow.state["aadhaar_number"] = aadhaar; flow.advance_step(); flow.save()
            return {"answer": _generate_summary(flow), "sources": [], "followups": [], "guided": True, "step": step}
        return {"answer": "That doesn't look like a valid Aadhaar number (12 digits). Please check and try again.", "sources": [], "followups": [], "guided": True, "step": step}

    # ── Summary / complete ───────────────────────────────────────
    elif step == "summary" or flow.is_complete():
        return {"answer": _generate_summary(flow), "sources": [], "followups": [], "guided": True, "step": "summary"}

    return None


def handle_document_upload(session_id: str, filename: str, doc_type: str) -> dict:
    flow = FlowManager(session_id, "anonymous")  # TODO: pass user_id from upload endpoint
    if not flow.has_active_flow():
        return {"answer": "Document received! Let me know what PAN service you need help with.", "guided": False, "complete": False}

    flow.record_document(filename, doc_type)
    pending = flow.get_pending_docs()

    if not pending:
        return {"answer": f"**{filename}** received!\n\nThat's everything. Here's your application summary:\n\n" + _generate_summary(flow), "guided": True, "complete": True}

    next_doc = pending[0]
    options  = "\n".join([f"- {o}" for o in next_doc["options"]])
    return {"answer": f"**{filename}** uploaded!\n\nOne more — I still need your **{next_doc['label']}**.\n\nAccepted:\n{options}\n\nUpload whenever you're ready.", "guided": True, "complete": False}


# ── Helpers ──────────────────────────────────────────────────────

def _ask_for_documents(flow: FlowManager, language: str = None) -> str:
    # Get language from flow state if not provided
    if language is None:
        language = flow.state.get("_current_language", "en")
    
    pending = flow.get_pending_docs()
    if not pending:
        return get_template("all_docs_received", language)

    DOC_WHY = {
        "aadhaar":          "Used for eKYC and Aadhaar-based identity verification." if language == 'en' else 
                           "eKYC மற்றும் ஆதார் அடிப்படையிலான அடையாள சரிபார்ப்புக்கு பயன்படுத்தப்படுகிறது." if language == 'ta' else
                           "eKYC और आधार-आधारित पहचान सत्यापन के लिए उपयोग किया जाता है।",
        "driving_license":  "Accepted as proof of identity and address." if language == 'en' else
                           "அடையாளம் மற்றும் முகவரி சான்றாக ஏற்றுக்கொள்ளப்படுகிறது." if language == 'ta' else
                           "पहचान और पते के प्रमाण के रूप में स्वीकार किया जाता है।",
        "photograph":       "Printed on your physical PAN card for visual identity verification." if language == 'en' else
                           "காட்சி அடையாள சரிபார்ப்புக்காக உங்கள் உடல் PAN அட்டையில் அச்சிடப்பட்டுள்ளது." if language == 'ta' else
                           "दृश्य पहचान सत्यापन के लिए आपके भौतिक PAN कार्ड पर मुद्रित।",
        "identity_proof":   "Mandatory KYC — confirms who you are." if language == 'en' else
                           "கட்டாய KYC — நீங்கள் யார் என்பதை உறுதிப்படுத்துகிறது." if language == 'ta' else
                           "अनिवार्य KYC — आप कौन हैं इसकी पुष्टि करता है।",
        "address_proof":    "Your address is permanently recorded on the PAN database." if language == 'en' else
                           "உங்கள் முகவரி PAN தரவுத்தளத்தில் நிரந்தரமாக பதிவு செய்யப்பட்டுள்ளது." if language == 'ta' else
                           "आपका पता PAN डेटाबेस में स्थायी रूप से दर्ज है।",
        "dob_proof":        "Your date of birth is permanently linked to your PAN." if language == 'en' else
                           "உங்கள் பிறந்த தேதி உங்கள் PAN உடன் நிரந்தரமாக இணைக்கப்பட்டுள்ளது." if language == 'ta' else
                           "आपकी जन्म तिथि आपके PAN से स्थायी रूप से जुड़ी हुई है।",
        "correction_proof": "Required to verify the change and prevent fraud." if language == 'en' else
                           "மாற்றத்தை சரிபார்க்கவும் மோசடியைத் தடுக்கவும் தேவை." if language == 'ta' else
                           "परिवर्तन को सत्यापित करने और धोखाधड़ी को रोकने के लिए आवश्यक।",
    }
    
    # Document label translations
    DOC_LABELS = {
        "aadhaar": {
            "en": "Aadhaar Card",
            "ta": "ஆதார் அட்டை",
            "hi": "आधार कार्ड"
        },
        "driving_license": {
            "en": "Driving License",
            "ta": "ஓட்டுநர் உரிமம்",
            "hi": "ड्राइविंग लाइसेंस"
        },
        "photograph": {
            "en": "Applicant Photograph",
            "ta": "விண்ணப்பதாரர் புகைப்படம்",
            "hi": "आवेदक का फोटोग्राफ"
        },
        "identity_proof": {
            "en": "Proof of Identity",
            "ta": "அடையாள சான்று",
            "hi": "पहचान प्रमाण"
        },
        "address_proof": {
            "en": "Address Proof",
            "ta": "முகவரி சான்று",
            "hi": "पता प्रमाण"
        },
        "address_proof_foreign": {
            "en": "Proof of Foreign Address",
            "ta": "வெளிநாட்டு முகவரி சான்று",
            "hi": "विदेशी पते का प्रमाण"
        },
        "address_proof_india": {
            "en": "Proof of Indian Address (if any)",
            "ta": "இந்திய முகவரி சான்று (ஏதேனும் இருந்தால்)",
            "hi": "भारतीय पते का प्रमाण (यदि कोई हो)"
        },
        "dob_proof": {
            "en": "Date of Birth Proof",
            "ta": "பிறந்த தேதி சான்று",
            "hi": "जन्म तिथि प्रमाण"
        },
        "correction_proof": {
            "en": "Proof supporting correction",
            "ta": "திருத்தத்தை ஆதரிக்கும் சான்று",
            "hi": "सुधार का समर्थन करने वाला प्रमाण"
        }
    }

    lines = [get_template("documents_needed", language) + "\n"]
    for i, doc in enumerate(pending, 1):
        optional_text = f" *({get_template('optional', language)})*" if doc.get("optional") else ""
        options  = ", ".join(doc["options"])
        why      = DOC_WHY.get(doc["key"], "Required for your PAN application." if language == 'en' else 
                              "உங்கள் PAN விண்ணப்பத்திற்கு தேவை." if language == 'ta' else
                              "आपके PAN आवेदन के लिए आवश्यक।")
        
        # Translate document label
        doc_key = doc.get('key', '')
        if doc_key in DOC_LABELS and language in DOC_LABELS[doc_key]:
            doc_label = DOC_LABELS[doc_key][language]
        else:
            doc_label = doc.get('label', doc_key.replace('_', ' ').title())
        
        lines.append(f"### {i}. {doc_label}{optional_text}")
        lines.append(f"> {why}")
        accepted_label = get_template("accepted", language) if language != 'en' else "Accepted"
        lines.append(f"{accepted_label}: {options}\n")

    lines.append("---")
    lines.append(get_template("ready_to_upload", language))
    return "\n".join(lines)


def _generate_summary(flow: FlowManager) -> str:
    service   = get_service(flow.state["service_id"])
    collected = flow.get_collected_docs()

    lines = [
        "Here's a summary of your application:\n",
        f"**Service:** {service['name']}",
        f"**Form:** {service['form']}",
    ]
    if flow.state.get("applicant_type"):
        lines.append(f"**Applicant type:** {flow.state['applicant_type'].replace('_', ' ').title()}")
    if flow.state.get("submission_mode"):
        lines.append(f"**Submission mode:** {flow.state['submission_mode']}")
    if flow.state.get("delivery_mode"):
        label = "Physical + e-PAN" if flow.state["delivery_mode"] == "physical_and_soft" else "e-PAN only"
        lines.append(f"**PAN delivery:** {label}")
    if flow.state.get("aadhaar_photo") is not None:
        lines.append(f"**Aadhaar photo on PAN:** {'Yes' if flow.state['aadhaar_photo'] else 'No'}")
    if flow.state.get("source_of_income"):
        lines.append(f"**Source of income:** {flow.state['source_of_income']}")
    if flow.state.get("address_for_comm"):
        lines.append(f"**Address for communication:** {flow.state['address_for_comm']}")
    if flow.state.get("residential_status"):
        lines.append(f"**Residential status:** {flow.state['residential_status']}")
    if flow.state.get("rep_assessee") is not None:
        lines.append(f"**Representative Assessee:** {'Yes' if flow.state['rep_assessee'] else 'No'}")
    if flow.state.get("full_name"):
        lines.append(f"**Full name (as in Aadhaar):** {flow.state['full_name']}")
    if flow.state.get("grandfather_name"):
        lines.append(f"**Grandfather's name:** {flow.state['grandfather_name']}")
    if flow.state.get("mother_name"):
        lines.append(f"**Mother's name:** {flow.state['mother_name']}")
    if flow.state.get("email"):
        lines.append(f"**Email:** {flow.state['email']}")
    if flow.state.get("salary"):
        lines.append(f"**Annual income:** {flow.state['salary']}")
    if flow.state.get("pan_number"):
        lines.append(f"**PAN:** {flow.state['pan_number']}")
    if flow.state.get("aadhaar_number"):
        lines.append(f"**Aadhaar:** {flow.state['aadhaar_number']}")
    if collected:
        lines.append(f"\n**Documents ({len(collected)}):**")
        for doc in collected:
            lines.append(f"- {doc['filename']} ({doc['doc_type']})")

    lines.append("\nYou're all set! Our team will review your documents and proceed with the application.")
    return "\n".join(lines)


# ── Details collection helpers ────────────────────────────────────

def _missing_details(flow: FlowManager) -> list[str]:
    """Return list of field keys that are still missing."""
    missing = []
    if not flow.state.get("full_name"):
        missing.append("full_name")
    if not flow.state.get("grandfather_name"):
        missing.append("grandfather_name")
    if not flow.state.get("mother_name"):
        missing.append("mother_name")
    if not flow.state.get("email"):
        missing.append("email")
    if not flow.state.get("salary"):
        missing.append("salary")
    return missing


def _ask_details_collection(flow: FlowManager, language: str = None) -> dict:
    """Build the prompt asking for whichever details are still missing."""
    missing = _missing_details(flow)
    state   = flow.state
    # Resolve language from argument → flow state → default en
    if language is None:
        language = state.get("_current_language", "en")
    ta = language == "ta"
    hi = language == "hi"

    # ── Email confirmation sub-step ───────────────────────────────
    account_email = state.get("_account_email")
    if "email" in missing and account_email and not state.get("_email_confirm_asked"):
        state["_email_confirm_asked"] = True
        flow.save()
        if ta:
            q = "**PAN கடிதப் பரிமாற்றத்திற்கான மின்னஞ்சல்** — உங்கள் கணக்கு மின்னஞ்சலை பயன்படுத்தலாமா?"
            yes_lbl = f"ஆம், {account_email} பயன்படுத்து"
            no_lbl  = "இல்லை, வேறு மின்னஞ்சல் பயன்படுத்துகிறேன்"
        elif hi:
            q = "**PAN पत्राचार के लिए ईमेल** — क्या मैं आपका खाता ईमेल उपयोग करूँ?"
            yes_lbl = f"हाँ, {account_email} उपयोग करें"
            no_lbl  = "नहीं, अलग ईमेल उपयोग करूँगा"
        else:
            q = "**Email for PAN correspondence** — should I use your account email?"
            yes_lbl = f"Yes, use {account_email}"
            no_lbl  = "No, use a different one"
        opts = {
            "type": "email_confirm",
            "account_email": account_email,
            "choices": [yes_lbl, no_lbl],
        }
        return {
            "answer": q,
            "sources": [], "followups": [], "guided": True,
            "step": "details_collection", "options": opts,
        }

    # ── Collected status block ────────────────────────────────────
    collected_lines = []
    if ta:
        if state.get("full_name"):
            collected_lines.append(f"✅ **முழு பெயர்:** {state['full_name']}")
        if state.get("grandfather_name"):
            collected_lines.append(f"✅ **தாத்தாவின் பெயர்:** {state['grandfather_name']}")
        if state.get("mother_name"):
            collected_lines.append(f"✅ **தாயின் பெயர்:** {state['mother_name']}")
        if state.get("email"):
            collected_lines.append(f"✅ **மின்னஞ்சல்:** {state['email']}")
        if state.get("salary"):
            collected_lines.append(f"✅ **ஆண்டு வருமானம்:** {state['salary']}")
    elif hi:
        if state.get("full_name"):
            collected_lines.append(f"✅ **पूरा नाम:** {state['full_name']}")
        if state.get("grandfather_name"):
            collected_lines.append(f"✅ **दादा का नाम:** {state['grandfather_name']}")
        if state.get("mother_name"):
            collected_lines.append(f"✅ **माँ का नाम:** {state['mother_name']}")
        if state.get("email"):
            collected_lines.append(f"✅ **ईमेल:** {state['email']}")
        if state.get("salary"):
            collected_lines.append(f"✅ **वार्षिक आय:** {state['salary']}")
    else:
        if state.get("full_name"):
            collected_lines.append(f"✅ **Full name:** {state['full_name']}")
        if state.get("grandfather_name"):
            collected_lines.append(f"✅ **Grandfather's name:** {state['grandfather_name']}")
        if state.get("mother_name"):
            collected_lines.append(f"✅ **Mother's name:** {state['mother_name']}")
        if state.get("email"):
            collected_lines.append(f"✅ **Email:** {state['email']}")
        if state.get("salary"):
            collected_lines.append(f"✅ **Annual income:** {state['salary']}")

    collected_block = ("\n".join(collected_lines) + "\n\n") if collected_lines else ""

    # ── Ask for missing fields ────────────────────────────────────
    ask_parts = []
    if ta:
        if "full_name" in missing:
            ask_parts.append("- **முழு பெயர்** — ஆதார் அட்டையில் உள்ளபடி சரியாக")
        if "grandfather_name" in missing:
            ask_parts.append("- **தாத்தாவின் முழு பெயர்** (அதிகாரப்பூர்வ பதிவுகளின்படி)")
        if "mother_name" in missing:
            ask_parts.append("- **தாயின் முழு பெயர்** (அதிகாரப்பூர்வ பதிவுகளின்படி)")
        if "email" in missing:
            ask_parts.append("- **மின்னஞ்சல் முகவரி** — PAN கடிதப் பரிமாற்றத்திற்காக")
        if "salary" in missing:
            ask_parts.append("- **ஆண்டு வருமானம் / சம்பளம்** (மாதாந்திர அல்ல — எ.கா. ₹5,00,000 அல்லது 500000)")
    elif hi:
        if "full_name" in missing:
            ask_parts.append("- **पूरा नाम** — आधार कार्ड पर जैसा है ठीक वैसा")
        if "grandfather_name" in missing:
            ask_parts.append("- **दादा का पूरा नाम** (आधिकारिक रिकॉर्ड के अनुसार)")
        if "mother_name" in missing:
            ask_parts.append("- **माँ का पूरा नाम** (आधिकारिक रिकॉर्ड के अनुसार)")
        if "email" in missing:
            ask_parts.append("- **ईमेल पता** — PAN पत्राचार के लिए")
        if "salary" in missing:
            ask_parts.append("- **वार्षिक आय / वेतन** (प्रति वर्ष, मासिक नहीं — जैसे ₹5,00,000)")
    else:
        if "full_name" in missing:
            ask_parts.append("- **Full name** exactly as it appears on your Aadhaar card")
        if "grandfather_name" in missing:
            ask_parts.append("- **Grandfather's full name** (as per official records)")
        if "mother_name" in missing:
            ask_parts.append("- **Mother's full name** (as per official records)")
        if "email" in missing:
            ask_parts.append("- **Email address** for PAN correspondence")
        if "salary" in missing:
            ask_parts.append("- **Annual income / salary** (per year, not monthly — e.g. ₹5,00,000 or 500000)")

    # ── Assemble answer ───────────────────────────────────────────
    if not ask_parts:
        if ta:
            answer = f"{collected_block}அருமை! என்னிடம் தேவையான அனைத்து விவரங்களும் உள்ளன.\n\nஉறுதிப்படுத்தல் காட்டுகிறேன்..."
        elif hi:
            answer = f"{collected_block}बढ़िया! मेरे पास सभी आवश्यक विवरण हैं।\n\nपुष्टि दिखा रहा हूँ..."
        else:
            answer = f"{collected_block}Perfect! I have all the details I need.\n\nLet me show you the confirmation..."
    elif collected_lines:
        ask_block = "\n".join(ask_parts)
        if ta:
            answer = f"{collected_block}கிட்டத்தட்ட முடிந்தது! இன்னும் தேவை:\n\n{ask_block}"
        elif hi:
            answer = f"{collected_block}लगभग हो गया! अभी चाहिए:\n\n{ask_block}"
        else:
            answer = f"{collected_block}Almost there! I still need:\n\n{ask_block}"
    else:
        ask_block = "\n".join(ask_parts)
        if ta:
            answer = f"சரி! இப்போது உங்கள் விண்ணப்பத்தை நிரப்ப சில தனிப்பட்ட விவரங்கள் தேவை.\n\nதயவுசெய்து தரவும்:\n\n{ask_block}"
        elif hi:
            answer = f"बढ़िया! अब आपके आवेदन को भरने के लिए कुछ व्यक्तिगत विवरण चाहिए।\n\nकृपया बताएं:\n\n{ask_block}"
        else:
            answer = f"Great! Now I need a few personal details to fill in your application.\n\nPlease provide:\n\n{ask_block}"

    return {
        "answer": answer,
        "sources": [], "followups": [], "guided": True, "step": "details_collection",
    }


def _extract_multiple_field_updates(flow: FlowManager, inp: str, raw: str) -> bool:
    """
    Extract multiple field updates from a single message.
    Handles inputs like:
      "change my name to John and mother name to Mary and salary to 5 lakh"
      "name to Ravi and email to ravi@gmail.com"
      "name Ravi, salary 5 lakh"
    Returns True if at least one field was updated.
    """
    updated = False
    text = raw.strip()
    lower = text.lower()

    print(f"[DEBUG _extract_multiple_field_updates] Input: {text!r}")

    # ── Extract full name ─────────────────────────────────────────
    # Flexible: "name to/is/as X", "change name X", "my name X"
    # CRITICAL: Must NOT match "mother name"
    name_patterns = [
        # "... name to/is/as <value>" — preceded by optional "full", but NOT "mother/mom"
        r"(?<!\bmother\s)(?<!\bmom\s)(?<!\bmother's\s)(?<!\bmom's\s)"
        r"(?:my\s+)?(?:full\s+)?name\s+(?:to|is|as|:)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        r"(?:change|update|correct)\s+(?:my\s+)?(?:full\s+)?name\s+(?:to\s+|as\s+|:?\s*)?([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        # Tanglish: "ennodiya per deva" / "en per ravi" / "naan per kumar"
        r"(?:ennoda|ennodiya|en|naan|naanu)\s+(?:peyar|per)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s*,|\s+amma\b|\s+salary\b|\s+sambalam\b|\s*$)",
    ]
    for pattern in name_patterns:
        name_match = re.search(pattern, text, re.IGNORECASE)
        if name_match:
            match_start = name_match.start()
            preceding_text = text[:match_start].lower()
            if re.search(r'\b(mother|mom|mum|maa|amma)\b', preceding_text[-20:] if len(preceding_text) > 20 else preceding_text):
                print(f"[DEBUG] Skipping full_name match - detected mother/mom keyword before it")
                continue
            candidate = name_match.group(1).strip()
            words = candidate.split()
            filtered_words = [w for w in words if w.lower() not in ('my', 'name', 'is', 'to', 'the', 'full', 'and', 'per', 'peyar')]
            if filtered_words:
                candidate = ' '.join(filtered_words)
                if _is_valid_name(candidate):
                    flow.state["full_name"] = candidate
                    updated = True
                    print(f"[DEBUG] ✓ Updated full_name to: {candidate!r}")
                    break

    # ── Extract mother's name ─────────────────────────────────────
    mother_patterns = [
        r"(?:my\s+)?(?:mother|mom|mum|maa|amma)(?:'?s)?\s+name\s+(?:to|is|as|:)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        r"(?:change|update|correct)\s+(?:my\s+)?(?:mother|mom|mum)(?:'?s)?\s+name\s+(?:to\s+|as\s+|:?\s*)?([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        # bare: "mother name Sunitha" or "mother Sunitha" or "mother as Sunitha"
        r"(?:mother|mom|mum)(?:'?s)?\s+(?:name\s+)?(?:to\s+|is\s+|as\s+|:?\s*)([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        # Tanglish: "amma per nabina" / "thaayin per meena" / "amma peyar priya"
        r"(?:amma|thaayin|thaay|ammaa)\s+(?:peyar|per)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s*,|\s+salary\b|\s+sambalam\b|\s*$)",
    ]
    for pattern in mother_patterns:
        mom_match = re.search(pattern, text, re.IGNORECASE)
        if mom_match:
            candidate = mom_match.group(1).strip()
            words = candidate.split()
            filtered_words = [w for w in words if w.lower() not in ('my', 'mother', 'mom', 'name', 'is', 'to', 'the', 'and', 'per', 'peyar', 'amma', 'thaayin')]
            if filtered_words:
                candidate = ' '.join(filtered_words)
                if _is_valid_name(candidate):
                    flow.state["mother_name"] = candidate
                    updated = True
                    print(f"[DEBUG] ✓ Updated mother_name to: {candidate!r}")
                    break

    # ── Extract grandfather's name ────────────────────────────────
    grandfather_patterns = [
        r"(?:my\s+)?(?:grandfather|grandpa|grand\s*father|thatha|thaatha|thathaa|paati|nana)(?:'?s)?\s+name\s+(?:to|is|as|:)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        r"(?:change|update|correct)\s+(?:my\s+)?(?:grandfather|grandpa|thatha|thaatha)(?:'?s)?\s+name\s+(?:to\s+|as\s+|:?\s*)?([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        # bare: "grandfather name Rajan" / "grandfather Rajan"
        r"(?:grandfather|grandpa|thatha|thaatha)(?:'?s)?\s+(?:name\s+)?(?:to\s+|is\s+|as\s+|:?\s*)([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        # Tanglish: "thatha per rajan" / "thatha peyar murugan"
        r"(?:thatha|thaatha|thaathaa)\s+(?:peyar|per)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s*,|\s+salary\b|\s*$)",
    ]
    for pattern in grandfather_patterns:
        gf_match = re.search(pattern, text, re.IGNORECASE)
        if gf_match:
            candidate = gf_match.group(1).strip()
            words = candidate.split()
            filtered_words = [w for w in words if w.lower() not in ('my', 'grandfather', 'grandpa', 'thatha', 'thaatha', 'name', 'is', 'to', 'the', 'and', 'per', 'peyar')]
            if filtered_words:
                candidate = ' '.join(filtered_words)
                if _is_valid_name(candidate):
                    flow.state["grandfather_name"] = candidate
                    updated = True
                    print(f"[DEBUG] ✓ Updated grandfather_name to: {candidate!r}")
                    break
    email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        flow.state["email"] = email_match.group(0).lower()
        flow.state["email_source"] = "new"
        updated = True
        print(f"[DEBUG] ✓ Updated email to: {flow.state['email']!r}")

    # ── Extract salary ────────────────────────────────────────────
    salary_result = _parse_salary(text)
    if salary_result:
        flow.state["salary"] = salary_result
        updated = True
        print(f"[DEBUG] ✓ Updated salary to: {salary_result!r}")

    # ── Extract submission mode ───────────────────────────────────
    _SUBMISSION_MAP = {
        "aadhaar": "Aadhaar-based Online (eKYC)",
        "ekyc": "Aadhaar-based Online (eKYC)",
        "online": "Aadhaar-based Online (eKYC)",
        "ekc": "Aadhaar-based Online (eKYC)",
        "upload": "Upload scanned docs & eSign",
        "scan": "Upload scanned docs & eSign",
        "esign": "Upload scanned docs & eSign",
        "scanned": "Upload scanned docs & eSign",
        "courier": "Fill online + courier physical form",
        "physical form": "Fill online + courier physical form",
        "post": "Fill online + courier physical form",
        "speed post": "Fill online + courier physical form",
    }
    # Match: "submission mode to/is/: aadhaar" or "change submission to ekyc"
    _sub_m = re.search(
        r"(?:submission\s+mode?|submit\s+mode?|how\s+to\s+submit)\s*(?:to|is|as|:|-|→)?\s*([a-zA-Z\s]+?)(?:\s+and\b|\s*,|\s*$)",
        text, re.IGNORECASE
    )
    if _sub_m:
        kw = _sub_m.group(1).strip().lower()
        matched_mode = next((v for k, v in _SUBMISSION_MAP.items() if k in kw), None)
        if matched_mode:
            flow.state["submission_mode"] = matched_mode
            updated = True
            print(f"[DEBUG] ✓ Updated submission_mode to: {matched_mode!r}")
    # Also match bare keyword after "change/update" near submission context
    if not flow.state.get("submission_mode") or not updated:
        for kw, mode in _SUBMISSION_MAP.items():
            if re.search(rf"\b{re.escape(kw)}\b", lower):
                if re.search(r"\b(submission|submit|mode)\b", lower):
                    flow.state["submission_mode"] = mode
                    updated = True
                    print(f"[DEBUG] ✓ Updated submission_mode (keyword) to: {mode!r}")
                    break

    # ── Extract delivery mode ─────────────────────────────────────
    if re.search(r"(?:delivery|pan\s+delivery)\s*(?:to|is|as|:)?\s*(?:physical|both|hard|home)", text, re.IGNORECASE):
        flow.state["delivery_mode"] = "physical_and_soft"
        updated = True
        print(f"[DEBUG] ✓ Updated delivery_mode to: physical_and_soft")
    elif re.search(r"(?:delivery|pan\s+delivery)\s*(?:to|is|as|:)?\s*(?:soft|email|digital|e-?pan|only)", text, re.IGNORECASE):
        flow.state["delivery_mode"] = "soft_only"
        updated = True
        print(f"[DEBUG] ✓ Updated delivery_mode to: soft_only")

    # ── Extract aadhaar photo ─────────────────────────────────────
    _aadhar_photo_ctx = re.search(r"\b(aa?dh?a+r\s+photo|photo\s+on\s+pan|photo\s+consent)\b", lower)
    if _aadhar_photo_ctx:
        if re.search(r"\b(yes|agree|consent|allow|ok|okay)\b", lower):
            flow.state["aadhaar_photo"] = True
            updated = True
            print(f"[DEBUG] ✓ Updated aadhaar_photo to: True")
        elif re.search(r"\b(no|decline|disagree|don'?t|not)\b", lower):
            flow.state["aadhaar_photo"] = False
            updated = True
            print(f"[DEBUG] ✓ Updated aadhaar_photo to: False")

    # ── Extract source of income ─────────────────────────────────
    _SOI_CONTEXT = re.search(r"\b(source\s+of\s+income|income\s+source|income\s+type)\b", lower)
    if _SOI_CONTEXT:
        _SOI_MAP = [
            (re.compile(r"\b(salary|salaried)\b", re.IGNORECASE), "Salary"),
            (re.compile(r"\b(business|profession|self.?employed|freelanc)\b", re.IGNORECASE), "Income from Business / Profession"),
            (re.compile(r"\b(house\s+property|rental|rent)\b", re.IGNORECASE), "Income from House property"),
            (re.compile(r"\b(other\s+source|other)\b", re.IGNORECASE), "Income from Other sources"),
            (re.compile(r"\b(capital\s+gain)\b", re.IGNORECASE), "Capital Gains"),
            (re.compile(r"\b(no\s+income|unemployed|student|homemaker)\b", re.IGNORECASE), "No income"),
        ]
        matched_soi = [label for pat, label in _SOI_MAP if pat.search(text)]
        if matched_soi:
            flow.state["source_of_income"] = ", ".join(matched_soi)
            updated = True
            print(f"[DEBUG] ✓ Updated source_of_income to: {flow.state['source_of_income']!r}")

    # ── Extract address for communication ────────────────────────
    _ADDR_CONTEXT = re.search(r"\b(address\s+for\s+comm(unication)?|communication\s+address)\b", lower)
    if _ADDR_CONTEXT:
        if re.search(r"\b(residence|home|residential)\b", lower):
            flow.state["address_for_comm"] = "Residence"
            updated = True
            print(f"[DEBUG] ✓ Updated address_for_comm to: Residence")
        elif re.search(r"\b(office|work|workplace)\b", lower):
            flow.state["address_for_comm"] = "Office"
            updated = True
            print(f"[DEBUG] ✓ Updated address_for_comm to: Office")
        elif re.search(r"\b(representative|ra\b|assessee)\b", lower):
            flow.state["address_for_comm"] = "Representative Assessee (RA)"
            updated = True
            print(f"[DEBUG] ✓ Updated address_for_comm to: Representative Assessee (RA)")

    # ── Extract residential status ───────────────────────────────
    _RES_CONTEXT = re.search(r"\b(residential\s+status|residency|resident\s+status)\b", lower)
    if _RES_CONTEXT:
        if re.search(r"\b(non.?resident|nri)\b", lower):
            flow.state["residential_status"] = "Non-resident"
            updated = True
            print(f"[DEBUG] ✓ Updated residential_status to: Non-resident")
        elif re.search(r"\b(rnor|not\s+ordinarily)\b", lower):
            flow.state["residential_status"] = "Resident but not ordinarily resident"
            updated = True
            print(f"[DEBUG] ✓ Updated residential_status to: RNOR")
        elif re.search(r"\bresident\b", lower):
            flow.state["residential_status"] = "Resident"
            updated = True
            print(f"[DEBUG] ✓ Updated residential_status to: Resident")

    # ── Extract representative assessee ─────────────────────────
    _RA_CONTEXT = re.search(r"\b(representative\s+assessee|rep\s+assessee)\b", lower)
    if _RA_CONTEXT:
        if re.search(r"\b(yes|yeah|yep|true|appoint|need)\b", lower):
            flow.state["rep_assessee"] = True
            updated = True
            print(f"[DEBUG] ✓ Updated rep_assessee to: True")
        elif re.search(r"\b(no|nope|nah|false|not)\b", lower):
            flow.state["rep_assessee"] = False
            updated = True
            print(f"[DEBUG] ✓ Updated rep_assessee to: False")

    print(f"[DEBUG _extract_multiple_field_updates] Updated: {updated}")

    # ── Positional fallback for ordered bare lists ────────────────────────────
    # e.g. "deva, govindhan, nabina, 3 lakhs" when asked for:
    #   Full name / Grandfather's name / Mother's name / Annual income
    # Only fires when the input has multiple comma/and segments and none of the
    # keyword-based patterns above matched the name fields.
    if not flow.state.get("full_name") or not flow.state.get("grandfather_name") or not flow.state.get("mother_name"):
        # Re-segment the raw input
        _raw_segs_and = re.split(r'\s+and\s+', raw.strip(), flags=re.IGNORECASE)
        _raw_segs = []
        for part in _raw_segs_and:
            sub = re.split(r'(?<!\d),(?!\d{2,3}(?:,|\b))', part)
            _raw_segs.extend(s.strip() for s in sub if s.strip())

        if len(_raw_segs) >= 2:
            _FIELD_ORDER = ["full_name", "grandfather_name", "mother_name", "email", "salary"]
            _missing_fields = [f for f in _FIELD_ORDER if not flow.state.get(f)
                               and (f != "email" or not flow.state.get("email"))
                               and (f != "salary" or not flow.state.get("salary"))]

            # Only use segments that look like plain names or salary values
            # (no field-keyword prefix like "name is", "mother name", etc.)
            _KW_PREFIX_RE = re.compile(
                r"^(?:my\s+)?(?:full\s+)?(?:name|mother|mom|grandfather|grandpa|thatha|"
                r"email|salary|income|per|peru)\b",
                re.IGNORECASE
            )
            plain_segs = [s for s in _raw_segs if not _KW_PREFIX_RE.match(s)]

            if len(plain_segs) >= 2 and _missing_fields:
                print(f"[DEBUG _extract_multiple] Positional fallback: missing={_missing_fields}, segs={plain_segs}")
                for i, field in enumerate(_missing_fields):
                    if i >= len(plain_segs):
                        break
                    seg = plain_segs[i].strip()
                    if not seg:
                        continue
                    if field == "salary":
                        result = _parse_salary(seg)
                        if result:
                            flow.state["salary"] = result
                            updated = True
                            print(f"[DEBUG _extract_multiple] ✓ salary (positional) = {result!r}")
                    elif field == "email":
                        em = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", seg)
                        if em:
                            flow.state["email"] = em.group(0).lower()
                            flow.state["email_source"] = "new"
                            updated = True
                            print(f"[DEBUG _extract_multiple] ✓ email (positional) = {flow.state['email']!r}")
                    else:
                        # Clean stop words from the segment
                        _STOPS = {'my', 'name', 'is', 'full', 'the', 'a', 'an', 'and',
                                  'mother', 'mom', 'grandfather', 'grandpa', 'thatha',
                                  'salary', 'income', 'email', 'per', 'peru', 'peyar'}
                        words = [w for w in seg.split() if w.lower() not in _STOPS]
                        candidate = ' '.join(words).strip()
                        if candidate and _is_valid_name(candidate) and not _is_keyword(candidate):
                            flow.state[field] = candidate
                            updated = True
                            print(f"[DEBUG _extract_multiple] ✓ {field} (positional) = {candidate!r}")

    return updated


def _extract_details(flow: FlowManager, inp: str, raw: str) -> bool:
    """
    Extract personal details from free-text input.
    Handles multi-fact messages like:
      "my name is deva and mother name is Nabina J and salary is 6 lakhs"
    Returns True if at least one field was updated.
    """
    updated = False
    text = raw.strip()

    print(f"[DEBUG _extract_details] Input: {text!r}")
    print(f"[DEBUG _extract_details] State before: full_name={flow.state.get('full_name')!r}, "
          f"mother_name={flow.state.get('mother_name')!r}, salary={flow.state.get('salary')!r}, "
          f"email={flow.state.get('email')!r}")

    # ── Step 1: Normalise common typos ───────────────────────────
    _KW_TYPOS = [
        (r'\bnaem\b',   'name'),   (r'\bnme\b',    'name'),   (r'\bnam\b',    'name'),
        (r'\bmothre\b', 'mother'), (r'\bmoter\b',  'mother'), (r'\bmothr\b',  'mother'),
        (r'\bmuther\b', 'mother'), (r'\bamma\b',   'mother'), (r'\bmaa\b',    'mother'),
        (r'\bemali\b',  'email'),  (r'\beamil\b',  'email'),
        (r'\bslary\b',  'salary'), (r'\bsalry\b',  'salary'),
        (r'\bincme\b',  'income'), (r'\bincoe\b',  'income'),
        (r'\blaksh\b',  'lakh'),   (r'\blaks\b',   'lakh'),
        (r'\blakhs\b',  'lakh'),   (r'\blaakh\b',  'lakh'),
        (r'\blac\b',    'lakh'),   (r'\blacs\b',   'lakh'),
        (r'\blkahs\b',  'lakh'),   (r'\blkah\b',   'lakh'),    # Common typos
        (r'\blkhs\b',   'lakh'),   (r'\blahks\b',  'lakh'),
        (r'\blahk\b',   'lakh'),   (r'\blakss\b',  'lakh'),
        # Romanized Tamil numbers
        (r'\bonnu\b',   '1'),      (r'\boṉṉu\b',   '1'),
        (r'\brendu\b',  '2'),      (r'\breṇṭu\b',  '2'),
        (r'\bmoonu\b',  '3'),      (r'\bmūṉṟu\b',  '3'),
        (r'\bnaalu\b',  '4'),      (r'\bnāṉku\b',  '4'),
        (r'\banju\b',   '5'),      (r'\baintu\b',  '5'),      (r'\bainthu\b', '5'),
        (r'\baaru\b',   '6'),      (r'\bāṟu\b',    '6'),
        (r'\bezu\b',    '7'),      (r'\belu\b',    '7'),      (r'\bēḻu\b',    '7'),
        (r'\bettu\b',   '8'),      (r'\beṭṭu\b',   '8'),
        (r'\bombodu\b', '9'),      (r'\bonpathu\b','9'),      (r'\bonbathu\b','9'),
        (r'\bpathu\b',  '10'),     (r'\bpatthu\b', '10'),     (r'\bpattu\b',  '10'),
        # Romanized Tamil "lakh" variations
        (r'\blatcham\b',    'lakh'), (r'\blaksham\b',   'lakh'),
        (r'\blacham\b',     'lakh'), (r'\blakṣam\b',    'lakh'),
        # Romanized Tamil "crore/kodi" variations — கோடி
        (r'\bkodis?\b',     'crore'), (r'\bkodi\b',     'crore'),
        (r'\bkoodi\b',      'crore'), (r'\bkoday\b',    'crore'),
        (r'\bkotis?\b',     'crore'), (r'\bkoti\b',     'crore'),
        # Romanized Tamil keywords
        (r'\bperu\b',       'name'),     (r'\bpeeru\b',     'name'),
        (r'\bvanthu\b',     'is'),       (r'\bvandu\b',     'is'),
        (r'\bennodiya\b',   'my'),       (r'\bennode\b',    'my'),
        (r'\bennoda\b',     'my'),
        (r'\bsambalam\b',   'salary'),   (r'\bsambhalam\b', 'salary'),
    ]
    for pat, repl in _KW_TYPOS:
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)

    print(f"[DEBUG _extract_details] After normalisation: {text!r}")

    # ── Step 2: Segment the message into labelled parts ──────────
    # Split on "and" / "," — but NOT on commas inside numbers (e.g. 5,00,000).
    # Strategy: split on "and" first, then split on commas only when NOT between digits.
    segments_raw = re.split(r'\s+and\s+', text, flags=re.IGNORECASE)
    segments = []
    for part in segments_raw:
        # Split on commas that are NOT between digits (avoids splitting 5,00,000)
        sub = re.split(r'(?<!\d),(?!\d{2,3}(?:,|\b))', part)
        segments.extend(s.strip() for s in sub if s.strip())
    print(f"[DEBUG _extract_details] Segments: {segments}")

    # ── Helper: clean a name candidate ───────────────────────────
    _STOP_WORDS = {
        'my', 'name', 'is', 'the', 'full', 'and', 'a', 'an', 'her', 'his', 'their', 'no',
        'mother', 'mothers', 'mom', 'moms', 'maa', 'amma',
        'grandfather', 'grandpa', 'thatha', 'thaatha',
        'salary', 'income', 'email', 'mail', 'annual', 'per', 'year',
        # Romanized Tamil stop words
        'peru', 'peeru', 'ennodiya', 'ennode', 'ennoda', 'vanthu', 'vandu',
    }

    def _clean_name(raw_name: str) -> str:
        words = raw_name.strip().split()
        kept = [w for w in words if w.lower() not in _STOP_WORDS]
        return ' '.join(kept).strip()

    # ── Step 3: Extract mother's name FIRST (higher specificity) ─
    if not flow.state.get("mother_name"):
        for seg in segments:
            # Patterns: "mother name is X", "mother's name X", "mom name X", "her name is X"
            # Also handle romanized Tamil: "amma per X", "amma peru X"
            # NOTE: "amma" is normalised to "mother" in Step 1, so match both
            m = re.match(
                r"(?:my\s+|her\s+|his\s+|their\s+)?(?:mother(?:'?s)?|mom(?:'?s)?|maa|amma)\s+(?:full\s+)?(?:name|per|peru)\s*(?:is\s*)?[:\-]?\s*(.+)",
                seg, re.IGNORECASE
            )
            if not m:
                # Also catch: "her name is X" (when context is about mother)
                m = re.match(
                    r"(?:her|his|their)\s+(?:name|per|peru)\s*(?:is\s*)?[:\-]?\s*(.+)",
                    seg, re.IGNORECASE
                )
            if not m:
                # Also catch: "mother X Y" (no "name" keyword)
                m = re.match(
                    r"(?:my\s+|her\s+|his\s+)?(?:mother(?:'?s)?|mom(?:'?s)?|amma)\s+(?!name|per|peru\b)(.+)",
                    seg, re.IGNORECASE
                )
            if m:
                candidate = _clean_name(m.group(1))
                print(f"[DEBUG _extract_details] Mother candidate from segment {seg!r}: {candidate!r}")
                if candidate and _is_valid_name(candidate):
                    flow.state["mother_name"] = candidate
                    updated = True
                    print(f"[DEBUG _extract_details] ✓ mother_name = {candidate!r}")
                    break

        # ── Step 3b: Bare-name fallback when agent specifically asked for mother name ──
        # If full_name is already set but mother_name is still missing, and the entire
        # input looks like a plain name (no salary/email/other keywords), treat it as
        # the mother's name — the agent just asked "Please provide your mother's full name".
        if not flow.state.get("mother_name") and flow.state.get("full_name"):
            _has_other_keywords = re.search(
                r'\b(salary|income|earn|email|mail|₹|rs\.?|inr|name\b|full\b)\b',
                text, re.IGNORECASE
            )
            if not _has_other_keywords:
                # The whole input is likely just the mother's name
                candidate = _clean_name(text)
                print(f"[DEBUG _extract_details] Mother bare-name fallback candidate: {candidate!r}")
                if candidate and _is_valid_name(candidate) and not _is_keyword(candidate):
                    flow.state["mother_name"] = candidate
                    updated = True
                    print(f"[DEBUG _extract_details] ✓ mother_name (bare fallback) = {candidate!r}")

    # ── Step 3c: Extract grandfather's name ──────────────────────
    if not flow.state.get("grandfather_name"):
        for seg in segments:
            m = re.match(
                r"(?:my\s+)?(?:grandfather(?:'?s)?|grandpa(?:'?s)?|thatha|thaatha)(?:'?s)?\s+(?:full\s+)?(?:name|per|peru)\s*(?:is\s*)?[:\-]?\s*(.+)",
                seg, re.IGNORECASE
            )
            if not m:
                # "grandfather X Y" with no "name" keyword
                m = re.match(
                    r"(?:my\s+)?(?:grandfather(?:'?s)?|grandpa(?:'?s)?|thatha|thaatha)\s+(?!name|per|peru\b)(.+)",
                    seg, re.IGNORECASE
                )
            if m:
                candidate = _clean_name(m.group(1))
                if candidate and _is_valid_name(candidate):
                    flow.state["grandfather_name"] = candidate
                    updated = True
                    print(f"[DEBUG _extract_details] ✓ grandfather_name = {candidate!r}")
                    break

    # ── Step 4: Extract full name ─────────────────────────────────
    if not flow.state.get("full_name"):
        for seg in segments:
            # Skip segments that are about mother or grandfather
            if re.search(r'\b(mother|mom|maa|amma|grandfather|grandpa|thatha|thaatha)\b', seg, re.IGNORECASE):
                continue
            # Skip segments that are about salary/income/email
            if re.search(r'\b(salary|income|earn|email|mail|₹|rs\.?|inr)\b', seg, re.IGNORECASE):
                continue

            # Pattern: "my name is X" / "name is X" / "name: X"
            # Also handle romanized Tamil: "my per X", "ennodiya per X"
            m = re.match(
                r"(?:my\s+)?(?:full\s+)?(?:name|per|peru)\s*(?:is\s*)?[:\-]?\s*(.+)",
                seg, re.IGNORECASE
            )
            if m:
                candidate = _clean_name(m.group(1))
                print(f"[DEBUG _extract_details] Name candidate from segment {seg!r}: {candidate!r}")
                if candidate and _is_valid_name(candidate) and not _is_keyword(candidate):
                    if candidate != flow.state.get("mother_name"):
                        flow.state["full_name"] = candidate
                        updated = True
                        print(f"[DEBUG _extract_details] ✓ full_name = {candidate!r}")
                        break

        # Fallback: if still no name, look for a name-like token in the whole text
        # only in the portion before any mother/salary keyword
        if not flow.state.get("full_name"):
            search_text = text
            # Truncate at first mother/salary keyword
            cut = re.search(r'\b(mother|mom|amma|salary|income|email)\b', text, re.IGNORECASE)
            if cut:
                search_text = text[:cut.start()]

            # Look for "name is X" or "per X" pattern anywhere
            m = re.search(
                r"(?:my\s+)?(?:full\s+)?(?:name|per|peru)\s*(?:is\s*)?[:\-]?\s*([A-Za-z][A-Za-z\s]{1,40}?)(?:\s*$|\s*,|\s+and\b)",
                search_text, re.IGNORECASE
            )
            if m:
                candidate = _clean_name(m.group(1))
                print(f"[DEBUG _extract_details] Name fallback candidate: {candidate!r}")
                if candidate and len(candidate) >= 2 and _is_valid_name(candidate) and not _is_keyword(candidate):
                    if candidate != flow.state.get("mother_name"):
                        flow.state["full_name"] = candidate
                        updated = True
                        print(f"[DEBUG _extract_details] ✓ full_name (fallback) = {candidate!r}")

    # ── Step 5: Extract email ─────────────────────────────────────
    if not flow.state.get("email"):
        _use_account = re.compile(
            r"\b(use\s+(my\s+)?(account|same|existing|registered|current)\s+email|"
            r"same\s+as\s+(account|registered)|yes\s+(use|keep|same)|keep\s+(it|same|this))\b",
            re.IGNORECASE
        )
        account_email = flow.state.get("_account_email")
        if account_email and _use_account.search(text.lower()):
            flow.state["email"] = account_email
            flow.state["email_source"] = "account"
            updated = True
            print(f"[DEBUG _extract_details] ✓ email = account ({account_email!r})")
        else:
            email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
            if email_match:
                flow.state["email"] = email_match.group(0).lower()
                flow.state["email_source"] = "new"
                updated = True
                print(f"[DEBUG _extract_details] ✓ email = {flow.state['email']!r}")

    # ── Step 6: Extract salary / annual income ────────────────────
    if not flow.state.get("salary"):
        salary_found = False
        for seg in segments:
            result = _parse_salary(seg)
            if result:
                flow.state["salary"] = result
                updated = True
                salary_found = True
                print(f"[DEBUG _extract_details] ✓ salary = {result!r}")
                break
        if not salary_found:
            # Final fallback: search entire normalised text
            result = _parse_salary(text)
            if result:
                flow.state["salary"] = result
                updated = True
                print(f"[DEBUG _extract_details] ✓ salary (fallback) = {result!r}")

    # ── Step 7: Positional fallback — bare comma/and-separated list ─────────
    # When the user responds to the prompt with values in the same order as asked,
    # e.g. "deva, govidhan, nabina, 3 lakhs" in response to:
    #   Full name / Grandfather's name / Mother's name / Annual income
    # Map each segment to the next missing field in the collection order.
    #
    # Only activate when:
    #   - At least one segment looks like a plain name/value (no keyword matched)
    #   - There are multiple comma/and-separated segments
    #   - At least one field is still missing

    _missing_now = _missing_details(flow)
    if _missing_now and len(segments) >= 2:
        # Build the ordered list of still-missing fields
        _FIELD_ORDER = ["full_name", "grandfather_name", "mother_name", "email", "salary"]
        remaining_fields = [f for f in _FIELD_ORDER if f in _missing_now]

        if remaining_fields:
            # Build a list of segments that weren't already consumed by keyword patterns
            # A segment is "unconsumed" if it doesn't contain field keywords
            _KEYWORD_RE = re.compile(
                r"\b(name|per|peru|mother|mom|amma|grandfather|grandpa|thatha|"
                r"email|salary|income|₹|rs\.?|inr)\b",
                re.IGNORECASE
            )
            plain_segments = [s for s in segments if not _KEYWORD_RE.search(s)]

            if len(plain_segments) >= 2 or (len(plain_segments) == len(segments) and len(segments) >= 1):
                # Use all segments if they're all plain (no keywords at all in any)
                segs_to_use = plain_segments if plain_segments else segments
                print(f"[DEBUG _extract_details] Positional fallback: fields={remaining_fields}, segs={segs_to_use}")

                for i, field in enumerate(remaining_fields):
                    if i >= len(segs_to_use):
                        break
                    seg = segs_to_use[i].strip()
                    if not seg or flow.state.get(field):
                        continue

                    if field == "salary":
                        result = _parse_salary(seg)
                        if result:
                            flow.state["salary"] = result
                            updated = True
                            print(f"[DEBUG _extract_details] ✓ salary (positional) = {result!r}")
                    elif field == "email":
                        em = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", seg)
                        if em:
                            flow.state["email"] = em.group(0).lower()
                            flow.state["email_source"] = "new"
                            updated = True
                            print(f"[DEBUG _extract_details] ✓ email (positional) = {flow.state['email']!r}")
                    else:
                        # Name field — clean and validate
                        candidate = _clean_name(seg)
                        if candidate and _is_valid_name(candidate) and not _is_keyword(candidate):
                            flow.state[field] = candidate
                            updated = True
                            print(f"[DEBUG _extract_details] ✓ {field} (positional) = {candidate!r}")

    print(f"[DEBUG _extract_details] Final: full_name={flow.state.get('full_name')!r}, "
          f"grandfather_name={flow.state.get('grandfather_name')!r}, "
          f"mother_name={flow.state.get('mother_name')!r}, salary={flow.state.get('salary')!r}, "
          f"updated={updated}")
    return updated


def _parse_salary(text: str) -> str | None:
    """
    Parse salary/income from a string in any common Indian format.
    Returns formatted string like "₹5,00,000" or None if not found.

    Handles:
      - 6 lakh / 6 lakhs / 6L / 6l / 6.5 lakh / 3lahks / 5lakh (no space)
      - 6 lpa / 6 LPA / 6.5 lpa  (Lakhs Per Annum)
      - 6 cr / 6 crore / 6.5 crore / 2crore (no space)
      - 50k / 50K / 50 thousand
      - ₹5,00,000 / Rs. 500000 / INR 500000
      - 500000 (bare number ≥ 10000, treated as rupees)
      - "six lakh" / "five lakh fifty thousand" (word numbers)
    """
    t = text.strip().lower()

    # ── Step 0: Insert space between digit and attached unit (3lahks → 3 lahks) ──
    # Handles: "3lahks", "5lakh", "6lakhs", "2crore", "50k", "3kodi" etc.
    _UNIT_SUFFIXES = (
        r'lahks?|lakhs?|laksh|laks|laakh|lac[cs]?|lkahs?|lkah|lkhs|lahks?|lahk|lakss'
        r'|lpa|l\.p\.a\.?'
        r'|crores?|cr'
        r'|kodis?|kodi'           # Tamil: கோடி (crore)
        r'|millions?'
        r'|thousands?'
        r'|k'
        r'|l\b'
    )
    t = re.sub(rf'(\d)({_UNIT_SUFFIXES})', r'\1 \2', t)

    # ── Step 1: Normalise unit spellings ─────────────────────────
    _NORM = [
        (r'\blpa\b',     'lakh'),
        (r'\bl\.p\.a\.?\b', 'lakh'),
        (r'\blakhs?\b',  'lakh'),   (r'\blaccs?\b', 'lakh'),
        (r'\blac\b',     'lakh'),   (r'\blacs\b',   'lakh'),
        (r'\blaakh\b',   'lakh'),   (r'\blaksh\b',  'lakh'),
        (r'\blaks\b',    'lakh'),   (r'\blkahs?\b', 'lakh'),
        (r'\blkah\b',    'lakh'),   (r'\blkhs\b',   'lakh'),
        (r'\blahks?\b',  'lakh'),   (r'\blahk\b',   'lakh'),
        (r'\blakss\b',   'lakh'),
        (r'\blatcham\b', 'lakh'),   (r'\blaksham\b','lakh'),
        (r'\blacham\b',  'lakh'),
        (r'\bcrores?\b', 'crore'),  (r'\bcr\b',     'crore'),
        # Tamil romanized: கோடி = crore
        (r'\bkodis?\b',  'crore'),  (r'\bkodi\b',   'crore'),
        (r'\bkoodi\b',   'crore'),  (r'\bkoday\b',  'crore'),
        (r'\bkotis?\b',  'crore'),  (r'\bkoti\b',   'crore'),  # Hindi कोटि
        (r'\bmillion\b', 'crore'),  # 1M ≈ not crore but map loosely for intent
        (r'\bthousands?\b', 'k'),
        (r'\bper\s+annum\b', ''),
        (r'\bp\.?a\.?\b', ''),
    ]
    for pat, repl in _NORM:
        t = re.sub(pat, repl, t)

    # ── Step 2: Word numbers → digits ────────────────────────────
    _WORD_NUMS = {
        'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,
        'six':6,'seven':7,'eight':8,'nine':9,'ten':10,
        'eleven':11,'twelve':12,'thirteen':13,'fourteen':14,'fifteen':15,
        'sixteen':16,'seventeen':17,'eighteen':18,'nineteen':19,'twenty':20,
        'thirty':30,'forty':40,'fifty':50,'sixty':60,'seventy':70,
        'eighty':80,'ninety':90,'hundred':100,
    }
    def _words_to_num(s: str) -> str:
        tokens = s.split()
        result, acc = [], 0
        for tok in tokens:
            if tok in _WORD_NUMS:
                acc += _WORD_NUMS[tok]
            else:
                if acc:
                    result.append(str(acc))
                    acc = 0
                result.append(tok)
        if acc:
            result.append(str(acc))
        return ' '.join(result)

    t = _words_to_num(t)

    # ── Step 3: Pattern matching ──────────────────────────────────
    def _to_rupees(num: float, unit: str) -> float:
        u = unit.strip().lower()
        if u == 'lakh':  return num * 100_000
        if u == 'crore': return num * 10_000_000
        if u == 'k':     return num * 1_000
        return num

    def _fmt(num: float) -> str:
        return f"₹{num:,.0f}"

    # 1. Currency prefix: ₹ / Rs. / INR then number then optional unit
    m = re.search(
        r'(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(lakh|crore|k)?',
        t, re.IGNORECASE
    )
    if m:
        try:
            return _fmt(_to_rupees(float(m.group(1).replace(',','')), m.group(2) or ''))
        except ValueError:
            pass

    # 2. Keyword then number then unit: "salary is 6 lakh", "income 5,00,000"
    m = re.search(
        r'(?:salary|income|earn(?:ing)?s?|annual)\s*(?:is\s*|:\s*|of\s*)?'
        r'([\d,]+(?:\.\d+)?)\s*(lakh|crore|k)?',
        t, re.IGNORECASE
    )
    if m:
        try:
            return _fmt(_to_rupees(float(m.group(1).replace(',','')), m.group(2) or ''))
        except ValueError:
            pass

    # 3. Number directly attached to single-letter unit: "6L", "6.5L", "50K", "2CR"
    m = re.search(r'\b([\d]+(?:\.\d+)?)\s*(l|k|cr)\b', t, re.IGNORECASE)
    if m:
        try:
            unit_map = {'l': 'lakh', 'k': 'k', 'cr': 'crore'}
            return _fmt(_to_rupees(float(m.group(1)), unit_map[m.group(2).lower()]))
        except ValueError:
            pass

    # 4. Number + unit (with space after normalization): "6 lakh", "2.5 crore", "50 k"
    m = re.search(r'\b([\d,]+(?:\.\d+)?)\s+(lakh|crore|k)\b', t, re.IGNORECASE)
    if m:
        try:
            return _fmt(_to_rupees(float(m.group(1).replace(',','')), m.group(2)))
        except ValueError:
            pass

    # 5. Bare number ≥ 10,000 (treat as rupees): "500000", "5,00,000"
    m = re.search(r'\b([\d,]+)\b', t)
    if m:
        try:
            val = float(m.group(1).replace(',',''))
            if val >= 10_000:
                return _fmt(val)
        except ValueError:
            pass

    return None


def _is_valid_name(name: str) -> bool:
    """
    Basic sanity check for a person name.
    Allows names like "Deva" (single name), "Deva J" (first name + initial), or "John Doe" (full names).
    """
    if not name or len(name.strip()) < 2:
        return False
    words = name.strip().split()
    if len(words) < 1 or len(words) > 5:
        return False
    
    # Allow single-letter words (initials) but require at least one word with 2+ characters
    has_substantial_word = any(len(w) >= 2 for w in words)
    if not has_substantial_word:
        return False  # Reject names like "A B" (all initials)
    
    # Must be mostly alphabetic (letters and spaces)
    alpha_ratio = sum(c.isalpha() or c.isspace() for c in name) / len(name)
    if alpha_ratio < 0.85:
        print(f"[DEBUG _is_valid_name] Rejected '{name}' - alpha_ratio={alpha_ratio:.2f} < 0.85")
        return False
    
    return True


_KEYWORDS = {
    "residence", "office", "representative", "assessee", "resident",
    "non-resident", "salary", "income", "business", "capital", "gains",
    "aadhaar", "aadhar", "driving", "license", "photograph", "indian",
    "citizen", "company", "foreign", "physical", "digital", "email",
    "yes", "no", "okay", "sure", "proceed", "confirm",
}

def _is_keyword(text: str) -> bool:
    return any(w.lower() in _KEYWORDS for w in text.split())


def _build_documents_response(flow: FlowManager, language: str = None) -> dict:
    """
    Build the documents-step response dict.
    Always includes confirmation_fields so the user can still edit any field
    after the document list is shown, without having to go back to confirmation.
    """
    if language is None:
        language = flow.state.get("_current_language", "en")

    doc_text = _ask_for_documents(flow, language)

    # Re-use _build_confirmation to get the live confirmation_fields structure,
    # then pull only the fields part — we don't want its answer text here.
    _conf = _build_confirmation(flow)

    return {
        "answer": doc_text,
        "sources": [], "followups": [], "guided": True,
        "step": "documents",
        "flow_confirmed": True,
        "confirmation_fields": _conf.get("confirmation_fields"),   # ← edit panel
        "flow_data": {
            "full_name":          flow.state.get("full_name"),
            "grandfather_name":   flow.state.get("grandfather_name"),
            "mother_name":        flow.state.get("mother_name"),
            "email":              flow.state.get("email"),
            "salary":             flow.state.get("salary"),
            "applicant_type":     flow.state.get("applicant_type"),
            "submission_mode":    flow.state.get("submission_mode"),
            "delivery_mode":      flow.state.get("delivery_mode"),
            "aadhaar_photo":      flow.state.get("aadhaar_photo"),
            "source_of_income":   flow.state.get("source_of_income"),
            "address_for_comm":   flow.state.get("address_for_comm"),
            "residential_status": flow.state.get("residential_status"),
            "rep_assessee":       flow.state.get("rep_assessee"),
        },
    }


def _build_confirmation(flow: FlowManager) -> dict:
    """Build the full confirmation summary with confirm_action buttons."""
    s = flow.state

    def _yn(val):
        if val is True:  return "Yes"
        if val is False: return "No"
        return str(val) if val else "—"

    delivery = (
        "Physical + e-PAN" if s.get("delivery_mode") == "physical_and_soft"
        else "e-PAN only" if s.get("delivery_mode") == "soft_only"
        else "—"
    )

    lines = [
        "Here's everything I've collected for your PAN application.",
        "",
        "## Application Options",
        f"- Submission mode: **{s.get('submission_mode') or '—'}**",
        f"- PAN delivery: **{delivery}**",
        f"- Aadhaar photo on PAN: **{_yn(s.get('aadhaar_photo'))}**",
        f"- Source of income: **{s.get('source_of_income') or '—'}**",
        f"- Address for communication: **{s.get('address_for_comm') or '—'}**",
        f"- Residential status: **{s.get('residential_status') or '—'}**",
        f"- Representative Assessee: **{_yn(s.get('rep_assessee'))}**",
        "",
        "## Personal Details",
        f"- Full name (as in Aadhaar): **{s.get('full_name') or '—'}**",
        f"- Grandfather's name: **{s.get('grandfather_name') or '—'}**",
        f"- Mother's name: **{s.get('mother_name') or '—'}**",
        f"- Email: **{s.get('email') or '—'}**",
        f"- Annual income: **{s.get('salary') or '—'}**",
        "",
        "---",
        "",
        "Does everything look correct? Proceed to document upload?",
        "",
        "You can also update multiple fields at once — just say something like:",
        '*"change my name to John and salary to 5 lakh"*',
    ]

    answer = "\n".join(lines)

    # Add explicit button options for Proceed/Change action buttons
    opts = {
        "type": "confirmation",
        "choices": ["Yes, proceed", "Change something"],
    }

    # ── Per-field structured data for inline edit buttons ────────────────────
    # Each entry: { key, label, label_ta, value, display_value, field_type, options? }
    confirmation_fields = [
        # ── Application Options ──────────────────────────────────────────────
        {
            "key": "submission_mode",
            "label": "Submission Mode",
            "label_ta": "சமர்ப்பிக்கும் முறை",
            "value": s.get("submission_mode") or "",
            "display_value": s.get("submission_mode") or "—",
            "field_type": "radio",
            "section": "application",
            "choices": [
                "Aadhaar-based Online (eKYC)",
                "Upload scanned docs & eSign",
                "Fill online + courier physical form",
            ],
            "choices_ta": [
                "ஆதார் அடிப்படையிலான ஆன்லைன் (eKYC)",
                "ஸ்கேன் செய்த ஆவணங்களை பதிவேற்றி eSign செய்யவும்",
                "ஆன்லைனில் நிரப்பி இயற்பியல் படிவத்தை அனுப்பவும்",
            ],
        },
        {
            "key": "delivery_mode",
            "label": "PAN Delivery",
            "label_ta": "விநியோக முறை",
            "value": s.get("delivery_mode") or "",
            "display_value": delivery,
            "field_type": "radio",
            "section": "application",
            "choices": [
                "Physical copy to home + soft copy on email (Fees applicable)",
                "Only soft copy on email (Fees applicable)",
            ],
            "choices_ta": [
                "வீட்டிற்கு இயற்பியல் நகல் + மின்னஞ்சலில் மென் நகல் (கட்டணம் உண்டு)",
                "மின்னஞ்சலில் மட்டும் மென் நகல் (கட்டணம் உண்டு)",
            ],
        },
        {
            "key": "aadhaar_photo",
            "label": "Aadhaar Photo on PAN",
            "label_ta": "ஆதார் புகைப்படம்",
            "value": str(s.get("aadhaar_photo")) if s.get("aadhaar_photo") is not None else "",
            "display_value": _yn(s.get("aadhaar_photo")),
            "field_type": "radio",
            "section": "application",
            "choices": ["Yes", "No"],
            "choices_ta": ["ஆம்", "இல்லை"],
        },
        {
            "key": "source_of_income",
            "label": "Source of Income",
            "label_ta": "வருமான மூலம்",
            "value": s.get("source_of_income") or "",
            "display_value": s.get("source_of_income") or "—",
            "field_type": "radio",
            "section": "application",
            "choices": [
                "Salary",
                "Income from Business / Profession",
                "Income from House property",
                "Income from Other sources",
                "Capital Gains",
                "No income",
            ],
            "choices_ta": [
                "சம்பளம்",
                "வணிகம் / தொழிலிலிருந்து வருமானம்",
                "வீட்டு சொத்திலிருந்து வருமானம்",
                "பிற மூலங்களிலிருந்து வருமானம்",
                "மூலதன ஆதாயங்கள்",
                "வருமானம் இல்லை",
            ],
        },
        {
            "key": "address_for_comm",
            "label": "Address for Communication",
            "label_ta": "தொடர்பு முகவரி",
            "value": s.get("address_for_comm") or "",
            "display_value": s.get("address_for_comm") or "—",
            "field_type": "radio",
            "section": "application",
            "choices": ["Residence", "Office", "Representative Assessee (RA)"],
            "choices_ta": ["வீடு", "அலுவலகம்", "பிரதிநிதி நியமனம் (RA)"],
        },
        {
            "key": "residential_status",
            "label": "Residential Status",
            "label_ta": "குடியிருப்பு நிலை",
            "value": s.get("residential_status") or "",
            "display_value": s.get("residential_status") or "—",
            "field_type": "radio",
            "section": "application",
            "choices": ["Resident", "Non-resident", "Resident but not ordinarily resident"],
            "choices_ta": ["குடியிருப்பாளர்", "குடியிருப்பு இல்லாதவர்", "குடியிருப்பாளர் ஆனால் வழக்கமாக இல்லாதவர்"],
        },
        {
            "key": "rep_assessee",
            "label": "Representative Assessee",
            "label_ta": "பிரதிநிதி நியமனம்",
            "value": str(s.get("rep_assessee")) if s.get("rep_assessee") is not None else "",
            "display_value": _yn(s.get("rep_assessee")),
            "field_type": "radio",
            "section": "application",
            "choices": ["Yes", "No"],
            "choices_ta": ["ஆம்", "இல்லை"],
        },
        # ── Personal Details ─────────────────────────────────────────────────
        {
            "key": "full_name",
            "label": "Full Name (as in Aadhaar)",
            "label_ta": "முழு பெயர் (ஆதார் படி)",
            "value": s.get("full_name") or "",
            "display_value": s.get("full_name") or "—",
            "field_type": "text",
            "section": "personal",
        },
        {
            "key": "grandfather_name",
            "label": "Grandfather's Name",
            "label_ta": "தாத்தாவின் பெயர்",
            "value": s.get("grandfather_name") or "",
            "display_value": s.get("grandfather_name") or "—",
            "field_type": "text",
            "section": "personal",
        },
        {
            "key": "mother_name",
            "label": "Mother's Name",
            "label_ta": "தாயின் பெயர்",
            "value": s.get("mother_name") or "",
            "display_value": s.get("mother_name") or "—",
            "field_type": "text",
            "section": "personal",
        },
        {
            "key": "email",
            "label": "Email",
            "label_ta": "மின்னஞ்சல்",
            "value": s.get("email") or "",
            "display_value": s.get("email") or "—",
            "field_type": "text",
            "section": "personal",
        },
        {
            "key": "salary",
            "label": "Annual Income",
            "label_ta": "ஆண்டு வருமானம்",
            "value": s.get("salary") or "",
            "display_value": s.get("salary") or "—",
            "field_type": "text",
            "section": "personal",
        },
    ]

    return {
        "answer": answer,
        "sources": [], "followups": [], "guided": False,
        "step": "confirmation",
        "options": opts,
        "confirm_action": True,
        "confirmation_fields": confirmation_fields,
    }


def _detect_modification_field(inp: str) -> str | None:
    """
    Detect which field the user wants to modify from their message.
    Supports English and Tamil.
    """
    lower = inp.strip().lower()
    print(f"[DEBUG] Detecting field from input: {lower!r}")

    # ── Mother name — check FIRST to avoid matching plain "name" ──
    # English + Tamil patterns
    if re.search(r"\b(mother|mom|mum|தாய்|அம்மா)\b", lower):
        print("[DEBUG] Matched: mother_name")
        return "mother_name"

    # ── Grandfather name — check before plain "name" ───────────────
    if re.search(r"\b(grandfather|grandpa|grand\s*father|thatha|thaatha|தாத்தா)\b", lower):
        print("[DEBUG] Matched: grandfather_name")
        return "grandfather_name"

    # ── Full name ──────────────────────────────────────────────────
    # English + Tamil: பெயர் (name)
    if re.search(r"\b(full\s+name|my\s+name|name\s+on\s+aadhaar|aadhaar\s+name|"
                 r"change\s+name|update\s+name|name\s+is|name\s+to|name$|^name\b|"
                 r"பெயர்|முழு\s*பெயர்|என்\s*பெயர்)\b", lower):
        print("[DEBUG] Matched: full_name")
        return "full_name"

    # ── Email ──────────────────────────────────────────────────────
    # English + Tamil: மின்னஞ்சல் (email)
    if re.search(r"\b(email|mail|gmail|e-mail|மின்னஞ்சல்|மெயில்)\b", lower):
        print("[DEBUG] Matched: email")
        return "email"

    # ── Source of income — check BEFORE plain "income/salary" ─────
    # English + Tamil: வருமான ஆதாரம் (income source)
    if re.search(r"\b(source\s+of\s+income|income\s+source|income\s+type|^source\b|"
                 r"வருமான\s*ஆதாரம்|வருமானம்\s*வகை)\b", lower):
        print("[DEBUG] Matched: source_of_income")
        return "source_of_income"

    # ── Annual income / salary ─────────────────────────────────────
    # English + Tamil: சம்பளம் (salary), வருமானம் (income), ஆண்டு வருமானம் (annual income)
    if re.search(r"\b(salary|income|earning|annual|pay|annual\s+income|"
                 r"சம்பளம்|வருமானம்|ஆண்டு\s*வருமானம்|சம்பளத்|வருவாய்)\b", lower):
        print("[DEBUG] Matched: salary")
        return "salary"

    # ── Submission mode ────────────────────────────────────────────
    # English + Tamil: சமர்ப்பிப்பு முறை (submission mode)
    if re.search(r"\b(submission|how\s+to\s+submit|submit\s+mode|submission\s+mode|"
                 r"சமர்ப்பிப்பு|சமர்ப்பிக்கும்\s*முறை|சமர்ப்பிப்பு\s*முறை)\b", lower):
        print("[DEBUG] Matched: submission_mode")
        return "submission_mode"

    # ── Delivery mode ──────────────────────────────────────────────
    # English + Tamil: விநியோக முறை (delivery mode), PAN விநியோகம் (PAN delivery)
    if re.search(r"\b(delivery|card\s+delivery|pan\s+delivery|soft\s+copy|"
                 r"விநியோக|விநியோகம்|விநியோக\s*முறை|அனுப்பும்\s*முறை)\b", lower):
        print("[DEBUG] Matched: delivery_mode")
        return "delivery_mode"

    # ── Aadhaar photo ──────────────────────────────────────────────
    # English + Tamil: ஆதார் புகைப்படம் (Aadhaar photo)
    if re.search(r"\b(aa?dhaa?r\s+photo|photo\s+on\s+pan|photo\s+consent|aadhar\s+photo|aadhaar\s+photo|"
                 r"ஆதார்\s*புகைப்படம்|புகைப்படம்)\b", lower):
        print("[DEBUG] Matched: aadhaar_photo")
        return "aadhaar_photo"

    # ── Address for communication ──────────────────────────────────
    # English + Tamil: தொடர்பு முகவரி (communication address)
    if re.search(r"\b(address\s+for\s+comm(unication)?|communication\s+address|"
                 r"comm\s+address|address.*communication|communication.*address|"
                 r"தொடர்பு\s*முகவரி|தொடர்பிற்கான\s*முகவரி|முகவரி)\b", lower):
        print("[DEBUG] Matched: address_for_comm")
        return "address_for_comm"
    if re.search(r"^address$|^change\s+address$|^update\s+address$|^முகவரி$", lower):
        print("[DEBUG] Matched: address_for_comm (simple)")
        return "address_for_comm"

    # ── Residential status ─────────────────────────────────────────
    # English + Tamil: குடியிருப்பு நிலை (residential status)
    if re.search(r"\b(residential\s+status|residency|resident\s+status|residential|"
                 r"குடியிருப்பு|குடியிருப்பு\s*நிலை|வசிப்பிட\s*நிலை)\b", lower):
        print("[DEBUG] Matched: residential_status")
        return "residential_status"

    # ── Representative Assessee ────────────────────────────────────
    # English + Tamil: பிரதிநிதி மதிப்பீட்டாளர் (representative assessee)
    if re.search(r"\b(representative\s+assessee|rep\s+assessee|appointing\s+representative|"
                 r"பிரதிநிதி|பிரதிநிதி\s*மதிப்பீட்டாளர்)\b", lower):
        print("[DEBUG] Matched: rep_assessee")
        return "rep_assessee"

    # ── Bare field-label fallback — exact label text from confirmation screen ──
    _LABEL_MAP = {
        # English labels
        "submission mode":           "submission_mode",
        "pan delivery":              "delivery_mode",
        "aadhaar photo on pan":      "aadhaar_photo",
        "source of income":          "source_of_income",
        "address for communication": "address_for_comm",
        "residential status":        "residential_status",
        "representative assessee":   "rep_assessee",
        "full name":                 "full_name",
        "annual income":             "salary",
        "mothers name":              "mother_name",
        "mother name":               "mother_name",
        "grandfather's name":        "grandfather_name",
        "grandfather name":          "grandfather_name",
        "grandfathers name":         "grandfather_name",
        "thatha name":               "grandfather_name",
        # Tamil labels
        "சமர்ப்பிப்பு முறை":         "submission_mode",
        "பான் விநியோகம்":            "delivery_mode",
        "ஆதார் புகைப்படம்":          "aadhaar_photo",
        "வருமான ஆதாரம்":            "source_of_income",
        "தொடர்பு முகவரி":           "address_for_comm",
        "குடியிருப்பு நிலை":         "residential_status",
        "பிரதிநிதி மதிப்பீட்டாளர்":  "rep_assessee",
        "முழு பெயர்":                "full_name",
        "ஆண்டு வருமானம்":           "salary",
        "தாயின் பெயர்":              "mother_name",
        "தாத்தாவின் பெயர்":          "grandfather_name",
        "தாத்தா பெயர்":              "grandfather_name",
    }
    for label, field in _LABEL_MAP.items():
        if label in lower:
            print(f"[DEBUG] Matched via label map: {field}")
            return field

    print(f"[DEBUG] No field matched for: {lower!r}")
    return None


def _ask_for_field(flow: FlowManager, field: str) -> dict:
    """Ask the user to provide a new value for a specific field, with options if applicable."""
    
    # Fields with radio/checkbox options
    if field == "submission_mode":
        opts = {
            "type": "radio", "label": "Submission mode", "field": "submission_mode",
            "choices": [
                "Aadhaar-based Online (eKYC)",
                "Upload scanned docs & eSign",
                "Fill online + courier physical form",
            ],
            "descriptions": [
                "Uses your Aadhaar details for eKYC — Name, Photo, DOB, Gender & Address.",
                "Upload scanned Photo, Signature and supporting documents, then eSign.",
                "Fill the form online, print, sign and courier/speed-post to Protean's Pune office.",
            ],
        }
        return {
            "answer": "**How would you like to submit your PAN application documents?**",
            "sources": [], "followups": [], "guided": True,
            "step": "confirmation", "options": opts,
        }
    
    elif field == "delivery_mode":
        opts = {
            "type": "radio", "label": "PAN delivery", "field": "delivery_mode",
            "choices": [
                "Physical copy to home + soft copy on email (Fees applicable)",
                "Only soft copy on email (Fees applicable)",
            ],
        }
        return {
            "answer": (
                "**How would you like your PAN card to be delivered?**\n\n"
                "Here are the applicable fees:\n\n"
                + _FEE_PHYSICAL.strip()
                + "\n\n---\n\n"
                + _FEE_SOFT.strip()
            ),
            "sources": [], "followups": [], "guided": True,
            "step": "confirmation", "options": opts,
        }
    
    elif field == "aadhaar_photo":
        opts = {
            "type": "radio", "label": "Aadhaar photo consent", "field": "aadhaar_photo",
            "choices": ["Yes", "No"],
        }
        return {
            "answer": "**I hereby agree to have my Aadhaar photo printed on my PAN Card.**\n\n> Note: If you do not wish to use your Aadhaar photo, you may apply for a PAN with a separate photograph.",
            "sources": [], "followups": [], "guided": True,
            "step": "confirmation", "options": opts,
        }
    
    elif field == "source_of_income":
        opts = {
            "type": "radio", "label": "Source of Income", "field": "source_of_income",
            "choices": [
                "Salary",
                "Income from Business / Profession",
                "Income from House property",
                "Income from Other sources",
                "Capital Gains",
                "No income",
            ],
        }
        return {
            "answer": "**Please select your Source of Income:**",
            "sources": [], "followups": [], "guided": True,
            "step": "confirmation", "options": opts,
        }
    
    elif field == "address_for_comm":
        hint = "**Important instructions for e-KYC (Individual):**\n1. Address from Aadhaar card will be used as residence address.\n2. PAN card dispatched to Aadhaar address.\n3. If Aadhaar address exceeds IT Dept length limit, e-KYC won't be available."
        opts = {
            "type": "radio", "label": "Address for Communication", "field": "address_for_comm",
            "choices": ["Residence", "Office", "Representative Assessee (RA)"],
            "hint": hint,
        }
        return {
            "answer": "**Address for Communication** — Please tick as applicable:",
            "sources": [], "followups": [], "guided": True,
            "step": "confirmation", "options": opts,
        }
    
    elif field == "residential_status":
        opts = {
            "type": "radio", "label": "Residential Status", "field": "residential_status",
            "choices": ["Resident", "Non-resident", "Resident but not ordinarily resident"],
        }
        return {
            "answer": "**What is your Residential Status?**",
            "sources": [], "followups": [], "guided": True,
            "step": "confirmation", "options": opts,
        }
    
    elif field == "rep_assessee":
        opts = {
            "type": "radio", "label": "Representative Assessee", "field": "rep_assessee",
            "choices": ["Yes", "No"],
        }
        return {
            "answer": "**Appointing Representative Assessee?**\n\n> A Representative Assessee is someone who manages tax obligations on behalf of another person (e.g. a guardian for a minor, or a legal heir for a deceased person). Select **Yes** only if you are applying on behalf of someone else.",
            "sources": [], "followups": [], "guided": True,
            "step": "confirmation", "options": opts,
        }
    
    # Text input fields (no options)
    else:
        prompts = {
            "full_name":       "Please provide your **full name exactly as it appears on your Aadhaar card**:",
            "grandfather_name":"Please provide your **grandfather's full name** (as per official records):",
            "mother_name":     "Please provide your **mother's full name** (as per official records):",
            "email":           "Please provide the **email address** you'd like to use for PAN correspondence:",
            "salary":          "Please provide your **annual income / salary per year** (not monthly — e.g. ₹5,00,000):",
        }
        answer = prompts.get(field, f"Please provide the updated value for **{field.replace('_', ' ').title()}**:")
        return {
            "answer": answer,
            "sources": [], "followups": [], "guided": True,
            "step": "confirmation",
        }


def _apply_field_update(flow: FlowManager, field: str, inp: str, raw: str):
    """Apply a user-provided update to a specific field."""
    text = raw.strip()
    lower = inp.lower()

    if field == "full_name":
        # Extract name from input - handle "name is X", "name as X", "name to X" and just "X"
        name_match = re.search(
            r"(?:(?:my\s+)?(?:full\s+)?name\s+(?:is|as|to)\s+|change\s+(?:to|it\s+to)\s+|update\s+(?:to|it\s+to)\s+)?([A-Za-z][A-Za-z\s]{1,50})$",
            text, re.IGNORECASE
        )
        if name_match:
            candidate = name_match.group(1).strip()
        else:
            candidate = text
        
        # Filter out common command/preposition words
        words = candidate.split()
        _FILTER_WORDS = {'my', 'name', 'is', 'as', 'the', 'full', 'change', 'update', 'to', 'it'}
        filtered_words = [w for w in words if w.lower() not in _FILTER_WORDS]
        
        if filtered_words:
            candidate = ' '.join(filtered_words)
            if _is_valid_name(candidate):
                flow.state["full_name"] = candidate
                print(f"[DEBUG _apply_field_update] Updated full_name to: {candidate!r}")
            else:
                print(f"[DEBUG _apply_field_update] Invalid name: {candidate!r}")
        else:
            print(f"[DEBUG _apply_field_update] Name filtered to empty")

    elif field == "mother_name":
        # Extract mother's name - handle "mother name is/as/to X", "mother name X", or just "X"
        _FILTER_WORDS = {'my', 'mother', "mother's", 'mothers', 'mom', "mom's", 'moms',
                         'name', 'is', 'as', 'the', 'full', 'change', 'update', 'to', 'it', 'maa', 'amma'}        # Try explicit pattern first: "mother name is/as/to X" / "change to X"
        name_match = re.search(
            r"(?:mother(?:'?s)?\s+name\s+(?:is|as|to)\s+|mom(?:'?s)?\s+name\s+(?:is|as|to)\s+|"
            r"change\s+(?:to|it\s+to)\s+|update\s+(?:to|it\s+to)\s+)([A-Za-z][A-Za-z\s]{0,50}?)(?:\s*$)",
            text, re.IGNORECASE
        )
        if name_match:
            candidate = name_match.group(1).strip()
        else:
            candidate = text.strip()

        # Filter out common command/preposition words
        words = candidate.split()
        filtered_words = [w for w in words if w.lower() not in _FILTER_WORDS]

        if filtered_words:
            candidate = ' '.join(filtered_words)
            if _is_valid_name(candidate):
                flow.state["mother_name"] = candidate
                print(f"[DEBUG _apply_field_update] Updated mother_name to: {candidate!r}")
            else:
                print(f"[DEBUG _apply_field_update] Invalid mother name: {candidate!r}")
        else:
            # All words were filtered — the raw input IS the name (e.g. user typed just "Sunita")
            candidate = text.strip()
            if _is_valid_name(candidate):
                flow.state["mother_name"] = candidate
                print(f"[DEBUG _apply_field_update] Updated mother_name (raw) to: {candidate!r}")
            else:
                print(f"[DEBUG _apply_field_update] Mother name filtered to empty")

    elif field == "grandfather_name":
        _FILTER_WORDS = {'my', 'grandfather', "grandfather's", 'grandfathers', 'grandpa',
                         'thatha', 'thaatha', 'name', 'is', 'as', 'the', 'full', 'change', 'update', 'to', 'it'}
        words = text.strip().split()
        filtered_words = [w for w in words if w.lower() not in _FILTER_WORDS]
        candidate = ' '.join(filtered_words) if filtered_words else text.strip()
        if _is_valid_name(candidate):
            flow.state["grandfather_name"] = candidate
            print(f"[DEBUG _apply_field_update] Updated grandfather_name to: {candidate!r}")
        else:
            # Fall back to raw input as name
            if _is_valid_name(text.strip()):
                flow.state["grandfather_name"] = text.strip()
                print(f"[DEBUG _apply_field_update] Updated grandfather_name (raw) to: {text.strip()!r}")
            else:
                print(f"[DEBUG _apply_field_update] Invalid grandfather name: {text.strip()!r}")

    elif field == "email":
        account_email = flow.state.get("_account_email")
        _use_account = re.compile(
            r"\b(use\s+(my\s+)?(account|same|existing|registered|current)\s+email|"
            r"same\s+as\s+(account|registered)|yes\s+(use|keep|same)|keep\s+(it|same|this))\b",
            re.IGNORECASE
        )
        if account_email and _use_account.search(lower):
            flow.state["email"] = account_email
            flow.state["email_source"] = "account"
        else:
            email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
            if email_match:
                flow.state["email"] = email_match.group(0).lower()
                flow.state["email_source"] = "new"

    elif field == "salary":
        result = _parse_salary(text)
        if result:
            flow.state["salary"] = result
            print(f"[DEBUG _apply_field_update] Updated salary to: {result!r}")
        else:
            print(f"[DEBUG _apply_field_update] Could not parse salary from: {text!r}")

    elif field == "submission_mode":
        _map = {
            "1": "Aadhaar-based Online (eKYC)", "aadhaar": "Aadhaar-based Online (eKYC)", "ekyc": "Aadhaar-based Online (eKYC)",
            "2": "Upload scanned docs & eSign", "upload": "Upload scanned docs & eSign", "scan": "Upload scanned docs & eSign",
            "3": "Fill online + courier physical form", "courier": "Fill online + courier physical form", "physical": "Fill online + courier physical form",
        }
        key = lower.split()[0] if lower else ""
        matched = _map.get(key) or next((v for k, v in _map.items() if k in lower), None)
        if matched:
            flow.state["submission_mode"] = matched

    elif field == "delivery_mode":
        if re.search(r"\b(1|physical|home|both|hard)\b", lower):
            flow.state["delivery_mode"] = "physical_and_soft"
        elif re.search(r"\b(2|soft|email|only|digital|e.?pan)\b", lower):
            flow.state["delivery_mode"] = "soft_only"

    elif field == "aadhaar_photo":
        # Handle both short responses and full option text from radio buttons
        # Check for "no" FIRST (more specific) before "yes"
        print(f"[DEBUG] aadhaar_photo: lower={lower!r}, text={text!r}")
        
        # Check for "no" first - be very explicit
        if lower.strip() == "no" or lower.strip() == "n":
            print("[DEBUG] Matched exact 'no' or 'n'")
            flow.state["aadhaar_photo"] = False
        elif re.search(r"\b(no|nope|nah|disagree|decline|don'?t|dont)\b", lower):
            print("[DEBUG] Matched 'no' pattern")
            flow.state["aadhaar_photo"] = False
        elif "no" in lower:
            print("[DEBUG] Found 'no' substring")
            flow.state["aadhaar_photo"] = False
        # Now check for "yes"
        elif lower.strip() == "yes" or lower.strip() == "y":
            print("[DEBUG] Matched exact 'yes' or 'y'")
            flow.state["aadhaar_photo"] = True
        elif re.search(r"\b(yes|yeah|yep|sure|ok|okay|agree|consent)\b", lower):
            print("[DEBUG] Matched 'yes' pattern")
            flow.state["aadhaar_photo"] = True
        elif "yes" in lower:
            print("[DEBUG] Found 'yes' substring")
            flow.state["aadhaar_photo"] = True
        else:
            print(f"[DEBUG] No match found for aadhaar_photo, input was: {lower!r}")
        
        print(f"[DEBUG] Final aadhaar_photo value: {flow.state.get('aadhaar_photo')}")

    elif field == "source_of_income":
        _SOI = [
            (re.compile(r"\b(salary|salaried|1)\b", re.IGNORECASE), "Salary"),
            (re.compile(r"\b(business|profession|self.?employed|freelanc|2)\b", re.IGNORECASE), "Income from Business / Profession"),
            (re.compile(r"\b(house\s+property|rental|rent|3)\b", re.IGNORECASE), "Income from House property"),
            (re.compile(r"\b(other\s+sources?|4)\b", re.IGNORECASE), "Income from Other sources"),
            (re.compile(r"\b(capital\s+gains?|5)\b", re.IGNORECASE), "Capital Gains"),
            (re.compile(r"\b(no\s+income|unemployed|student|homemaker|6)\b", re.IGNORECASE), "No income"),
        ]
        matched = [label for pat, label in _SOI if pat.search(text)]
        if matched:
            flow.state["source_of_income"] = ", ".join(matched)

    elif field == "address_for_comm":
        _map = {"residence": "Residence", "home": "Residence", "1": "Residence",
                "office": "Office", "work": "Office", "2": "Office",
                "representative": "Representative Assessee (RA)", "ra": "Representative Assessee (RA)", "3": "Representative Assessee (RA)"}
        key = lower.strip()
        matched = _map.get(key) or next((v for k, v in _map.items() if k in key), None)
        if matched:
            flow.state["address_for_comm"] = matched

    elif field == "residential_status":
        _map = {"resident": "Resident", "1": "Resident",
                "non-resident": "Non-resident", "nri": "Non-resident", "2": "Non-resident",
                "rnor": "Resident but not ordinarily resident", "3": "Resident but not ordinarily resident"}
        key = lower.strip()
        matched = _map.get(key) or next((v for k, v in _map.items() if k in key), None)
        if matched:
            flow.state["residential_status"] = matched

    elif field == "rep_assessee":
        if re.search(r"^(yes|y|yeah|yep|sure|ok|okay)$", lower):
            flow.state["rep_assessee"] = True
        elif re.search(r"^(no|nope|nah|n)$", lower):
            flow.state["rep_assessee"] = False


def _extract_pan(text: str) -> str | None:
    match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text.upper())
    return match.group(0) if match else None

def _extract_aadhaar(text: str) -> str | None:
    digits = re.sub(r'\D', '', text)
    return digits if len(digits) == 12 else None

def merge_form_fields(flow: FlowManager, text: str):
    pass


# ── Document Access with OTP ──────────────────────────────────────────────────

def request_user_documents(user_token: str, session_id: str) -> dict:
    """
    Request access to user's uploaded documents with OTP verification.
    This is called when the agent needs to access documents for processing.
    
    Args:
        user_token: JWT token for the user
        session_id: Current session ID
    
    Returns:
        dict: Response with OTP request status and instructions for user
    """
    flow = FlowManager(session_id, "anonymous")
    
    # Check if OTP already requested and pending
    if flow.state.get("_otp_requested") and not flow.state.get("_otp_verified"):
        return {
            "answer": "I've already sent an OTP to your registered phone number. Please provide the 6-digit code to continue.\n\n(OTP expires in 10 minutes)",
            "sources": [],
            "followups": [],
            "guided": True,
            "awaiting_otp": True,
        }
    
    # Check if OTP already verified
    if flow.state.get("_otp_verified"):
        return {
            "answer": "Access already granted. I can now access your documents.",
            "sources": [],
            "followups": [],
            "guided": True,
            "otp_verified": True,
        }
    
    # Request OTP
    result = request_document_access(user_token)
    
    if result.get("success"):
        # Mark OTP as requested
        flow.state["_otp_requested"] = True
        flow.state["_otp_phone_last_4"] = result.get("phone_last_4")
        flow.state["_otp_file_count"] = result.get("file_count", 0)
        flow.save()
        
        phone_hint = f" (ending in {result['phone_last_4']})" if result.get("phone_last_4") else ""
        
        return {
            "answer": f"🔐 **Document Access Verification Required**\n\n"
                     f"I need to access your uploaded documents to process your PAN application. "
                     f"For security, I've sent a 6-digit OTP to your registered phone number{phone_hint}.\n\n"
                     f"**Please provide the OTP to continue.**\n\n"
                     f"📱 OTP expires in {result.get('expires_in_minutes', 10)} minutes\n"
                     f"📄 Documents to access: {result.get('file_count', 0)} file(s)",
            "sources": [],
            "followups": ["Enter OTP"],
            "guided": True,
            "awaiting_otp": True,
            "otp_requested": True,
        }
    else:
        error = result.get("error")
        if error == "no_phone":
            return {
                "answer": "⚠️ **Phone Number Required**\n\n"
                         "To access your documents securely, you need to have a phone number registered. "
                         "Please add your phone number to your profile first.\n\n"
                         "Would you like me to guide you through adding a phone number?",
                "sources": [],
                "followups": ["Yes, help me add phone", "I'll do it later"],
                "guided": True,
                "requires_phone": True,
            }
        elif error == "no_documents":
            return {
                "answer": "📄 **No Documents Found**\n\n"
                         "I don't see any uploaded documents yet. Please upload your documents first using the 📎 paperclip button.",
                "sources": [],
                "followups": [],
                "guided": True,
                "no_documents": True,
            }
        else:
            return {
                "answer": f"❌ **OTP Request Failed**\n\n"
                         f"I couldn't send the OTP: {result.get('message', 'Unknown error')}\n\n"
                         f"Please try again in a moment.",
                "sources": [],
                "followups": ["Try again"],
                "guided": True,
                "otp_failed": True,
            }


def verify_user_documents_otp(user_token: str, session_id: str, otp: str) -> dict:
    """
    Verify OTP and grant agent access to user documents.
    
    Args:
        user_token: JWT token for the user
        session_id: Current session ID
        otp: 6-digit OTP code from user
    
    Returns:
        dict: Response with verification status and document list
    """
    flow = FlowManager(session_id, "anonymous")
    
    # Verify OTP
    result = verify_document_access(user_token, otp)
    
    if result.get("success"):
        # Mark OTP as verified
        flow.state["_otp_verified"] = True
        flow.state["_otp_verified_at"] = result.get("access_granted_at")
        flow.state["_otp_expires_at"] = result.get("access_expires_at")
        flow.state["_available_documents"] = result.get("documents", [])
        flow.save()
        
        doc_count = len(result.get("documents", []))
        doc_list = "\n".join([
            f"- {doc['file_name']} ({doc['mime_type']}, {doc['file_size']} bytes)"
            for doc in result.get("documents", [])[:5]  # Show first 5
        ])
        
        more_docs = ""
        if doc_count > 5:
            more_docs = f"\n... and {doc_count - 5} more document(s)"
        
        return {
            "answer": f"✅ **OTP Verified Successfully!**\n\n"
                     f"I now have access to your documents and can process your PAN application.\n\n"
                     f"**Documents available ({doc_count}):**\n{doc_list}{more_docs}\n\n"
                     f"🔒 Access expires in 30 minutes for security.\n\n"
                     f"Let me review your documents and continue with the application...",
            "sources": [],
            "followups": [],
            "guided": True,
            "otp_verified": True,
            "documents": result.get("documents", []),
        }
    else:
        error = result.get("error")
        if error == "invalid_otp":
            remaining = result.get("remaining_attempts")
            attempts_msg = f"\n\n⚠️ {remaining} attempt(s) remaining." if remaining else ""
            return {
                "answer": f"❌ **Invalid OTP**\n\n"
                         f"The OTP you provided is incorrect. Please check and try again.{attempts_msg}",
                "sources": [],
                "followups": ["Try again", "Resend OTP"],
                "guided": True,
                "otp_invalid": True,
                "remaining_attempts": remaining,
            }
        elif error == "too_many_attempts":
            return {
                "answer": "🚫 **Too Many Failed Attempts**\n\n"
                         "You've exceeded the maximum number of OTP verification attempts. "
                         "Please request a new OTP.",
                "sources": [],
                "followups": ["Request new OTP"],
                "guided": True,
                "otp_expired": True,
            }
        else:
            return {
                "answer": f"❌ **Verification Failed**\n\n"
                         f"{result.get('message', 'Unknown error')}\n\n"
                         f"Please try again.",
                "sources": [],
                "followups": ["Try again", "Request new OTP"],
                "guided": True,
                "verification_failed": True,
            }


def check_document_access(session_id: str) -> bool:
    """
    Check if agent has verified access to user documents.
    
    Args:
        session_id: Current session ID
    
    Returns:
        bool: True if access is granted and not expired
    """
    flow = FlowManager(session_id, "anonymous")
    
    if not flow.state.get("_otp_verified"):
        return False
    
    # Check if access has expired (30 minutes)
    expires_at = flow.state.get("_otp_expires_at")
    if expires_at:
        from datetime import datetime
        try:
            expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            now = datetime.now(expires.tzinfo)
            if now > expires:
                # Access expired
                flow.state["_otp_verified"] = False
                flow.save()
                return False
        except Exception as e:
            print(f"[ERROR] Failed to parse expiry time: {e}")
            return False
    
    return True

