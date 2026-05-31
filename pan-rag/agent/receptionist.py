# agent/receptionist.py
import re
from agent.service_flows import detect_service, get_service, SERVICES
from agent.flow_manager import FlowManager
from agent.user_profile import prefill_flow_from_profile, save_flow_to_profile
from agent.document_access import request_document_access, verify_document_access


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


def _display_user_profile(user_id: str, flow: FlowManager, account_email: str = "", session_id: str = "") -> dict:
    """
    Display all information collected about the user from profile, current flow, and recent conversations.
    """
    from agent.user_profile import get_user_profile
    from memory.memory_manager import MemoryManager
    
    # Collect information from multiple sources
    profile = get_user_profile(user_id) if user_id else None
    flow_state = flow.state
    
    # Also check recent conversation history for mentioned details
    memory = MemoryManager()
    recent_context = memory.get_cached_context(session_id, user_id) if session_id else ""
    
    # Build the display
    lines = ["Here's what I know about you so far: 📋", ""]
    has_info = False
    
    # Personal Details
    personal_details = []
    
    # Full name (from flow or profile)
    full_name = flow_state.get("full_name") or (profile.get("full_name") if profile else None)
    if full_name:
        personal_details.append(f"**Full name:** {full_name}")
        has_info = True
    
    # Mother's name (from flow or profile)
    mother_name = flow_state.get("mother_name") or (profile.get("mother_name") if profile else None)
    if mother_name:
        personal_details.append(f"**Mother's name:** {mother_name}")
        has_info = True
    
    # Email (from flow, profile, or account)
    email = flow_state.get("email") or (profile.get("email") if profile else None) or account_email
    if email:
        personal_details.append(f"**Email:** {email}")
        has_info = True
    
    # Phone (from flow or profile)
    phone = flow_state.get("phone") or (profile.get("phone") if profile else None)
    if phone:
        personal_details.append(f"**Phone:** {phone}")
        has_info = True
    
    # Annual income (from flow or profile)
    salary = flow_state.get("salary") or (profile.get("annual_income") if profile else None)
    if salary:
        personal_details.append(f"**Annual income:** {salary}")
        has_info = True
    
    if personal_details:
        lines.append("**Personal Details:**")
        lines.extend(personal_details)
        lines.append("")
    
    # PAN Application Preferences
    pan_prefs = []
    
    # Get preferences from flow or profile
    pan_preferences = profile.get("pan_preferences", {}) if profile else {}
    if isinstance(pan_preferences, str):
        try:
            import json
            pan_preferences = json.loads(pan_preferences)
        except:
            pan_preferences = {}
    
    submission_mode = flow_state.get("submission_mode") or pan_preferences.get("submission_mode")
    if submission_mode:
        pan_prefs.append(f"**Submission mode:** {submission_mode}")
        has_info = True
    
    delivery_mode = flow_state.get("delivery_mode") or pan_preferences.get("delivery_mode")
    if delivery_mode:
        delivery_text = "Physical + e-PAN" if delivery_mode == "physical_and_soft" else "e-PAN only" if delivery_mode == "soft_only" else delivery_mode
        pan_prefs.append(f"**PAN delivery:** {delivery_text}")
        has_info = True
    
    aadhaar_photo = flow_state.get("aadhaar_photo")
    if aadhaar_photo is None and pan_preferences:
        aadhaar_photo = pan_preferences.get("aadhaar_photo")
    if aadhaar_photo is not None:
        pan_prefs.append(f"**Aadhaar photo on PAN:** {'Yes' if aadhaar_photo else 'No'}")
        has_info = True
    
    source_of_income = flow_state.get("source_of_income") or pan_preferences.get("source_of_income")
    if source_of_income:
        if isinstance(source_of_income, list):
            source_of_income = ", ".join(source_of_income)
        pan_prefs.append(f"**Source of income:** {source_of_income}")
        has_info = True
    
    address_for_comm = flow_state.get("address_for_comm") or pan_preferences.get("address_for_comm")
    if address_for_comm:
        pan_prefs.append(f"**Address for communication:** {address_for_comm}")
        has_info = True
    
    residential_status = flow_state.get("residential_status") or pan_preferences.get("residential_status")
    if residential_status:
        pan_prefs.append(f"**Residential status:** {residential_status}")
        has_info = True
    
    rep_assessee = flow_state.get("rep_assessee")
    if rep_assessee is None and pan_preferences:
        rep_assessee = pan_preferences.get("rep_assessee")
    if rep_assessee is not None:
        pan_prefs.append(f"**Representative Assessee:** {'Yes' if rep_assessee else 'No'}")
        has_info = True
    
    if pan_prefs:
        lines.append("**PAN Application Preferences:**")
        lines.extend(pan_prefs)
        lines.append("")
    
    # Check if there's an active or incomplete flow
    if flow.has_active_flow():
        current_step = flow.get_current_step()
        service_id = flow_state.get("service_id")
        if service_id:
            lines.append("**Current Application Status:**")
            lines.append(f"You have an in-progress application at step: **{current_step}**")
            lines.append("")
            has_info = True
    
    # If no information found
    if not has_info:
        # Check if there's any conversation history
        if recent_context and len(recent_context) > 50:
            return {
                "answer": "I can see we've chatted before, but I don't have any saved details yet. As we continue our conversation and you share information, I'll remember it to help you better.\n\nWould you like to start a PAN application or ask me anything about PAN services?",
                "sources": [],
                "followups": ["Apply for new PAN", "Check PAN status", "Link Aadhaar with PAN"],
                "guided": False,
            }
        else:
            return {
                "answer": "I don't have any information about you yet. As we chat and you share details, I'll remember them to make our conversations more helpful.\n\nWould you like to start a PAN application or ask me anything about PAN services?",
                "sources": [],
                "followups": ["Apply for new PAN", "Check PAN status", "Link Aadhaar with PAN"],
                "guided": False,
            }
    
    # Add footer
    lines.append("---")
    lines.append("This information is saved securely and will be used to help you with PAN services.")
    lines.append("\nWould you like to continue with your application or start a new one?")
    
    return {
        "answer": "\n".join(lines),
        "sources": [],
        "followups": ["Continue application", "Start new application", "Check PAN status"],
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
    flow = FlowManager(session_id)
    
    # ── Prefill flow from user profile on first interaction ──────
    # Load saved user details from previous sessions to personalize
    if user_id and not flow.has_active_flow() and not flow.state.get("_profile_loaded"):
        flow.state = prefill_flow_from_profile(user_id, flow.state)
        flow.state["_profile_loaded"] = True
        flow.save()

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
    _show_profile = re.compile(
        r"\b(show|tell|what|display|list)\s+(me\s+)?(what|everything|all|info|information|details|data)\s+"
        r"(you\s+)?(know|have|collected|saved|stored|remember)\s+(about\s+me|on\s+me|for\s+me)",
        re.IGNORECASE
    )
    if _show_profile.search(question):
        return _display_user_profile(user_id, flow, account_email, session_id)
    
    # ── Handle direct questions about saved information ──────────
    # e.g., "what is my name", "what is my mother name", "what is my email"
    _direct_info_query = re.compile(
        r"\b(what|whats|tell\s+me)\s+(is|are)\s+(my|the)\s+(name|mother|email|salary|income|full\s+name|mother'?s?\s+name)",
        re.IGNORECASE
    )
    if _direct_info_query.search(question) and user_id:
        from agent.user_profile import get_user_profile
        profile = get_user_profile(user_id)
        
        # Check what information they're asking for
        lower_q = question.lower()
        
        if "mother" in lower_q:
            mother_name = flow.state.get("mother_name") or (profile.get("mother_name") if profile else None)
            if mother_name:
                return {
                    "answer": f"Your mother's name is **{mother_name}**.",
                    "sources": [],
                    "followups": ["Show me what you know about me", "Apply for new PAN"],
                    "guided": False,
                }
            else:
                return {
                    "answer": "I don't have your mother's name on record yet. Would you like to provide it?",
                    "sources": [],
                    "followups": ["Show me what you know about me", "Continue with PAN application"],
                    "guided": False,
                }
        
        elif "email" in lower_q:
            email = flow.state.get("email") or (profile.get("email") if profile else None) or account_email
            if email:
                return {
                    "answer": f"Your email is **{email}**.",
                    "sources": [],
                    "followups": ["Show me what you know about me", "Apply for new PAN"],
                    "guided": False,
                }
        
        elif "salary" in lower_q or "income" in lower_q:
            salary = flow.state.get("salary") or (profile.get("annual_income") if profile else None)
            if salary:
                return {
                    "answer": f"Your annual income is **{salary}**.",
                    "sources": [],
                    "followups": ["Show me what you know about me", "Apply for new PAN"],
                    "guided": False,
                }
        
        elif "name" in lower_q and "mother" not in lower_q:
            full_name = flow.state.get("full_name") or (profile.get("full_name") if profile else None)
            if full_name:
                return {
                    "answer": f"Your full name is **{full_name}**.",
                    "sources": [],
                    "followups": ["Show me what you know about me", "Apply for new PAN"],
                    "guided": False,
                }
            else:
                return {
                    "answer": "I don't have your name on record yet. Would you like to provide it?",
                    "sources": [],
                    "followups": ["Show me what you know about me", "Continue with PAN application"],
                    "guided": False,
                }
        
        # If we couldn't find the specific info, show full profile
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
            # 1. Load from Supabase profile
            flow.state = prefill_flow_from_profile(user_id, flow.state)
            flow.state["_profile_loaded"] = True

            # 2. Also parse user_context (Node sends this every request — more up-to-date)
            if user_context:
                _prefill_from_user_context(flow, user_context)

            # Start the flow (sets service_id + step sequence, resets current_step)
            flow.start_flow(service_id)

            # Fast-forward past all steps that are already answered
            result = _smart_advance_to_first_missing(flow, language, user_id)
            if result:
                return result
            # All steps answered — go straight to confirmation
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

    def _step_answered(step: str) -> bool:
        s = flow.state
        if step == "applicant_type":
            return bool(s.get("applicant_type"))
        if step == "submission_mode":
            return bool(s.get("submission_mode"))
        if step == "delivery_mode":
            return bool(s.get("delivery_mode"))
        if step == "aadhaar_photo":
            return s.get("aadhaar_photo") is not None   # False is a valid answer
        if step == "source_of_income":
            return bool(s.get("source_of_income"))
        if step == "address_for_comm":
            return bool(s.get("address_for_comm"))
        if step == "residential_status":
            return bool(s.get("residential_status"))
        if step == "rep_assessee":
            return s.get("rep_assessee") is not None    # False is a valid answer
        if step == "details_collection":
            missing = _missing_details(flow)
            return len(missing) == 0
        # confirmation, documents, summary — never skip
        return False

    # Walk through steps and skip answered ones
    for step in steps:
        if step in ("confirmation", "documents", "summary"):
            # Always stop here — user must confirm/upload
            flow.state["current_step"] = step
            flow.save()
            if step == "confirmation":
                return _build_confirmation(flow)
            return _ask_step(flow)

        if not _step_answered(step):
            # This step needs an answer — set it as current and ask
            flow.state["current_step"] = step
            flow.save()
            return _ask_step(flow)

    # All steps answered — go to confirmation
    flow.state["current_step"] = "confirmation"
    flow.save()
    return None   # caller will call _build_confirmation


def _start_flow_response(flow: FlowManager, language: str) -> dict:
    step = flow.get_current_step()
    service = get_service(flow.state["service_id"])
    name = service["name"]

    if step == "applicant_type":
        opts = {
            "type": "radio", "label": "Applicant type", "field": "applicant_type",
            "choices": ["Indian Citizen", "Indian Company / HUF / Firm", "Foreign Citizen / NRI / Overseas"],
        }
        return {
            "answer"  : f"Let's get your **{name}** sorted.\n\nWhich of these fits you?",
            "sources" : [], "followups": [], "guided": True, "step": step, "options": opts,
        }

    return _ask_step(flow)


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
        return {
            "answer": "Great! Now let's collect your details.\n\n" + _ask_details_collection(flow)["answer"],
            "sources": [],
            "followups": [],
            "guided": True,
            "step": "details_collection",
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


def _ask_step(flow: FlowManager) -> dict:
    """Return the question + options for the current step."""
    step = flow.get_current_step()

    # ── applicant_type ────────────────────────────────────────────
    if step == "applicant_type":
        opts = {
            "type": "radio", "label": "Applicant type", "field": "applicant_type",
            "choices": ["Indian Citizen", "Indian Company / HUF / Firm", "Foreign Citizen / NRI / Overseas"],
        }
        service = get_service(flow.state.get("service_id", ""))
        name = service.get("name", "PAN Application")
        return {
            "answer": f"Let's get your **{name}** sorted.\n\nWhich of these fits you?",
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
            "type": "checkbox", "label": "Source of Income", "field": "source_of_income",
            "choices": ["Salary", "Income from Business / Profession", "Income from House property",
                        "Income from Other sources", "Capital Gains", "No income"],
        }
        return {"answer": "**Please select your Source of Income** (select all that apply):", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

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
        return {"answer": "I'll need your existing **PAN number** first (10-character code, e.g. **ABCDE1234F**).", "sources": [], "followups": [], "guided": True, "step": step}

    elif step == "aadhaar_number":
        return {"answer": "Now I need your **Aadhaar number** (12 digits).", "sources": [], "followups": [], "guided": True, "step": step}

    return {"answer": "Let's continue — please provide the next detail.", "sources": [], "followups": [], "guided": True, "step": step}


def _continue_flow(flow: FlowManager, user_input: str, language: str, user_id: str = None) -> dict:
    step = flow.get_current_step()
    inp  = user_input.strip()

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
        _foreign = re.compile(r"\b(3|three|foreign|nri|non.?resident|overseas|oci|pio|abroad|expat|us\s+citizen|uk\s+citizen)\b", re.IGNORECASE)
        _entity  = re.compile(r"\b(2|two|company|huf|firm|llp|trust|partnership|hindu\s+undivided|corporate)\b", re.IGNORECASE)
        _indian  = re.compile(r"\b(1|one|indian\s+citizen|indian|india|individual)\b", re.IGNORECASE)

        if _foreign.search(inp):
            flow.state["service_id"] = None; flow.state["complete"] = True; flow.save()
            return None
        elif _entity.search(inp):
            flow.state["service_id"] = None; flow.state["complete"] = True; flow.save()
            return None
        elif _indian.search(inp):
            flow.state["applicant_type"] = "indian_citizen"
            flow.advance_step()
            flow.save()
            return _ask_step(flow)
        else:
            opts = {"type": "radio", "label": "Applicant type", "field": "applicant_type",
                    "choices": ["Indian Citizen", "Indian Company / HUF / Firm", "Foreign Citizen / NRI / Overseas"]}
            return {"answer": "Could you pick one of these?", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Submission mode (Q2) ─────────────────────────────────────
    elif step == "submission_mode":
        _map = {
            "1": "Aadhaar-based Online (eKYC)",
            "aadhaar": "Aadhaar-based Online (eKYC)",
            "ekyc": "Aadhaar-based Online (eKYC)",
            "2": "Upload scanned docs & eSign",
            "upload": "Upload scanned docs & eSign",
            "scan": "Upload scanned docs & eSign",
            "esign": "Upload scanned docs & eSign",
            "3": "Fill online + courier physical form",
            "courier": "Fill online + courier physical form",
            "physical": "Fill online + courier physical form",
            "post": "Fill online + courier physical form",
        }
        key = inp.lower().split()[0] if inp else ""
        matched = _map.get(key) or next((v for k, v in _map.items() if k in inp.lower()), None)
        if matched:
            flow.state["submission_mode"] = matched
            # Save this answer for future reuse
            flow.state["_saved_submission_mode"] = matched
            return _advance_after_answer(flow, user_id)
        opts = {"type": "radio", "label": "Submission mode", "field": "submission_mode",
                "choices": ["Aadhaar-based Online (eKYC)", "Upload scanned docs & eSign", "Fill online + courier physical form"]}
        return {"answer": "Please select one of the submission modes:", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Delivery mode (Q2b) ──────────────────────────────────────
    elif step == "delivery_mode":
        _physical = re.compile(r"\b(1|physical|home|both|hard\s*copy)\b", re.IGNORECASE)
        _soft     = re.compile(r"\b(2|soft|email|only\s+soft|e.?pan|digital)\b", re.IGNORECASE)

        if _physical.search(inp):
            flow.state["delivery_mode"] = "physical_and_soft"
            # Save this answer for future reuse
            flow.state["_saved_delivery_mode"] = "Physical copy to home + soft copy on email (Fees applicable)"
            next_q = _advance_after_answer(flow)
            # Show fee table for physical+soft
            next_q["answer"] = _FEE_PHYSICAL.strip() + "\n\n---\n\n" + next_q["answer"]
            return next_q
        elif _soft.search(inp):
            flow.state["delivery_mode"] = "soft_only"
            # Save this answer for future reuse
            flow.state["_saved_delivery_mode"] = "Only soft copy on email (Fees applicable)"
            next_q = _advance_after_answer(flow)
            next_q["answer"] = _FEE_SOFT.strip() + "\n\n---\n\n" + next_q["answer"]
            return next_q
        else:
            opts = {"type": "radio", "label": "PAN delivery", "field": "delivery_mode",
                    "choices": ["Physical copy to home + soft copy on email (Fees applicable)", "Only soft copy on email (Fees applicable)"]}
            return {"answer": "**How do you want your PAN card to be delivered?**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Aadhaar photo consent (Q3) ───────────────────────────────
    elif step == "aadhaar_photo":
        _yes = re.compile(r"^(yes|y|yeah|yep|agree|ok|okay|sure)$", re.IGNORECASE)
        _no  = re.compile(r"^(no|nope|nah|disagree|decline)$", re.IGNORECASE)
        if _yes.match(inp):
            flow.state["aadhaar_photo"] = True
            # Save this answer for future reuse
            flow.state["_saved_aadhaar_photo"] = True
            return _advance_after_answer(flow, user_id)
        elif _no.match(inp):
            flow.state["aadhaar_photo"] = False
            # Save this answer for future reuse
            flow.state["_saved_aadhaar_photo"] = False
            return _advance_after_answer(flow, user_id)
        else:
            opts = {"type": "radio", "label": "Aadhaar photo consent", "field": "aadhaar_photo", "choices": ["Yes", "No"]}
            return {"answer": "Please select **Yes** or **No** for Aadhaar photo on PAN card:", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Source of income (Q4) ────────────────────────────────────
    elif step == "source_of_income":
        _SOI = [
            (re.compile(r"\b(salary|salaried|1)\b", re.IGNORECASE),                          "Salary"),
            (re.compile(r"\b(business|profession|self.?employed|freelanc|2)\b", re.IGNORECASE), "Income from Business / Profession"),
            (re.compile(r"\b(house\s+property|rental|rent|3)\b", re.IGNORECASE),              "Income from House property"),
            (re.compile(r"\b(other\s+sources?|4)\b", re.IGNORECASE),                          "Income from Other sources"),
            (re.compile(r"\b(capital\s+gains?|5)\b", re.IGNORECASE),                          "Capital Gains"),
            (re.compile(r"\b(no\s+income|unemployed|student|homemaker|housewife|retired|fresher|6)\b", re.IGNORECASE), "No income"),
        ]
        matched = []
        for pat, label in _SOI:
            if pat.search(inp):
                matched.append(label)
        if matched:
            flow.state["source_of_income"] = ", ".join(matched)
            # Save this answer for future reuse
            flow.state["_saved_source_of_income"] = matched  # Save as list
            return _advance_after_answer(flow, user_id)
        opts = {"type": "checkbox", "label": "Source of Income", "field": "source_of_income",
                "choices": ["Salary", "Income from Business / Profession", "Income from House property",
                            "Income from Other sources", "Capital Gains", "No income"]}
        return {"answer": "**Please select your Source of Income:**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Address for communication (Q5) ───────────────────────────
    elif step == "address_for_comm":
        _map = {
            "residence": "Residence", "home": "Residence", "1": "Residence",
            "office": "Office", "work": "Office", "2": "Office",
            "representative": "Representative Assessee (RA)", "ra": "Representative Assessee (RA)", "3": "Representative Assessee (RA)",
        }
        key = inp.lower().strip()
        matched = _map.get(key) or next((v for k, v in _map.items() if k in key), None)
        if matched:
            flow.state["address_for_comm"] = matched
            # Save this answer for future reuse
            flow.state["_saved_address_for_comm"] = matched
            return _advance_after_answer(flow, user_id)
        hint = "**Important instructions for e-KYC (Individual):**\n1. Address from Aadhaar card will be used as residence address.\n2. PAN card dispatched to Aadhaar address.\n3. If Aadhaar address exceeds IT Dept length limit, e-KYC won't be available."
        opts = {"type": "radio", "label": "Address for Communication", "field": "address_for_comm",
                "choices": ["Residence", "Office", "Representative Assessee (RA)"], "hint": hint}
        return {"answer": "**Address for Communication** — Please tick as applicable:", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Residential status (Q6) ──────────────────────────────────
    elif step == "residential_status":
        _map = {
            "resident": "Resident", "1": "Resident",
            "non-resident": "Non-resident", "non resident": "Non-resident", "nri": "Non-resident", "2": "Non-resident",
            "not ordinarily": "Resident but not ordinarily resident",
            "rnor": "Resident but not ordinarily resident", "3": "Resident but not ordinarily resident",
        }
        key = inp.lower().strip()
        matched = _map.get(key) or next((v for k, v in _map.items() if k in key), None)
        if matched:
            flow.state["residential_status"] = matched
            # Save this answer for future reuse
            flow.state["_saved_residential_status"] = matched
            return _advance_after_answer(flow, user_id)
        opts = {"type": "radio", "label": "Residential Status", "field": "residential_status",
                "choices": ["Resident", "Non-resident", "Resident but not ordinarily resident"]}
        return {"answer": "**What is your Residential Status?**", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Representative Assessee (Q7) ─────────────────────────────
    elif step == "rep_assessee":
        _yes = re.compile(r"^(yes|y|yeah|yep|yup|sure|ok|okay)$", re.IGNORECASE)
        _no  = re.compile(r"^(no|nope|nah|n)$", re.IGNORECASE)
        if _yes.match(inp):
            flow.state["rep_assessee"] = True
            # Save this answer for future reuse
            flow.state["_saved_rep_assessee"] = True
            return _advance_after_answer(flow, user_id)
        elif _no.match(inp):
            flow.state["rep_assessee"] = False
            # Save this answer for future reuse
            flow.state["_saved_rep_assessee"] = False
            return _advance_after_answer(flow, user_id)
        else:
            opts = {"type": "radio", "label": "Representative Assessee", "field": "rep_assessee",
                    "choices": ["Yes", "No"]}
            return {"answer": "Please select **Yes** or **No** — are you appointing a Representative Assessee?", "sources": [], "followups": [], "guided": True, "step": step, "options": opts}

    # ── Details collection (Q8) ───────────────────────────────────
    elif step == "details_collection":
        # ── FIRST: Check for cancellation/restart intent BEFORE any email logic ──
        if re.search(r"\b(apply|start|begin|new|pan|cancel|stop|quit|restart)\b", inp.lower()):
            # User wants to cancel or start over
            flow.state["service_id"] = None
            flow.state["complete"] = True
            flow.save()
            return {
                "answer": "Got it! I've cancelled the current application. Feel free to start fresh whenever you're ready - just say something like \"I want to apply for a new PAN card\".",
                "sources": [],
                "followups": [],
                "guided": False,
                "close_form": True,
            }
        
        # ── Handle email_confirm response ─────────────────────────
        # "Yes, use X@..." → use account email
        # "No, use a different one" → set pending flag, ask for input
        if flow.state.get("_email_confirm_asked") and not flow.state.get("email"):
            _use_acct = re.compile(r"^yes\b", re.IGNORECASE)
            _use_new  = re.compile(r"^no\b", re.IGNORECASE)
            
            if _use_acct.match(inp):
                flow.state["email"] = flow.state.get("_account_email", "")
                flow.state["email_source"] = "account"
                flow.state["_email_input_pending"] = False
                flow.save()
                # Continue to check other missing details
                missing = _missing_details(flow)
                if not missing:
                    flow.advance_step()
                    flow.save()
                    return _build_confirmation(flow)
                return _ask_details_collection(flow)
            elif _use_new.match(inp):
                flow.state["_email_input_pending"] = True
                flow.save()
                return {
                    "answer": "Please enter the email address you'd like to use for PAN correspondence (or type **cancel** to start over):",
                    "sources": [], "followups": [], "guided": True,
                    "step": "details_collection",
                    "options": {"type": "email_input"},
                }
            elif flow.state.get("_email_input_pending"):
                # User typed their email into the inline input box
                email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", inp)
                if email_match:
                    flow.state["email"] = email_match.group(0).lower()
                    flow.state["email_source"] = "new"
                    flow.state["_email_input_pending"] = False
                    flow.save()
                    # Continue to check other missing details
                    missing = _missing_details(flow)
                    if not missing:
                        flow.advance_step()
                        flow.save()
                        return _build_confirmation(flow)
                    return _ask_details_collection(flow)
                else:
                    # IMPROVED: More helpful error message with option to cancel
                    return {
                        "answer": "That doesn't look like a valid email. Please enter a valid email address (e.g. yourname@example.com), or type **cancel** to start over:",
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
        return _ask_details_collection(flow)

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
            r"^(yes|y|yeah|yep|yup|sure|ok|okay|proceed|confirm|looks\s+good|correct|all\s+good|go\s+ahead|yes,?\s*proceed)$",
            re.IGNORECASE
        )
        _no = re.compile(
            r"^(no|nope|nah|n|change|modify|update|edit|wrong|incorrect|fix"
            r"|no,?\s*i\s+need\s+to\s+change\s+something"
            r"|change\s+something"
            r"|i\s+want\s+to\s+change"
            r"|i\s+need\s+to\s+change).*$",
            re.IGNORECASE
        )

        # ── PRIORITY 1: User is providing the new value for a pending field ────
        # This must be checked BEFORE _no.match() to avoid "No" being treated as "change something"
        if flow.state.get("pending_modification") and flow.state["pending_modification"] != "__awaiting__":
            field = flow.state["pending_modification"]
            print(f"[DEBUG] Applying field update: field={field}, inp={inp!r}, user_input={user_input!r}")
            print(f"[DEBUG] Before update: {field}={flow.state.get(field)}")
            _apply_field_update(flow, field, inp, user_input)
            print(f"[DEBUG] After update: {field}={flow.state.get(field)}")
            flow.state["pending_modification"] = None
            flow.save()
            print(f"[DEBUG] Saved flow state, building confirmation...")

            # ── For delivery_mode: show the fee table before the confirmation ──
            if field == "delivery_mode":
                confirmation = _build_confirmation(flow)
                new_mode = flow.state.get("delivery_mode")
                if new_mode == "physical_and_soft":
                    fee_block = _FEE_PHYSICAL.strip()
                elif new_mode == "soft_only":
                    fee_block = _FEE_SOFT.strip()
                else:
                    fee_block = ""
                if fee_block:
                    confirmation["answer"] = fee_block + "\n\n---\n\n" + confirmation["answer"]
                return confirmation

            confirmation = _build_confirmation(flow)
            print(f"[DEBUG] Confirmation built, checking if aadhaar_photo is in answer...")
            if "Aadhaar photo on PAN" in confirmation.get("answer", ""):
                print(f"[DEBUG] Confirmation contains aadhaar_photo line")
            return confirmation

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
            
            # Build the document list response directly (skip the "reply Yes" prompt)
            doc_text = _ask_for_documents(flow)
            return {
                "answer": doc_text,
                "sources": [], "followups": [], "guided": True,
                "step": "documents",
                "flow_confirmed": True,
                "flow_data": {
                    # Personal details
                    "full_name":          flow.state.get("full_name"),
                    "mother_name":        flow.state.get("mother_name"),
                    "email":              flow.state.get("email"),
                    "salary":             flow.state.get("salary"),
                    # PAN preferences — ALL of them
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

        # ── PRIORITY 3: User clicked "Change something" or said what to change ──
        elif _no.match(inp):
            # NEW: Try to extract multiple field updates from a single message
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
                if s.get("full_name"):    lines.append(f"- **Full name** — currently: *{s['full_name']}*")
                if s.get("mother_name"):  lines.append(f"- **Mother's name** — currently: *{s['mother_name']}*")
                if s.get("email"):        lines.append(f"- **Email** — currently: *{s['email']}*")
                if s.get("salary"):       lines.append(f"- **Annual income** — currently: *{s['salary']}*")
                lines.append(f"- **Submission mode** — currently: *{s.get('submission_mode', '—')}*")
                lines.append(f"- **PAN delivery** — currently: *{'Physical + e-PAN' if s.get('delivery_mode') == 'physical_and_soft' else 'e-PAN only' if s.get('delivery_mode') else '—'}*")
                lines.append(f"- **Aadhaar photo on PAN** — currently: *{'Yes' if s.get('aadhaar_photo') else 'No' if s.get('aadhaar_photo') is not None else '—'}*")
                lines.append(f"- **Source of income** — currently: *{s.get('source_of_income', '—')}*")
                lines.append(f"- **Address for communication** — currently: *{s.get('address_for_comm', '—')}*")
                lines.append(f"- **Residential status** — currently: *{s.get('residential_status', '—')}*")
                lines.append(f"- **Representative Assessee** — currently: *{'Yes' if s.get('rep_assessee') else 'No' if s.get('rep_assessee') is not None else '—'}*")
                lines.append("\n**You can change multiple fields at once!**")
                lines.append("Examples:")
                lines.append("- *\"change my name to John and salary to 5 lakh\"*")
                lines.append("- *\"update email to john@example.com and mother name to Mary\"*")
                lines.append("- Or just tell me one field: *\"change my name\"*")
                flow.state["pending_modification"] = "__awaiting__"
                flow.save()
                return {
                    "answer": "\n".join(lines),
                    "sources": [], "followups": [], "guided": True, "step": step,
                }

        # ── PRIORITY 4: User is responding to "what to change" prompt ──────────
        elif flow.state.get("pending_modification") == "__awaiting__":
            # NEW: Try to extract multiple field updates from a single message
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
                    # Pattern 1: "my mother name is X" or "mother name is X" or "mom name is X"
                    mom_match = re.search(r"(?:my\s+)?(?:mother|mom)(?:'?s)?\s+name\s+is\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)", user_input, re.IGNORECASE)
                    if not mom_match:
                        # Pattern 2: "my mother name X" (missing "is")
                        mom_match = re.search(r"(?:my\s+)?(?:mother|mom)(?:'?s)?\s+name\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?:\s*$|\s+and\b|\s*,)", user_input, re.IGNORECASE)
                    
                    if mom_match:
                        candidate = mom_match.group(1).strip()
                        print(f"[DEBUG] Extracted mother name candidate: {candidate!r}")
                        # Split and filter out common words
                        words = candidate.split()
                        filtered_words = [w for w in words if w.lower() not in ('my', 'mother', 'mothers', 'mom', 'moms', 'name', 'is', 'the')]
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
                    # Try to extract salary - handle typos in units
                    salary_match = re.search(
                        r"(?:salary|income|earn(?:ing)?s?|annual|per\s+year|p\.?a\.?)\s*(?:is\s*)?[:\-]?\s*"
                        r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|laksh|laks|lakhs|laakh|lac|lacs|l\b|k\b|thousand|crore|cr\b)?",
                        inp.lower()
                    )
                    if salary_match:
                        raw_num = salary_match.group(1).replace(",", "")
                        unit_str = (salary_match.group(2) or "").lower().strip() if salary_match.lastindex and salary_match.lastindex >= 2 else ""
                        try:
                            num = float(raw_num)
                            # Normalize unit typos
                            if unit_str in ("lakh", "laksh", "laks", "lakhs", "laakh", "lac", "lacs", "l"):
                                num *= 100_000
                            elif unit_str in ("k", "thousand"):
                                num *= 1_000
                            elif unit_str in ("crore", "cr"):
                                num *= 10_000_000
                            formatted = f"₹{num:,.0f}" if num >= 100_000 else f"₹{int(num):,}"
                            flow.state["salary"] = formatted
                            flow.state["pending_modification"] = None
                            flow.save()
                            print(f"[DEBUG] ✓ Updated salary to: {formatted}")
                            return _build_confirmation(flow)
                        except ValueError:
                            print(f"[DEBUG] ✗ Salary parsing failed")
                
                # If value not found in message, ask for it
                print(f"[DEBUG] Value not extracted inline, asking for field: {field}")
                flow.state["pending_modification"] = field
                flow.save()
                return _ask_for_field(flow, field)
            else:
                print(f"[DEBUG] No field detected from input")
                return {
                    "answer": "I didn't catch that. Which field would you like to change? (e.g. *\"name\"*, *\"email\"*, *\"salary\"*, *\"mother's name\"*)",
                    "sources": [], "followups": [], "guided": True, "step": step,
                }

        # Fallback — re-show confirmation
        return _build_confirmation(flow)

    # ── Documents ────────────────────────────────────────────────
    elif step == "documents":
        if _is_off_topic_during_flow(inp): return None
        _confirm = re.compile(r"^(yes|y|yeah|yep|yup|sure|ok|okay|ready|let'?s\s+go|proceed|go\s+ahead|upload\s+now)$", re.IGNORECASE)
        if _confirm.match(inp):
            return {"answer": "Great! The upload panel is now open. Please upload your documents one at a time.", "sources": [], "followups": [], "guided": True, "step": step, "open_upload": True}
        return {"answer": "Whenever you're ready, reply **Yes** and I'll open the upload panel.\n\n" + _ask_for_documents(flow), "sources": [], "followups": [], "guided": True, "step": step}

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
    flow = FlowManager(session_id)
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

def _ask_for_documents(flow: FlowManager) -> str:
    pending = flow.get_pending_docs()
    if not pending:
        return "All documents are in — you're good to go!"

    DOC_WHY = {
        "aadhaar":          "Used for eKYC and Aadhaar-based identity verification.",
        "driving_license":  "Accepted as proof of identity and address.",
        "photograph":       "Printed on your physical PAN card for visual identity verification.",
        "identity_proof":   "Mandatory KYC — confirms who you are.",
        "address_proof":    "Your address is permanently recorded on the PAN database.",
        "dob_proof":        "Your date of birth is permanently linked to your PAN.",
        "correction_proof": "Required to verify the change and prevent fraud.",
    }

    lines = ["Here's what I need from you:\n"]
    for i, doc in enumerate(pending, 1):
        optional = " *(optional)*" if doc.get("optional") else ""
        options  = ", ".join(doc["options"])
        why      = DOC_WHY.get(doc["key"], "Required for your PAN application.")
        lines.append(f"### {i}. {doc['label']}{optional}")
        lines.append(f"> {why}")
        lines.append(f"Accepted: {options}\n")

    lines.append("---")
    lines.append("Ready to upload? Reply **Yes** and I'll open the upload panel.")
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
    if not flow.state.get("mother_name"):
        missing.append("mother_name")
    if not flow.state.get("email"):
        missing.append("email")
    if not flow.state.get("salary"):
        missing.append("salary")
    return missing


def _ask_details_collection(flow: FlowManager) -> dict:
    """Build the prompt asking for whichever details are still missing."""
    missing = _missing_details(flow)
    state   = flow.state

    # ── Email confirmation sub-step ───────────────────────────────
    # If email is still missing and we have the account email, show a
    # dedicated Yes/No card before asking for the other fields.
    account_email = state.get("_account_email")
    if "email" in missing and account_email and not state.get("_email_confirm_asked"):
        state["_email_confirm_asked"] = True
        flow.save()
        opts = {
            "type": "email_confirm",
            "account_email": account_email,
            "choices": [f"Yes, use {account_email}", "No, use a different one"],
        }
        return {
            "answer": "**Email for PAN correspondence** — should I use your account email?",
            "sources": [], "followups": [], "guided": True,
            "step": "details_collection", "options": opts,
        }

    # Build a status block showing what's already collected
    collected_lines = []
    if state.get("full_name"):
        collected_lines.append(f"✅ **Full name:** {state['full_name']}")
    if state.get("mother_name"):
        collected_lines.append(f"✅ **Mother's name:** {state['mother_name']}")
    if state.get("email"):
        collected_lines.append(f"✅ **Email:** {state['email']}")
    if state.get("salary"):
        collected_lines.append(f"✅ **Annual income:** {state['salary']}")

    collected_block = ("\n".join(collected_lines) + "\n\n") if collected_lines else ""

    # Build the ask for missing fields
    ask_parts = []
    if "full_name" in missing:
        ask_parts.append("- **Full name** exactly as it appears on your Aadhaar card")
    if "mother_name" in missing:
        ask_parts.append("- **Mother's full name** (as per official records)")
    if "email" in missing:
        ask_parts.append("- **Email address** for PAN correspondence")
    if "salary" in missing:
        ask_parts.append("- **Annual income / salary** (per year, not monthly — e.g. ₹5,00,000 or 500000)")

    # If no missing fields, this shouldn't happen (should advance to confirmation)
    # But if it does, show collected info only
    if not ask_parts:
        answer = (
            f"{collected_block}"
            f"Perfect! I have all the details I need.\n\n"
            f"Let me show you the confirmation..."
        )
    elif collected_lines:
        ask_block = "\n".join(ask_parts)
        answer = (
            f"{collected_block}"
            f"Almost there! I still need:\n\n{ask_block}"
        )
    else:
        ask_block = "\n".join(ask_parts)
        answer = (
            f"Great! Now I need a few personal details to fill in your application.\n\n"
            f"Please provide:\n\n{ask_block}"
        )

    return {
        "answer": answer,
        "sources": [], "followups": [], "guided": True, "step": "details_collection",
    }


def _extract_multiple_field_updates(flow: FlowManager, inp: str, raw: str) -> bool:
    """
    Extract multiple field updates from a single message.
    Handles inputs like: "change my name to John and mother name to Mary and salary to 5 lakh"
    Returns True if at least one field was updated.
    """
    updated = False
    text = raw.strip()
    lower = text.lower()
    
    print(f"[DEBUG _extract_multiple_field_updates] Input: {text!r}")
    
    # ── Extract full name ─────────────────────────────────────────
    # Patterns: "name to X", "name is X", "my name X"
    name_patterns = [
        r"(?:my\s+)?(?:full\s+)?name\s+(?:to|is)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        r"(?:change|update)\s+(?:my\s+)?(?:full\s+)?name\s+(?:to\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
    ]
    for pattern in name_patterns:
        name_match = re.search(pattern, text, re.IGNORECASE)
        if name_match:
            candidate = name_match.group(1).strip()
            # Filter out common words
            words = candidate.split()
            filtered_words = [w for w in words if w.lower() not in ('my', 'name', 'is', 'to', 'the', 'full', 'and')]
            if filtered_words:
                candidate = ' '.join(filtered_words)
                if _is_valid_name(candidate):
                    flow.state["full_name"] = candidate
                    updated = True
                    print(f"[DEBUG] ✓ Updated full_name to: {candidate!r}")
                    break
    
    # ── Extract mother's name ─────────────────────────────────────
    # Patterns: "mother name to X", "mother name is X", "mom name X"
    mother_patterns = [
        r"(?:my\s+)?(?:mother|mom)(?:'?s)?\s+name\s+(?:to|is)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
        r"(?:change|update)\s+(?:my\s+)?(?:mother|mom)(?:'?s)?\s+name\s+(?:to\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+and\b|\s*,|\s*$)",
    ]
    for pattern in mother_patterns:
        mom_match = re.search(pattern, text, re.IGNORECASE)
        if mom_match:
            candidate = mom_match.group(1).strip()
            # Filter out common words
            words = candidate.split()
            filtered_words = [w for w in words if w.lower() not in ('my', 'mother', 'mom', 'name', 'is', 'to', 'the', 'and')]
            if filtered_words:
                candidate = ' '.join(filtered_words)
                if _is_valid_name(candidate):
                    flow.state["mother_name"] = candidate
                    updated = True
                    print(f"[DEBUG] ✓ Updated mother_name to: {candidate!r}")
                    break
    
    # ── Extract email ─────────────────────────────────────────────
    # Pattern: any valid email address
    email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        flow.state["email"] = email_match.group(0).lower()
        flow.state["email_source"] = "new"
        updated = True
        print(f"[DEBUG] ✓ Updated email to: {flow.state['email']!r}")
    
    # ── Extract salary ────────────────────────────────────────────
    # Patterns: "salary to 5 lakh", "salary is 500000", "income 5,00,000"
    salary_patterns = [
        r"(?:salary|income|annual)\s+(?:to|is)\s+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|laksh|laks|lakhs|laakh|lac|lacs|l\b|k\b|thousand|crore|cr\b)?",
        r"(?:change|update)\s+(?:my\s+)?(?:salary|income)\s+(?:to\s+)?(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|laksh|laks|lakhs|laakh|lac|lacs|l\b|k\b|thousand|crore|cr\b)?",
    ]
    for pattern in salary_patterns:
        salary_match = re.search(pattern, text, re.IGNORECASE)
        if salary_match:
            raw_num = salary_match.group(1).replace(",", "")
            unit_str = (salary_match.group(2) or "").lower().strip() if salary_match.lastindex >= 2 else ""
            try:
                num = float(raw_num)
                # Normalize unit
                if unit_str in ("lakh", "laksh", "laks", "lakhs", "laakh", "lac", "lacs", "l"):
                    num *= 100_000
                elif unit_str in ("k", "thousand"):
                    num *= 1_000
                elif unit_str in ("crore", "cr"):
                    num *= 10_000_000
                formatted = f"₹{num:,.0f}" if num >= 100_000 else f"₹{int(num):,}"
                flow.state["salary"] = formatted
                updated = True
                print(f"[DEBUG] ✓ Updated salary to: {formatted!r}")
                break
            except ValueError:
                pass
    
    # ── Extract submission mode ───────────────────────────────────
    submission_keywords = {
        "aadhaar": "Aadhaar-based Online (eKYC)",
        "ekyc": "Aadhaar-based Online (eKYC)",
        "online": "Aadhaar-based Online (eKYC)",
        "upload": "Upload scanned docs & eSign",
        "scan": "Upload scanned docs & eSign",
        "esign": "Upload scanned docs & eSign",
        "courier": "Fill online + courier physical form",
        "physical": "Fill online + courier physical form",
        "post": "Fill online + courier physical form",
    }
    submission_match = re.search(r"(?:submission|submit)\s+(?:mode\s+)?(?:to|is)\s+(\w+)", text, re.IGNORECASE)
    if submission_match:
        keyword = submission_match.group(1).lower()
        if keyword in submission_keywords:
            flow.state["submission_mode"] = submission_keywords[keyword]
            updated = True
            print(f"[DEBUG] ✓ Updated submission_mode to: {flow.state['submission_mode']!r}")
    
    # ── Extract delivery mode ─────────────────────────────────────
    if re.search(r"(?:delivery|pan\s+delivery)\s+(?:to|is)\s+(?:physical|both|hard)", text, re.IGNORECASE):
        flow.state["delivery_mode"] = "physical_and_soft"
        updated = True
        print(f"[DEBUG] ✓ Updated delivery_mode to: physical_and_soft")
    elif re.search(r"(?:delivery|pan\s+delivery)\s+(?:to|is)\s+(?:soft|email|digital|e-?pan)", text, re.IGNORECASE):
        flow.state["delivery_mode"] = "soft_only"
        updated = True
        print(f"[DEBUG] ✓ Updated delivery_mode to: soft_only")
    
    # ── Extract aadhaar photo ─────────────────────────────────────
    aadhaar_photo_match = re.search(r"(?:aadhaar|aadhar)\s+photo\s+(?:to|is)\s+(yes|no)", text, re.IGNORECASE)
    if aadhaar_photo_match:
        value = aadhaar_photo_match.group(1).lower()
        flow.state["aadhaar_photo"] = (value == "yes")
        updated = True
        print(f"[DEBUG] ✓ Updated aadhaar_photo to: {flow.state['aadhaar_photo']}")
    
    print(f"[DEBUG _extract_multiple_field_updates] Updated: {updated}")
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
        'my', 'name', 'is', 'the', 'full', 'and', 'a', 'an',
        'mother', 'mothers', 'mom', 'moms', 'maa', 'amma',
        'salary', 'income', 'email', 'mail', 'annual', 'per', 'year',
    }

    def _clean_name(raw_name: str) -> str:
        words = raw_name.strip().split()
        kept = [w for w in words if w.lower() not in _STOP_WORDS]
        return ' '.join(kept).strip()

    # ── Step 3: Extract mother's name FIRST (higher specificity) ─
    if not flow.state.get("mother_name"):
        for seg in segments:
            # Patterns: "mother name is X", "mother's name X", "mom name X"
            m = re.match(
                r"(?:my\s+)?(?:mother(?:'?s)?|mom(?:'?s)?|maa|amma)\s+(?:full\s+)?name\s*(?:is\s*)?[:\-]?\s*(.+)",
                seg, re.IGNORECASE
            )
            if not m:
                # Also catch: "mother X Y" (no "name" keyword)
                m = re.match(
                    r"(?:my\s+)?(?:mother(?:'?s)?|mom(?:'?s)?)\s+(?!name\b)(.+)",
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

    # ── Step 4: Extract full name ─────────────────────────────────
    if not flow.state.get("full_name"):
        for seg in segments:
            # Skip segments that are about mother
            if re.search(r'\b(mother|mom|maa|amma)\b', seg, re.IGNORECASE):
                continue
            # Skip segments that are about salary/income/email
            if re.search(r'\b(salary|income|earn|email|mail|₹|rs\.?|inr)\b', seg, re.IGNORECASE):
                continue

            # Pattern: "my name is X" / "name is X" / "name: X"
            m = re.match(
                r"(?:my\s+)?(?:full\s+)?name\s*(?:is\s*)?[:\-]?\s*(.+)",
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
            cut = re.search(r'\b(mother|mom|salary|income|email)\b', text, re.IGNORECASE)
            if cut:
                search_text = text[:cut.start()]

            # Look for "name is X" pattern anywhere
            m = re.search(
                r"(?:my\s+)?(?:full\s+)?name\s*(?:is\s*)?[:\-]?\s*([A-Za-z][A-Za-z\s]{1,40}?)(?:\s*$|\s*,|\s+and\b)",
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
        # Try each segment independently for salary
        salary_found = False

        # Helper: parse Indian number format (5,00,000 → 500000)
        def _parse_indian_num(s: str) -> float:
            return float(s.replace(",", ""))

        for seg in segments:
            # Pattern A: keyword + number + optional unit
            # Handles: "salary is 6 lakh", "income 5,00,000", "annual 5,00,000"
            m = re.search(
                r"(?:salary|income|earn(?:ing)?s?|annual|per\s+year|p\.?a\.?)\s*(?:is\s*)?[:\-]?\s*"
                r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|l\b|k\b|thousand|crore|cr\b)?",
                seg, re.IGNORECASE
            )
            if not m:
                # Pattern B: currency symbol + number + optional unit
                m = re.search(
                    r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|l\b|k\b|thousand|crore|cr\b)?",
                    seg, re.IGNORECASE
                )
            if not m:
                # Pattern C: bare number + unit (e.g. "6 lakh", "500000")
                m = re.search(
                    r"\b([\d,]+(?:\.\d+)?)\s*(lakh|lac|l\b|k\b|thousand|crore|cr\b)\b",
                    seg, re.IGNORECASE
                )
            if m:
                raw_num_str = m.group(1)
                unit_str = (m.group(2) or "").lower().strip()
                print(f"[DEBUG _extract_details] Salary match in {seg!r}: num={raw_num_str!r}, unit={unit_str!r}")
                try:
                    num = _parse_indian_num(raw_num_str)
                    if unit_str in ("lakh", "lac", "l"):
                        num *= 100_000
                    elif unit_str in ("k", "thousand"):
                        num *= 1_000
                    elif unit_str in ("crore", "cr"):
                        num *= 10_000_000
                    formatted = f"₹{num:,.0f}"
                    flow.state["salary"] = formatted
                    updated = True
                    salary_found = True
                    print(f"[DEBUG _extract_details] ✓ salary = {formatted!r}")
                    break
                except ValueError as e:
                    print(f"[DEBUG _extract_details] ✗ Salary parse error: {e}")

        if not salary_found:
            # Final fallback: search entire normalised text
            m = re.search(
                r"(?:salary|income|earn(?:ing)?s?|annual)\s*(?:is\s*)?[:\-]?\s*"
                r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|l\b|k\b|thousand|crore|cr\b)?",
                text, re.IGNORECASE
            )
            if m:
                raw_num_str = m.group(1)
                unit_str = (m.group(2) or "").lower().strip()
                try:
                    num = _parse_indian_num(raw_num_str)
                    if unit_str in ("lakh", "lac", "l"):
                        num *= 100_000
                    elif unit_str in ("k", "thousand"):
                        num *= 1_000
                    elif unit_str in ("crore", "cr"):
                        num *= 10_000_000
                    formatted = f"₹{num:,.0f}"
                    flow.state["salary"] = formatted
                    updated = True
                    print(f"[DEBUG _extract_details] ✓ salary (fallback) = {formatted!r}")
                except ValueError:
                    pass

    print(f"[DEBUG _extract_details] Final: full_name={flow.state.get('full_name')!r}, "
          f"mother_name={flow.state.get('mother_name')!r}, salary={flow.state.get('salary')!r}, "
          f"updated={updated}")
    return updated


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


def _build_confirmation(flow: FlowManager) -> dict:
    """Build the full confirmation summary with confirm_action buttons."""
    s = flow.state

    def _yn(val):
        if val is True:  return "Yes"
        if val is False: return "No"
        return str(val) if val else "—"

    lines = [
        "Here's everything I've collected for your PAN application.\n",
        "**Application Options**",
        f"**Submission mode:** {s.get('submission_mode') or '—'}",
        f"**PAN delivery:** {'Physical + e-PAN' if s.get('delivery_mode') == 'physical_and_soft' else 'e-PAN only' if s.get('delivery_mode') == 'soft_only' else '—'}",
        f"**Aadhaar photo on PAN:** {_yn(s.get('aadhaar_photo'))}",
        f"**Source of income:** {s.get('source_of_income') or '—'}",
        f"**Address for communication:** {s.get('address_for_comm') or '—'}",
        f"**Residential status:** {s.get('residential_status') or '—'}",
        f"**Representative Assessee:** {_yn(s.get('rep_assessee'))}",
        "",
        "**Personal Details**",
        f"**Full name (as in Aadhaar):** {s.get('full_name') or '—'}",
        f"**Mother's name:** {s.get('mother_name') or '—'}",
        f"**Email:** {s.get('email') or '—'}",
        f"**Annual income:** {s.get('salary') or '—'}",
    ]

    answer = "\n".join(lines) + "\n\n---\n\nDoes everything look correct? Proceed to document upload?"

    return {
        "answer": answer,
        "sources": [], "followups": [], "guided": True,
        "step": "confirmation", "confirm_action": True,
    }


def _detect_modification_field(inp: str) -> str | None:
    """Detect which field the user wants to modify from their message."""
    lower = inp.lower()
    print(f"[DEBUG] Detecting field from input: {lower!r}")
    
    # Match "name" in various contexts - treat as full_name field
    # Check for "mother" FIRST to avoid false matches
    if re.search(r"\b(mother|mom|mum)\b", lower):
        print("[DEBUG] Matched: mother_name")
        return "mother_name"
    
    # Now check for general "name" patterns (after mother check)
    if re.search(r"\b(full\s+name|my\s+name|name\s+on\s+aadhaar|aadhaar\s+name|just\s+name|the\s+name|change\s+name|update\s+name|name\s+is|name\s+to|name$)\b", lower):
        print("[DEBUG] Matched: full_name")
        return "full_name"
    
    if re.search(r"\b(email|mail|gmail|e-mail)\b", lower):
        print("[DEBUG] Matched: email")
        return "email"
    # Check "source of income" BEFORE "salary/income" to avoid false matches
    if re.search(r"\b(source\s+of\s+income|income\s+source|income\s+type)\b", lower):
        print("[DEBUG] Matched: source_of_income")
        return "source_of_income"
    if re.search(r"\b(salary|income|earning|annual|pay)\b", lower):
        print("[DEBUG] Matched: salary")
        return "salary"
    if re.search(r"\b(submission|how\s+to\s+submit|submit\s+mode)\b", lower):
        print("[DEBUG] Matched: submission_mode")
        return "submission_mode"
    if re.search(r"\b(delivery|card\s+delivery|physical|soft\s+copy)\b", lower):
        print("[DEBUG] Matched: delivery_mode")
        return "delivery_mode"
    if re.search(r"\b(aa?dhaa?r\s+photo|photo\s+on\s+pan|photo\s+consent|aadhar\s+photo)\b", lower):
        print("[DEBUG] Matched: aadhaar_photo")
        return "aadhaar_photo"
    # Check for "address" patterns - be flexible with variations
    if re.search(r"\b(address\s+for\s+comm|communication\s+address|address\s+for\s+communication|comm\s+address|address.*communication|communication.*address)\b", lower):
        print("[DEBUG] Matched: address_for_comm")
        return "address_for_comm"
    # Also match just "address" if it's the only word or with "change/update"
    if re.search(r"^address$|^change\s+address$|^update\s+address$", lower):
        print("[DEBUG] Matched: address_for_comm (simple)")
        return "address_for_comm"
    if re.search(r"\b(residential\s+status|residency|resident\s+status)\b", lower):
        print("[DEBUG] Matched: residential_status")
        return "residential_status"
    # Check for "representative assessee" - must be specific to avoid matching address option
    if re.search(r"\b(representative\s+assessee|rep\s+assessee|appointing\s+representative)\b", lower):
        print("[DEBUG] Matched: rep_assessee")
        return "rep_assessee"
    
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
            "type": "checkbox", "label": "Source of Income", "field": "source_of_income",
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
            "answer": "**Please select your Source of Income** (select all that apply):",
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
            "full_name":   "Please provide your **full name exactly as it appears on your Aadhaar card**:",
            "mother_name": "Please provide your **mother's full name** (as per official records):",
            "email":       "Please provide the **email address** you'd like to use for PAN correspondence:",
            "salary":      "Please provide your **annual income / salary per year** (not monthly — e.g. ₹5,00,000):",
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
        # Extract name from input - handle both "name is X" and just "X"
        # First try to extract from pattern like "name is X" or "change to X"
        name_match = re.search(
            r"(?:name\s+(?:is|to)\s+|change\s+(?:to|it\s+to)\s+|update\s+(?:to|it\s+to)\s+)?([A-Za-z][A-Za-z\s]{1,50})$",
            text, re.IGNORECASE
        )
        if name_match:
            candidate = name_match.group(1).strip()
        else:
            # If no pattern match, treat entire input as the name
            candidate = text
        
        # Filter out common command words
        words = candidate.split()
        _FILTER_WORDS = {'my', 'name', 'is', 'the', 'full', 'change', 'update', 'to', 'it'}
        filtered_words = [w for w in words if w.lower() not in _FILTER_WORDS]
        
        if filtered_words:
            candidate = ' '.join(filtered_words)  # Preserve original case
            if _is_valid_name(candidate):
                flow.state["full_name"] = candidate
                print(f"[DEBUG _apply_field_update] Updated full_name to: {candidate!r}")
            else:
                print(f"[DEBUG _apply_field_update] Invalid name: {candidate!r}")
        else:
            print(f"[DEBUG _apply_field_update] Name filtered to empty")

    elif field == "mother_name":
        # Extract mother's name - handle both "mother name is X" and just "X"
        name_match = re.search(
            r"(?:mother(?:'?s)?\s+name\s+(?:is|to)\s+|mom(?:'?s)?\s+name\s+(?:is|to)\s+|change\s+(?:to|it\s+to)\s+|update\s+(?:to|it\s+to)\s+)?([A-Za-z][A-Za-z\s]{1,50})$",
            text, re.IGNORECASE
        )
        if name_match:
            candidate = name_match.group(1).strip()
        else:
            candidate = text
        
        # Filter out common command words
        words = candidate.split()
        _FILTER_WORDS = {'my', 'mother', 'mothers', 'mom', 'moms', 'name', 'is', 'the', 'full', 'change', 'update', 'to', 'it'}
        filtered_words = [w for w in words if w.lower() not in _FILTER_WORDS]
        
        if filtered_words:
            candidate = ' '.join(filtered_words)  # Preserve original case
            if _is_valid_name(candidate):
                flow.state["mother_name"] = candidate
                print(f"[DEBUG _apply_field_update] Updated mother_name to: {candidate!r}")
            else:
                print(f"[DEBUG _apply_field_update] Invalid mother name: {candidate!r}")
        else:
            print(f"[DEBUG _apply_field_update] Mother name filtered to empty")

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
        # Re-use the extraction logic
        dummy_flow_state_backup = dict(flow.state)
        flow.state["salary"] = None
        _extract_details(flow, lower, text)
        if not flow.state.get("salary"):
            flow.state["salary"] = dummy_flow_state_backup.get("salary")

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
    flow = FlowManager(session_id)
    
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
    flow = FlowManager(session_id)
    
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
    flow = FlowManager(session_id)
    
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

