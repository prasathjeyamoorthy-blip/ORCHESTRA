# api/routes.py
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.schemas import QuestionRequest, AnswerResponse, SummarizeRequest
from api.chain_instance import get_chain
import traceback
import json
import re
from fastapi import UploadFile, File, Form
from agent.receptionist import handle_document_upload, merge_form_fields
import shutil
import httpx
from pathlib import Path


# ── Options definitions for every updatable field ────────────────
# These mirror exactly what receptionist.py uses so clicking a button
# feeds the same text back through the normal flow handler.
_FIELD_OPTIONS: dict[str, dict] = {
    "submission_mode": {
        "type": "radio",
        "label": "Submission Mode",
        "field": "submission_mode",
        "choices": [
            "Aadhaar-based Online (eKYC)",
            "Upload scanned docs & eSign",
            "Fill online + courier physical form",
        ],
    },
    "delivery_mode": {
        "type": "radio",
        "label": "PAN Delivery",
        "field": "delivery_mode",
        "choices": [
            "Physical copy to home + soft copy on email (Fees applicable)",
            "Only soft copy on email (Fees applicable)",
        ],
    },
    "aadhaar_photo": {
        "type": "radio",
        "label": "Aadhaar Photo on PAN",
        "field": "aadhaar_photo",
        "choices": ["Yes", "No"],
    },
    "source_of_income": {
        "type": "radio",
        "label": "Source of Income",
        "field": "source_of_income",
        "choices": [
            "Salary | சம்பளம்",
            "Income from Business / Profession | வணிகம் / தொழில்",
            "Income from House property | வீட்டு சொத்து",
            "Income from Other sources | பிற மூலங்கள்",
            "Capital Gains | மூலதன ஆதாயங்கள்",
            "No income | வருமானம் இல்லை",
        ],
    },
    "address_for_comm": {
        "type": "radio",
        "label": "Address for Communication",
        "field": "address_for_comm",
        "choices": ["Residence | வீடு", "Office | அலுவலகம்", "Representative Assessee (RA)"],
    },
    "residential_status": {
        "type": "radio",
        "label": "Residential Status",
        "field": "residential_status",
        "choices": [
            "Resident | குடியிருப்பாளர்",
            "Non-resident | குடியுரிமை இல்லாதவர்",
            "Resident but not ordinarily resident",
        ],
    },
    "rep_assessee": {
        "type": "radio",
        "label": "Representative Assessee",
        "field": "rep_assessee",
        "choices": ["Yes | ஆம்", "No | இல்லை"],
    },
}

router = APIRouter()

# ── Inline-edit message detector ─────────────────────────────────────────────
# Matches messages sent by the Save-All button in the confirmation panel, e.g.
#   "change Source of Income to Salary"
#   "change Full Name (as in Aadhaar) to Ravi | change Mother's Name to Priya"
# These must BYPASS the transliteration handler completely.
_INLINE_EDIT_PREFIX_RE = re.compile(
    r"^change\s+(Source of Income|Submission Mode|PAN Delivery|Aadhaar Photo on PAN"
    r"|Address for Communication|Residential Status|Representative Assessee"
    r"|Full Name \(as in Aadhaar\)|Full Name|Grandfather'?s Name|Mother'?s Name|Annual Income|Email)\s+to\s+",
    re.IGNORECASE,
)

def _is_inline_edit_message(msg: str) -> bool:
    """Return True if the message is a confirmation-panel inline edit (single or batched)."""
    parts = [p.strip() for p in msg.split(" | ") if p.strip()]
    return bool(parts) and all(_INLINE_EDIT_PREFIX_RE.match(p) for p in parts)

# ── Steps where "No" / "N" is a valid answer, never a cancellation ──────────
_YES_NO_ANSWER_STEPS = {
    "aadhaar_photo", "rep_assessee", "confirmation",
}

def _safe_question(question: str, session_id: str) -> str:
    """
    Guard: if the current flow step expects a Yes/No answer, never let a bare
    'no' / 'n' reach the cancellation detector.
    Also handles the email_confirm sub-step inside details_collection.
    """
    q = question.strip()
    if q.lower() not in ("no", "n", "nope", "nah"):
        return question
    try:
        from agent.flow_manager import FlowManager
        fm = FlowManager(session_id)
        if fm.has_active_flow():
            step = fm.get_current_step()
            # Standard yes/no steps
            if step in _YES_NO_ANSWER_STEPS:
                return "No"
            # Email confirm sub-step inside details_collection
            if step == "details_collection" and fm.state.get("_email_confirm_asked") and not fm.state.get("email"):
                return "No"
    except Exception:
        pass
    return question


@router.get("/flow-state/{user_id}/{session_id}")
def get_flow_state(user_id: str, session_id: str):
    """
    Return the current flow state for a session so the frontend can show
    a resume banner when the user switches back to an in-progress session.
    """
    from agent.flow_manager import FlowManager
    fm = FlowManager(session_id, user_id or "anonymous")

    if not fm.has_active_flow():
        return {"active": False}

    s = fm.state
    step = s.get("current_step")

    # Human-readable step label (English + Tamil)
    _STEP_LABELS = {
        "applicant_type":    {"en": "Applicant Type",            "ta": "விண்ணப்பதாரர் வகை"},
        "submission_mode":   {"en": "Submission Mode",           "ta": "சமர்ப்பிக்கும் முறை"},
        "delivery_mode":     {"en": "PAN Delivery",              "ta": "விநியோக முறை"},
        "aadhaar_photo":     {"en": "Aadhaar Photo Consent",     "ta": "ஆதார் புகைப்படம்"},
        "source_of_income":  {"en": "Source of Income",          "ta": "வருமான மூலம்"},
        "address_for_comm":  {"en": "Address for Communication", "ta": "தொடர்பு முகவரி"},
        "residential_status":{"en": "Residential Status",        "ta": "குடியிருப்பு நிலை"},
        "rep_assessee":      {"en": "Representative Assessee",   "ta": "பிரதிநிதி நியமனம்"},
        "details_collection":{"en": "Personal Details",          "ta": "தனிப்பட்ட விவரங்கள்"},
        "confirmation":      {"en": "Confirmation",              "ta": "உறுதிப்படுத்தல்"},
        "documents":         {"en": "Document Upload",           "ta": "ஆவண பதிவேற்றம்"},
        "summary":           {"en": "Summary",                   "ta": "சுருக்கம்"},
    }

    def _yn(v):
        if v is True:  return "Yes"
        if v is False: return "No"
        return v or "—"

    # Fields completed so far
    completed = {}
    if s.get("applicant_type"):    completed["applicant_type"]    = s["applicant_type"]
    if s.get("submission_mode"):   completed["submission_mode"]   = s["submission_mode"]
    if s.get("delivery_mode"):     completed["delivery_mode"]     = s["delivery_mode"]
    if s.get("aadhaar_photo") is not None: completed["aadhaar_photo"] = _yn(s["aadhaar_photo"])
    if s.get("source_of_income"):  completed["source_of_income"]  = s["source_of_income"]
    if s.get("address_for_comm"):  completed["address_for_comm"]  = s["address_for_comm"]
    if s.get("residential_status"):completed["residential_status"]= s["residential_status"]
    if s.get("rep_assessee") is not None: completed["rep_assessee"] = _yn(s["rep_assessee"])
    if s.get("full_name"):         completed["full_name"]         = s["full_name"]
    if s.get("grandfather_name"):  completed["grandfather_name"]  = s["grandfather_name"]
    if s.get("mother_name"):       completed["mother_name"]       = s["mother_name"]
    if s.get("email"):             completed["email"]             = s["email"]
    if s.get("salary"):            completed["salary"]            = s["salary"]
    if s.get("title"):             completed["title"]             = s["title"]
    if s.get("mobile"):            completed["mobile"]            = s["mobile"]

    # What's still missing for the current step
    missing_for_step = []
    if step == "details_collection":
        if not s.get("full_name"):          missing_for_step.append("full_name")
        if not s.get("grandfather_name"):   missing_for_step.append("grandfather_name")
        if not s.get("mother_name"):        missing_for_step.append("mother_name")
        if not s.get("email"):              missing_for_step.append("email")
        if not s.get("salary"):             missing_for_step.append("salary")

    return {
        "active": True,
        "service_id": s.get("service_id"),
        "current_step": step,
        "complete": s.get("complete", False) or step == "summary",
        "step_labels": _STEP_LABELS.get(step, {"en": step, "ta": step}),
        "completed_fields": completed,
        "missing_for_step": missing_for_step,
        "language": s.get("preferred_language", "en"),
        # Pending docs — so frontend knows what's still needed
        "pending_docs": fm.state.get("pending_docs", []),
        "collected_docs_count": len(fm.state.get("collected_docs", [])),
    }


@router.delete("/session/{session_id}")
def reset_session(session_id: str):
    """Clear flow state and memory for a session (called when session is created or deleted)."""
    from agent.flow_manager import FlowManager, SESSIONS_DIR
    from memory.memory_manager import MemoryManager

    # Delete flow state file
    state_file = SESSIONS_DIR / f"{session_id}.json"
    if state_file.exists():
        state_file.unlink()

    # Clear session memory from Upstash
    try:
        mm = MemoryManager()
        mm._del(f"session:{session_id}:history")
    except Exception:
        pass

    return {"cleared": session_id}


@router.post("/ask", response_model=AnswerResponse)
async def ask(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    import time
    _t = time.time()
    
    # ── Check for Tamil transliteration and field intent ──────────────────────
    from api.transliteration import handle_transliteration_request, format_field_update_response

    # Skip the transliteration interceptor when the message contains multiple
    # field-value pairs inline (e.g. "ennodiya per deva, amma per nabina, salary vanthu 3 lakhs").
    # Pass it straight through to _continue_flow which handles Tanglish multi-field extraction.
    def _is_multi_field_tanglish(msg: str) -> bool:
        tl = msg.lower()
        _value_signals = [
            # full_name signals: ennodiya/en/naan per/peyar <value>
            (r'\b(?:ennodiya|ennoda|ennode|en|naan|naanu)\s+(?:peyar|per|peru)\b', 'full_name'),
            # mother_name signals: amma/thaayin/thaay per/peyar <value>
            (r'\b(?:amma|ammaa|thaayin|thaay|thaaye)\s+(?:peyar|per|peru)\b',      'mother_name'),
            # salary signals: number + lakh/k, or salary/sambalam keyword near number
            (r'\b\d[\d,.]*\s*(?:lakh|lakhs|l\b|k\b|cr|crore)',                     'salary_num'),
            (r'\b(?:salary|sambalam|varumanam)\b',                                  'salary_kw'),
            # email
            (r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',               'email'),
        ]
        fields_with_values = set()
        for pattern, tag in _value_signals:
            if re.search(pattern, tl, re.IGNORECASE):
                fields_with_values.add(tag)
        # Need at least 2 distinct field tags (salary_kw + salary_num count as one)
        distinct = fields_with_values - {'salary_kw'} if 'salary_num' in fields_with_values else fields_with_values
        return len(distinct) >= 2

    skip_transliteration = _is_multi_field_tanglish(request.question) or _is_inline_edit_message(request.question)
    try:
        transliteration_result = None if skip_transliteration else await handle_transliteration_request(
            request.question,
            request.session_id or ""
        )
    except Exception as _te:
        print(f"[ask] transliteration check failed: {_te} — falling through to normal flow")
        transliteration_result = None
    
    if transliteration_result:
        # User wants to update a field using Tamil/transliterated message
        field = transliteration_result.get('field')
        value = transliteration_result.get('value')
        tamil_script = transliteration_result.get('tamil_script')
        
        print(f"[ask] Detected transliteration intent: field={field}, value={value}, tamil={tamil_script}")
        
        # Update the field in the flow manager if we have a value
        if field and value and request.session_id:
            from agent.flow_manager import FlowManager
            fm = FlowManager(request.session_id, request.user_id or "anonymous")
            # Update state even if no active flow (for application detail fields)
            fm.state[field] = value
            fm.save()
            print(f"[ask] Updated {field} to {value} in flow state")
        
        # Build short intro text (Tamil script if available, then English label)
        tamil_script = transliteration_result.get('tamil_script')
        field_labels = {
            'full_name': "Full Name", 'mother_name': "Mother's Name",
            'salary': "Annual Income", 'email': "Email Address",
            'phone': "Phone Number", 'address': "Residential Address",
            'submission_mode': "Submission Mode", 'delivery_mode': "PAN Delivery Mode",
            'aadhaar_photo': "Aadhaar Photo on PAN", 'source_of_income': "Source of Income",
            'address_for_comm': "Address for Communication",
            'residential_status': "Residential Status", 'rep_assessee': "Representative Assessee",
        }
        field_display = field_labels.get(field, (field or '').replace('_', ' ').title())

        intro_parts = []
        if tamil_script and tamil_script != request.question:
            intro_parts.append(f"*{tamil_script}*\n")
        intro_parts.append(f"I understand you want to update your **{field_display}**.")
        # For text fields (no predefined options) ask the user to type the value
        if field and field not in _FIELD_OPTIONS:
            intro_parts.append(f"\nPlease type the new value for {field_display}.")
        response_text = "\n".join(intro_parts)

        # Attach interactive options widget if this field has predefined choices
        options_obj = _FIELD_OPTIONS.get(field) if field else None

        elapsed_ms = int((time.time() - _t) * 1000)
        result = {
            "answer": response_text,
            "session_id": request.session_id,
            "sources": [],
            "followups": [],
            "elapsed_ms": elapsed_ms,
            "intent": "field_update",
            "guided": True,
            "options": options_obj,
        }
        return AnswerResponse(**result)
    
    # ── Normal processing if not transliteration ──────────────────────────────
    safe_q = _safe_question(request.question, request.session_id or "")

    try:
        result = get_chain().run(
            question=safe_q,
            session_id=request.session_id,
            user_id=request.user_id,
            user_context=request.user_context,
            account_email=request.account_email or "",
            language_override=request.language or None,
        )
        elapsed_ms = int((time.time() - _t) * 1000)
        print(f"[ask] intent={result.get('intent','?')} | {elapsed_ms}ms | q={request.question[:60]!r}")
        result["elapsed_ms"] = elapsed_ms
        return AnswerResponse(**result)
    except Exception as e:
        elapsed_ms = int((time.time() - _t) * 1000)
        print(f"[ask] ERROR after {elapsed_ms}ms: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-stream")
async def ask_stream(request: QuestionRequest):
    """
    SSE streaming endpoint.
    Runs all pre-LLM logic (intent, retrieval, flow) synchronously,
    then streams the final LLM answer token-by-token.

    Event format:
      data: {"type": "meta",  ...session_id, intent, sources, followups, open_upload, form_data}
      data: {"type": "token", "text": "..."}
      data: {"type": "done"}
      data: {"type": "error", "message": "..."}
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # ── Check for Tamil transliteration and field intent ──────────────────────
    from api.transliteration import handle_transliteration_request, format_field_update_response

    # Same multi-field bypass as in /ask
    def _is_multi_field_tanglish_stream(msg: str) -> bool:
        tl = msg.lower()
        _value_signals = [
            (r'\b(?:ennodiya|ennoda|ennode|en|naan|naanu)\s+(?:peyar|per|peru)\b', 'full_name'),
            (r'\b(?:amma|ammaa|thaayin|thaay|thaaye)\s+(?:peyar|per|peru)\b',      'mother_name'),
            (r'\b\d[\d,.]*\s*(?:lakh|lakhs|l\b|k\b|cr|crore)',                     'salary_num'),
            (r'\b(?:salary|sambalam|varumanam)\b',                                  'salary_kw'),
            (r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',               'email'),
        ]
        fields_with_values = set()
        for pattern, tag in _value_signals:
            if re.search(pattern, tl, re.IGNORECASE):
                fields_with_values.add(tag)
        distinct = fields_with_values - {'salary_kw'} if 'salary_num' in fields_with_values else fields_with_values
        return len(distinct) >= 2

    skip_transliteration_stream = _is_multi_field_tanglish_stream(request.question) or _is_inline_edit_message(request.question)
    try:
        transliteration_result = None if skip_transliteration_stream else await handle_transliteration_request(
            request.question,
            request.session_id or ""
        )
    except Exception as _te:
        print(f"[ask-stream] transliteration check failed: {_te} — falling through to normal flow")
        transliteration_result = None

    if transliteration_result:
        # User wants to update a field using Tamil/transliterated message
        field = transliteration_result.get('field')
        value = transliteration_result.get('value')
        tamil_script = transliteration_result.get('tamil_script')

        print(f"[ask-stream] Detected transliteration intent: field={field}, value={value}, tamil={tamil_script}")
        
        # Update the field in the flow manager if we have a value
        if field and value and request.session_id:
            from agent.flow_manager import FlowManager
            fm = FlowManager(request.session_id, request.user_id or "anonymous")
            # Update state even if no active flow (for application detail fields)
            fm.state[field] = value
            fm.save()
            print(f"[ask-stream] Updated {field} to {value} in flow state")
        
        # Build response
        current_value = None
        if request.user_context and field:
            # Try to extract current value from user_context
            # re is already imported at module level
            field_names = {
                'mother_name': r"-\s*Mother'?s?\s+name:\s*(.+)",
                'salary': r"-\s*Annual income:\s*(.+)",
                'email': r"-\s*Email:\s*(.+)",
                'phone': r"-\s*Phone:\s*(.+)",
                'address': r"-\s*Address:\s*(.+)",
                'full_name': r"-\s*Name:\s*(.+)",
            }
            if field in field_names:
                m = re.search(field_names[field], request.user_context, re.IGNORECASE)
                if m:
                    current_value = m.group(1).strip()
        
        response_text = format_field_update_response(transliteration_result, current_value)
        
        # Stream the response
        def transliteration_stream():
            try:
                # Send meta event with guided=True
                yield f"data: {json.dumps({'type': 'meta', 'session_id': request.session_id, 'intent': 'field_update', 'guided': True, 'sources': [], 'followups': ['Continue with application', 'Update another field', 'Show me all my details'], 'transliteration': {'detected': True, 'field': field, 'tamil_script': tamil_script, 'romanized': request.question}})}\n\n"
                
                # Stream the answer token by token
                for char in response_text:
                    yield f"data: {json.dumps({'type': 'token', 'text': char})}\n\n"
                
                # Send done event
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            transliteration_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # ── Normal processing if not transliteration ──────────────────────────────
    safe_q = _safe_question(request.question, request.session_id or "")
    chain = get_chain()

    def event_stream():
        try:
            # Run the full chain in streaming mode
            yield from chain.run_stream(
                question=safe_q,
                session_id=request.session_id,
                user_id=request.user_id,
                user_context=request.user_context,
                account_email=request.account_email or "",
                language_override=request.language or None,
            )
        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )




@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/summarize")
async def summarize(request: SummarizeRequest):
    """
    Generate a rolling summary of conversation history.
    Called fire-and-forget by the Node backend when history exceeds 20 messages.
    Payload: { "prompt": "...", "user_id": "..." }
    Returns: { "summary": "..." }
    """
    from generation.llm import _call

    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a conversation summarizer. "
                    "Produce a concise 3-5 sentence summary of the conversation. "
                    "Focus on what the user asked, what was resolved, and any important "
                    "details such as PAN number, name, income, or unresolved issues. "
                    "Write in plain English. Do not include greetings or filler."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        summary = _call(messages, max_tokens=200, temperature=0.2)
        return {"summary": summary}
    except Exception as e:
        print(f"[summarize] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Document upload agent URL — running on port 5000
DOC_AGENT_URL = os.getenv("DOC_AGENT_URL", "http://localhost:5000/api/verify")

@router.post("/upload")
async def upload_document(
    session_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    message: str = Form(default=""),
    user_id: str = Form(default="anonymous"),
):
    # Normalize empty/missing user_id to "anonymous"
    if not user_id or not user_id.strip():
        user_id = "anonymous"
    # Save file locally with document type in filename
    dest = UPLOAD_DIR / session_id
    dest.mkdir(parents=True, exist_ok=True)

    # Build temporary filename with original name to avoid conflicts
    # Format: user_{original_name} (e.g., "user_photo.jpg", "user_aadhar.pdf")
    _ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    temp_filename = f"user_{file.filename}"
    file_path = dest / temp_filename

    file_bytes = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # ── Forward to document upload agent for extraction + verification ──
    extraction_result = {}
    agent_error = None
    detected_doc_type = doc_type  # Default to user-provided type
    stored_filename = temp_filename  # Track the actual stored filename
    
    try:
        # Generate a temporary auth_id for pan_verification compatibility
        # In future integration, this should come from authenticated user
        temp_auth_id = session_id  # Using session_id as temporary auth_id
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                DOC_AGENT_URL,
                data={"auth_id": temp_auth_id, "doc_type": doc_type},
                # Send under both 'aadhaar' (legacy) and 'file' so pan_verification accepts any doc type
                files={
                    "aadhaar": (file.filename, file_bytes, file.content_type or "application/octet-stream"),
                    "file": (file.filename, file_bytes, file.content_type or "application/octet-stream"),
                },
            )
        if response.status_code == 200:
            extraction_result = response.json()
            print(f"\n✅ Extraction result for [{doc_type}] session [{session_id}]:")
            import json as _json
            print(_json.dumps(extraction_result, indent=2, ensure_ascii=False))
            
            # Get the DETECTED document type from extraction (more reliable than user input)
            # pan_verification returns document_type at top level OR inside doc_type_info
            detected_type = (
                extraction_result.get("document_type")
                or extraction_result.get("doc_type_info", {}).get("document_type")
                or extraction_result.get("all_extracted_data", {}).get("document_type")
                or extraction_result.get("extracted", {}).get("document_type")
                or ""
            )
            
            # Get the VLM description to help disambiguate "other_document"
            vlm_description = (
                extraction_result.get("doc_type_info", {}).get("description", "")
                or extraction_result.get("description", "")
            ).lower()
            
            if detected_type and detected_type != "unknown":
                # Normalize document type names to match service_flows.py expectations
                # pan_verification returns: aadhaar_card, profile_photo, signature, driving_license
                # service_flows expects: aadhaar, photograph, signature, driving_license
                type_normalization = {
                    "aadhaar_card": "aadhaar",
                    "aadhaar": "aadhaar",
                    "aadhar": "aadhaar",
                    "aadhar_card": "aadhaar",
                    "profile_photo": "photograph",
                    "photograph": "photograph",
                    "photo": "photograph",
                    "applicant_photo": "photograph",
                    "applicant_photograph": "photograph",
                    "face_photo": "photograph",
                    "passport_photo": "photograph",
                    "signature": "signature",
                    "applicant_signature": "signature",
                    "sign": "signature",
                    "driving_license": "driving_license",
                    "driver_license": "driving_license",
                    "dl": "driving_license",
                }

                # "other_document" fallback logic:
                if detected_type == "other_document":
                    fname_lower = file.filename.lower()
                    user_hint = doc_type.lower()

                    if "signature" in vlm_description or "sign" in vlm_description:
                        detected_doc_type = "signature"
                        print(f"      ℹ️ VLM description mentions signature → overriding other_document to: signature")
                    elif user_hint in ("signature", "sign", "applicant_signature"):
                        detected_doc_type = "signature"
                        print(f"      ℹ️ User doc_type hint is '{user_hint}' → overriding to: signature")
                    elif "sign" in fname_lower:
                        detected_doc_type = "signature"
                        print(f"      ℹ️ Filename contains 'sign' → overriding to: signature")
                    elif user_hint in ("photograph", "photo", "profile_photo", "applicant_photo"):
                        detected_doc_type = "photograph"
                        print(f"      ℹ️ User doc_type hint is '{user_hint}' → overriding to: photograph")
                    elif any(w in fname_lower for w in ("photo", "photograph", "portrait", "face")):
                        detected_doc_type = "photograph"
                        print(f"      ℹ️ Filename suggests photo → overriding to: photograph")
                    else:
                        # Fall back to normalized user hint
                        fallback = type_normalization.get(user_hint, user_hint)
                        detected_doc_type = fallback if fallback != "unknown" else detected_type
                        print(f"      ℹ️ other_document — falling back to user hint: {detected_doc_type}")
                else:
                    detected_doc_type = type_normalization.get(detected_type, detected_type)
                    # If VLM type not in map, try user hint as fallback
                    if detected_doc_type == detected_type and detected_type not in type_normalization:
                        user_fallback = type_normalization.get(doc_type.lower(), doc_type.lower())
                        if user_fallback != doc_type.lower():
                            detected_doc_type = user_fallback
                    print(f"      ℹ️ Detected: {detected_type} → normalized to: {detected_doc_type} (user said: {doc_type})")
            
            # Rename file to match detected type
            if detected_doc_type != doc_type or detected_doc_type != "unknown":
                # Create unique filename: {detected_type}_{timestamp}.{ext}
                import time
                timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
                clean_detected = detected_doc_type.lower().replace(" ", "_").replace("-", "_")
                new_filename = f"{clean_detected}_{timestamp}{_ext}"
                new_path = dest / new_filename
                
                # Rename
                import os
                if file_path.exists():
                    os.rename(file_path, new_path)
                    stored_filename = new_filename
                    file_path = new_path
                    print(f"      ✓ Renamed file to: {stored_filename}")
            
            # Store extraction result in Redis for finalize-application to retrieve
            # Use the DETECTED type for Redis key; store the richest available data
            try:
                from memory.memory_manager import MemoryManager
                mm = MemoryManager()
                # Prefer all_extracted_data (full fields), fall back to extracted_fields, then extracted
                cache_data = (
                    extraction_result.get("all_extracted_data")
                    or extraction_result.get("extracted_fields")
                    or extraction_result.get("extracted")
                    or {}
                )
                TTL = 60 * 60 * 24 * 30  # 30 days — long enough to survive cross-session use
                # Write under session-scoped key (primary)
                mm._setex(
                    f"extraction:{session_id}:{detected_doc_type}",
                    TTL,
                    _json.dumps(cache_data)
                )
                # Also write under user-scoped key (fallback for cross-session finalize)
                if user_id and user_id != "anonymous":
                    mm._setex(
                        f"extraction:{user_id}:{detected_doc_type}",
                        TTL,
                        _json.dumps(cache_data)
                    )
                    print(f"      ✓ Extraction cached: session key + user key for {detected_doc_type}")
                else:
                    print(f"      ✓ Extraction cached: session key for {detected_doc_type}")
            except Exception as cache_err:
                print(f"      ⚠️ Could not cache extraction result: {cache_err}")

            # Also persist to Supabase for permanent storage — survives Redis TTL expiry.
            # This is a backup write; confirm_save will overwrite with user-verified data later.
            # Only save Aadhaar (contains personal data); skip photo/signature.
            if detected_doc_type == "aadhaar" and user_id and user_id != "anonymous" and cache_data:
                try:
                    from supabase import create_client as _sb_create
                    _sb_url = os.getenv("SUPABASE_URL", "")
                    _sb_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")
                    if _sb_url and _sb_key:
                        import base64 as _b64
                        from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
                        _enc_key_b64 = os.getenv("DATA_ENCRYPTION_KEY", "")
                        if _enc_key_b64:
                            _enc_key = _b64.b64decode(_enc_key_b64)
                            _nonce = os.urandom(12)
                            _plain = _json.dumps(cache_data, separators=(",", ":")).encode()
                            _ct = _AESGCM(_enc_key).encrypt(_nonce, _plain, None)
                            _encrypted = _b64.b64encode(_nonce + _ct).decode()
                        else:
                            _encrypted = _json.dumps(cache_data)

                        _sb = _sb_create(_sb_url, _sb_key)
                        # Upsert keyed on (auth_id, doc_type) — won't duplicate
                        _sb.table("pan_extractions").upsert({
                            "auth_id":        user_id,
                            "doc_type":       detected_doc_type,
                            "extracted_data": _encrypted,
                            "session_id":     session_id,
                            "updated_at":     __import__('datetime').datetime.utcnow().isoformat(),
                        }, on_conflict="auth_id,doc_type").execute()
                        print(f"      ✓ Aadhaar extraction persisted to Supabase pan_extractions")
                except Exception as _sb_save_err:
                    # Non-fatal — Redis is the primary store, Supabase is just backup
                    # Table may not exist yet if migration hasn't been run
                    print(f"      ⚠️ Could not persist to Supabase pan_extractions: {_sb_save_err}")
        else:
            agent_error = response.json().get("error", "Document agent returned an error")
            print(f"\n❌ Document agent error [{doc_type}]: {agent_error}")
    except httpx.ConnectError:
        agent_error = "Document extraction service is offline. File saved — extraction skipped."
        print(f"\n⚠️  Document agent is offline at {DOC_AGENT_URL} — is the Flask server running on port 5000?  (cd pan_verification && python app.py)")
    except Exception as e:
        agent_error = f"Document extraction failed: {str(e)}"
        print(f"\n❌ Document extraction exception: {e}")

    # ── Extract form fields from the accompanying message text ──
    if message.strip():
        from agent.flow_manager import FlowManager
        fm = FlowManager(session_id, user_id)
        if fm.has_active_flow():
            merge_form_fields(fm, message)

    # ── Update conversation flow ──
    # Use the DETECTED document type (not user-provided) for flow tracking
    flow_result = handle_document_upload(
        session_id=session_id,
        filename=stored_filename,
        doc_type=detected_doc_type,
        user_id=user_id,
    )

    # ── Build response ──
    # Show user what document type was detected
    doc_type_display = detected_doc_type.replace("_", " ").title()
    chat_message = f"📄 **{doc_type_display}** detected!\n\n" + flow_result["answer"]
    
    if agent_error:
        chat_message += f"\n\n> ⚠️ {agent_error}"
    
    # ── Handle missing fields from document verification ──
    missing_fields_form = None
    if extraction_result and extraction_result.get("status") == "missing_fields":
        missing_fields = extraction_result.get("missing_fields", [])
        extracted_fields = extraction_result.get("extracted_fields", {})

        # Pre-fill missing fields from FlowManager state (e.g. mobile already collected in chat)
        try:
            from agent.flow_manager import FlowManager as _FM
            _fm = _FM(session_id, user_id or "anonymous")
            _prefill_map = {
                "mobile_number": _fm.state.get("mobile"),
                "phone":         _fm.state.get("mobile"),
                "email":         _fm.state.get("email"),
            }
            # Only keep fields that are actually missing and have a prefill value
            missing_fields = [
                {**f, "prefill": _prefill_map.get(f["field"]) or ""}
                for f in missing_fields
            ]
            # If mobile was already collected, remove it from missing list entirely
            missing_fields = [
                f for f in missing_fields
                if not (f["field"] in ("mobile_number", "phone") and _fm.state.get("mobile"))
            ]
        except Exception:
            pass

        # Build user-friendly message about missing fields
        missing_field_names = [field["label"] for field in missing_fields]
        if missing_field_names:
            chat_message = f"📄 Document processed! I extracted some information, but need you to provide the missing details:\n\n**Missing:** {', '.join(missing_field_names)}\n\nPlease fill in the form below to complete your document verification."
        else:
            # All missing fields were pre-filled from flow state — no form needed
            chat_message = f"📄 Document processed successfully — all fields extracted."

        # Only show form if there are still missing fields after pre-fill
        if missing_fields:
            missing_fields_form = {
                "fields": missing_fields,
                "extracted_fields": extracted_fields,
                "session_id": session_id,
                "auth_id": extraction_result.get("auth_id") or session_id,
                "quality_score": extraction_result.get("quality_score"),
            }

    return {
        "filename": file.filename,
        "stored_filename": stored_filename,
        "detected_doc_type": detected_doc_type,
        "user_provided_doc_type": doc_type,
        "session_id": session_id,
        "message": chat_message,
        "complete": flow_result.get("complete", False),
        "show_submit": flow_result.get("show_submit", False),
        "extraction": extraction_result if extraction_result else None,
        "verified": extraction_result.get("status") == "success" if extraction_result else False,
        "validation_errors": extraction_result.get("validation_errors", []),
        "missing_fields_form": missing_fields_form,
        "requires_completion": extraction_result.get("status") == "missing_fields" if extraction_result else False,
    }


@router.post("/record-document")
async def record_document_in_flow(request_data: dict):
    """
    Lightweight endpoint: record a document in FlowManager without re-running extraction.
    Called by document-upload-panel.jsx after pan_verification succeeds,
    so the flow knows the document was uploaded even when the panel (not chat) was used.

    Also accepts optional `extracted_data` — plain dict of VLM/confirmed fields.
    If provided, updates the Redis extraction cache so finalize-application reads
    the latest verified data instead of a stale or encrypted version.
    """
    session_id     = request_data.get("session_id")
    user_id        = request_data.get("user_id", "anonymous") or "anonymous"
    doc_type       = request_data.get("doc_type", "")
    filename       = request_data.get("filename", "unknown")
    extracted_data = request_data.get("extracted_data")   # optional plain dict

    if not session_id or not doc_type:
        raise HTTPException(status_code=400, detail="session_id and doc_type are required")

    # Update Redis extraction cache if caller provided plain extracted data
    if extracted_data and isinstance(extracted_data, dict) and extracted_data:
        try:
            from memory.memory_manager import MemoryManager
            import json as _json
            mm = MemoryManager()
            TTL = 60 * 60 * 24 * 30  # 30 days
            # Session-scoped key (primary)
            mm._setex(f"extraction:{session_id}:{doc_type}", TTL, _json.dumps(extracted_data))
            # User-scoped key (cross-session fallback)
            if user_id and user_id != "anonymous":
                mm._setex(f"extraction:{user_id}:{doc_type}", TTL, _json.dumps(extracted_data))
                print(f"[record-document] ✓ Updated Redis cache for {doc_type} (session + user keys)")
            else:
                print(f"[record-document] ✓ Updated Redis cache for {doc_type} (session key only)")
        except Exception as cache_err:
            print(f"[record-document] ⚠️ Could not update Redis cache: {cache_err}")

    from agent.receptionist import handle_document_upload
    flow_result = handle_document_upload(
        session_id=session_id,
        filename=filename,
        doc_type=doc_type,
        user_id=user_id,
    )
    return {
        "status": "ok",
        "doc_type": doc_type,
        "complete": flow_result.get("complete", False),
        "show_submit": flow_result.get("show_submit", False),
        "message": flow_result.get("answer", ""),
    }


@router.post("/complete_document")
async def complete_document_with_missing_fields(request_data: dict):
    """Complete document verification by submitting missing field data."""
    try:
        session_id = request_data.get("session_id")
        auth_id = request_data.get("auth_id") 
        extracted_fields = request_data.get("extracted_fields", {})
        user_fields = request_data.get("user_fields", {})
        
        if not session_id or not auth_id:
            raise HTTPException(status_code=400, detail="session_id and auth_id are required")
        
        # Forward completion request to pan_verification
        completion_result = {}
        completion_error = None
        
        try:
            # Prepare form data for pan_verification
            form_data = {
                "auth_id": auth_id,
                "extracted_fields": json.dumps(extracted_fields)
            }
            
            # Add user-provided fields
            for field_name, field_value in user_fields.items():
                if field_value and str(field_value).strip():
                    form_data[field_name] = str(field_value).strip()
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{DOC_AGENT_URL.replace('/api/verify', '')}/api/complete_missing_fields",
                    data=form_data
                )
                
            if response.status_code == 200:
                completion_result = response.json()
                print(f"\n✅ Document completion successful for session [{session_id}]")
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                completion_error = error_data.get("error", f"Completion failed with status {response.status_code}")
                
                # If there are specific validation errors, include them for the user
                v_errors = error_data.get("validation_errors", [])
                if v_errors:
                    completion_error += f": {', '.join(v_errors)}"
                
                print(f"\n❌ Document completion error: {completion_error}")
                
        except httpx.ConnectError:
            completion_error = "Document verification service is offline"
        except Exception as e:
            completion_error = f"Document completion failed: {str(e)}"
        
        # Return response
        if completion_result and completion_result.get("status") == "success":
            # Update Redis cache with the corrected plain data so finalize-application
            # reads the user-verified version, not the stale original VLM result.
            corrected_data = completion_result.get("aadhaar_data", {})
            if corrected_data and session_id:
                try:
                    from memory.memory_manager import MemoryManager
                    import json as _json
                    mm = MemoryManager()
                    TTL = 60 * 60 * 24 * 30  # 30 days
                    # Session-scoped key
                    mm._setex(f"extraction:{session_id}:aadhaar", TTL, _json.dumps(corrected_data))
                    # User-scoped key — survives session changes
                    auth_id = request_data.get("auth_id", "")
                    if auth_id and auth_id != "anonymous":
                        mm._setex(f"extraction:{auth_id}:aadhaar", TTL, _json.dumps(corrected_data))
                    print(f"[complete_document] ✓ Updated Redis cache with corrected aadhaar data")
                except Exception as cache_err:
                    print(f"[complete_document] ⚠️ Could not update Redis cache: {cache_err}")

            return {
                "status": "success",
                "message": "✅ Document verification completed successfully! All required information has been saved.",
                "session_id": session_id,
                "doc_id": completion_result.get("doc_id"),
                "completed_fields": completion_result.get("completed_fields", []),
                "extracted_data": corrected_data,
            }
        else:
            error_message = completion_error or "Document completion failed"
            return {
                "status": "error",
                "message": f"❌ {error_message}",
                "session_id": session_id,
                "validation_errors": completion_result.get("validation_errors", []) if completion_result else []
            }
            
    except Exception as e:
        print(f"[complete_document] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  FINALIZE APPLICATION - INTEGRATION ORCHESTRATOR
#  Collects all data and triggers automation_agent
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/finalize-application")
async def finalize_application(request_data: dict):
    """
    Final integration endpoint that:
    1. Collects FlowManager state (user chat responses)
    2. Collects document extraction results (from pan_verification)
    3. Merges all data into automation_agent schema
    4. Copies files to automation_agent/docs/
    5. Writes automation_agent/data.json
    6. Triggers automation_agent/main.py
    7. Returns payment URL to frontend
    """
    session_id = request_data.get("session_id")
    user_id = request_data.get("user_id", "anonymous")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    try:
        from agent.flow_manager import FlowManager
        import shutil
        from pathlib import Path
        
        print(f"\n{'='*80}")
        print(f"FINALIZING APPLICATION - Session: {session_id}")
        print(f"{'='*80}\n")
        
        # ── Step 1: Load FlowManager state ───────────────────────────────────
        fm = FlowManager(session_id, user_id)
        if not fm.has_active_flow():
            raise HTTPException(
                status_code=400,
                detail="No active flow found. Please complete the application steps first."
            )
        
        state = fm.state
        print(f"[1/7] ✓ Loaded FlowManager state")
        print(f"      Service: {state.get('service_id')}")
        print(f"      Current step: {state.get('current_step')}")
        print(f"      Documents collected: {len(state.get('collected_docs', []))}")
        
        # ── Step 2: Load document extraction results ─────────────────────────
        # Documents are stored in storage/uploads/{session_id}/.
        # If the user finalized from a DIFFERENT session than the one they uploaded
        # from, we fall back to scanning ALL upload dirs for this user.
        upload_dir = UPLOAD_DIR / session_id
        if not upload_dir.exists() or not list(upload_dir.glob("*")):
            # Scan all session dirs and use the most recently modified one
            # that has files belonging to this user's flow (collected_docs list)
            print(f"[2/7] ⚠ Upload dir for session {session_id} empty — scanning all sessions...")
            best_dir = None
            best_mtime = 0
            for candidate in UPLOAD_DIR.iterdir():
                if candidate.is_dir() and list(candidate.glob("*")):
                    mtime = candidate.stat().st_mtime
                    if mtime > best_mtime:
                        best_mtime = mtime
                        best_dir = candidate
            if best_dir:
                upload_dir = best_dir
                print(f"[2/7] ↳ Using upload dir from session: {upload_dir.name}")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No documents found. Please upload required documents first."
                )

        # Collect all uploaded files
        uploaded_files = list(upload_dir.glob("*"))
        print(f"\n[2/7] ✓ Found {len(uploaded_files)} uploaded files")
        for f in uploaded_files:
            print(f"      - {f.name}")

        # Load extraction results from memory (stored during upload)
        from memory.memory_manager import MemoryManager
        mm = MemoryManager()

        # Build doc_types to look up — from flow state collected_docs,
        # falling back to inferring from filenames if list is empty
        doc_types_to_load = [d.get("doc_type") for d in state.get("collected_docs", []) if d.get("doc_type")]
        if not doc_types_to_load:
            # Infer doc types from uploaded filenames
            _FNAME_TO_TYPE = {
                "aadhaar": "aadhaar", "aadhar": "aadhaar", "jaadhar": "aadhaar",
                "photo": "photograph", "jphoto": "photograph",
                "sign": "signature", "jsign": "signature",
                "driving": "driving_license", "license": "driving_license",
            }
            for f in uploaded_files:
                fname = f.name.lower()
                for keyword, dtype in _FNAME_TO_TYPE.items():
                    if keyword in fname and dtype not in doc_types_to_load:
                        doc_types_to_load.append(dtype)
            print(f"[2/7] ↳ Inferred doc types from filenames: {doc_types_to_load}")

        # Determine the upload session id for building file path references
        upload_session_id = upload_dir.name
        
        # Collect extracted data for each document type
        extraction_data = {}
        for doc_type in doc_types_to_load:
            # Primary: session-scoped key (same session as upload)
            cached = mm._get(f"extraction:{upload_session_id}:{doc_type}")

            # Fallback 1: current session key (if re-uploaded in this session)
            if not cached and upload_session_id != session_id:
                cached = mm._get(f"extraction:{session_id}:{doc_type}")

            # Fallback 2: user-scoped key (cross-session, written on every upload)
            if not cached and user_id and user_id != "anonymous":
                user_key = f"extraction:{user_id}:{doc_type}"
                cached = mm._get(user_key)
                if cached:
                    print(f"      ↳ Loaded {doc_type} from user-scoped key (cross-session fallback)")

            if cached:
                extraction_data[doc_type] = json.loads(cached)

        # Fallback 3: Supabase pan_extractions table (written on every upload)
        # AND documents table (written on confirm_save) — permanent storage.
        if "aadhaar" not in extraction_data and user_id and user_id != "anonymous":
            print(f"      ↳ Redis miss for aadhaar — trying Supabase...")
            try:
                from supabase import create_client as _sb_create
                _sb_url = os.getenv("SUPABASE_URL", "")
                _sb_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")
                if _sb_url and _sb_key:
                    _sb = _sb_create(_sb_url, _sb_key)

                    def _try_decrypt(raw_ed):
                        """Decrypt if encrypted blob, else parse as JSON."""
                        if isinstance(raw_ed, dict):
                            return raw_ed
                        if not isinstance(raw_ed, str):
                            return {}
                        try:
                            import base64 as _b64
                            from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
                            _key_b64 = os.getenv("DATA_ENCRYPTION_KEY", "")
                            if _key_b64:
                                _raw = _b64.b64decode(raw_ed)
                                _key = _b64.b64decode(_key_b64)
                                _plain = _AESGCM(_key).decrypt(_raw[:12], _raw[12:], None).decode()
                                return json.loads(_plain)
                        except Exception:
                            pass
                        try:
                            return json.loads(raw_ed)
                        except Exception:
                            return {}

                    recovered = None

                    # Try pan_extractions first (written on every upload — most up to date)
                    try:
                        resp = _sb.table("pan_extractions") \
                                   .select("extracted_data") \
                                   .eq("auth_id", user_id) \
                                   .eq("doc_type", "aadhaar") \
                                   .order("updated_at", desc=True) \
                                   .limit(1).execute()
                        if resp.data:
                            recovered = _try_decrypt(resp.data[0].get("extracted_data"))
                            if recovered:
                                print(f"      ✓ Recovered from pan_extractions table")
                    except Exception as _t1:
                        # Table may not exist yet — silently skip
                        print(f"      ↳ pan_extractions table not available: {_t1}")

                    # Try documents table (written on confirm_save — user-verified data)
                    if not recovered:
                        try:
                            resp = _sb.table("documents") \
                                       .select("extracted_data") \
                                       .eq("auth_id", user_id) \
                                       .eq("doc_type", "aadhaar") \
                                       .order("created_at", desc=True) \
                                       .limit(1).execute()
                            if resp.data:
                                recovered = _try_decrypt(resp.data[0].get("extracted_data"))
                                if recovered:
                                    print(f"      ✓ Recovered from documents table")
                        except Exception:
                            pass

                    if recovered:
                        extraction_data["aadhaar"] = recovered
                        # Re-cache in Redis (30 days) so future calls are fast
                        mm._setex(
                            f"extraction:{user_id}:aadhaar",
                            60 * 60 * 24 * 30,
                            json.dumps(recovered)
                        )
                        print(f"      ✓ Re-cached in Redis for future use")
                    else:
                        print(f"      ⚠ No aadhaar data found in Supabase for user {user_id[:8]}...")
            except Exception as _sb_err:
                print(f"      ⚠ Supabase fallback failed: {_sb_err}")
        print(f"\n[3/7] ✓ Loaded extraction data for {len(extraction_data)} document types")
        for doc_type in extraction_data.keys():
            print(f"      - {doc_type}")
        
        # ── Step 3: Merge all data into automation_agent schema ──────────────
        print(f"\n[4/7] ⚙️  Merging data into automation_agent schema...")

        # ── Helper: decrypt field values encrypted by pan_verification ───────
        def _decrypt_field(v: str) -> str:
            """
            If a string value looks like an AES-256-GCM base64 blob
            (nonce[12] + ciphertext, base64-encoded), decrypt it.
            Otherwise return as-is.
            """
            if not isinstance(v, str) or len(v) < 20 or not v.endswith("="):
                return v
            try:
                import base64 as _b64
                raw = _b64.b64decode(v)
                if len(raw) < 13:
                    return v
                key_b64 = os.getenv("DATA_ENCRYPTION_KEY")
                if not key_b64:
                    return v
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                key = _b64.b64decode(key_b64)
                if len(key) != 32:
                    return v
                aesgcm = AESGCM(key)
                nonce, ct = raw[:12], raw[12:]
                plain = aesgcm.decrypt(nonce, ct, None).decode("utf-8")
                # Strip surrounding JSON quotes if value was json.dumps'd as string
                if plain.startswith('"') and plain.endswith('"'):
                    plain = plain[1:-1]
                return plain
            except Exception:
                return v  # not encrypted — return original

        def _decrypt_dict(data: dict) -> dict:
            """Decrypt all string field values in an extraction dict."""
            return {k: _decrypt_field(v) if isinstance(v, str) else v
                    for k, v in (data or {}).items()}

        # Helper function to split full name
        def split_name(full_name):
            """
            Split a name into (first, middle, last) following NSDL form rules:

            1 word   "LOHIT"       → first="LOHIT",  middle="",   last="L"
                                      (single name: use first letter as last-name initial)
            2 words  "LOHIT G"     → first="LOHIT",  middle="",   last="G"
                                      (second word is the initial / last name)
            3+ words "LOHIT G K"   → first="LOHIT",  middle="G",  last="K"
                                      (words between first and last become middle)
            """
            if not full_name:
                return "", "", ""
            parts = [p.upper() for p in full_name.strip().split() if p]
            if len(parts) == 1:
                # Single word — use first letter as last-name initial, middle empty
                return parts[0], "", parts[0][0]
            if len(parts) == 2:
                # Two words — no middle name
                return parts[0], "", parts[1]
            # Three or more — middle = everything between first and last
            return parts[0], " ".join(parts[1:-1]), parts[-1]
        
        # Get Aadhaar extraction if available — decrypt any encrypted field values
        aadhaar_data = _decrypt_dict(extraction_data.get("aadhaar", {}))
        driving_license_data = _decrypt_dict(extraction_data.get("driving_license", {}))

        if not aadhaar_data:
            print(f"\n[WARNING] No Aadhaar extraction data found in Redis for session {session_id}")
            print(f"      DOB, address, Aadhaar number and gender will be blank.")
            print(f"      Collected docs: {[d.get('doc_type') for d in state.get('collected_docs', [])]}")
            # Try alternative keys
            for alt_key in ['aadhar', 'aadhaar_card', 'other_document']:
                alt = _decrypt_dict(extraction_data.get(alt_key, {}))
                if alt and (alt.get("aadhaar_number") or alt.get("aadhar_number") or alt.get("dob")):
                    print(f"      Found usable data under key '{alt_key}' — using as aadhaar_data")
                    aadhaar_data = alt
                    break
        
        # Build the 30-field data.json schema

        # ── Applicant name: use Aadhaar-extracted first/middle/last directly.
        # The full_name collected from chat is NOT used for splitting here —
        # Aadhaar extraction gives pre-split fields that are more reliable.
        #
        # NSDL South Indian convention:
        #   first  = given name  (e.g. "LOHIT")
        #   middle = middle name if exists, else ""
        #   last   = father's initial (e.g. "G" from father "GOPALAKRISHNAN")
        #
        # Fallback chain for last name:
        #   1. Aadhaar last_name field (if VLM split it)
        #   2. First letter of father_name from Aadhaar (S/O line)
        #   3. First letter of grandfather_name from chat
        #   4. First letter of applicant's own first name (absolute last resort)
        first  = (aadhaar_data.get("first_name")  or "").upper()
        middle = (aadhaar_data.get("middle_name") or "").upper()
        last   = (aadhaar_data.get("last_name")   or "").upper()
        if not first:
            # last-resort: split the full name field from Aadhaar
            first, middle, last = split_name(aadhaar_data.get("name", ""))
        # If last is still empty, derive from father's name (South Indian convention)
        if first and not last:
            _father_for_initial = (
                aadhaar_data.get("father_name", "")
                or aadhaar_data.get("father_first_name", "")
                or state.get("grandfather_name", "")
            ).strip()
            last = _father_for_initial[0].upper() if _father_for_initial else first[0]

        # Get parent names
        # Father name — read from C/O / S/O / D/O / W/O line on Aadhaar card.
        # The card prints a single name string (e.g. "S/O: GOPALAKRISHNAN").
        # The VLM is asked to split it, but for single-word names it may return
        # father_last_name as null — so only trust the VLM split when both
        # first AND last are present. Otherwise fall through to split_name().
        # If split also can't produce a last name (single-word father name),
        # use the first letter of chat's grandfather_name as the last name initial.
        # Fallback chain:
        #   1. VLM pre-split (only if both first_name AND last_name are non-null)
        #   2. split_name(aadhaar father_name full string)
        #   3. split_name(chat grandfather_name)  ← last resort
        _vlm_f_first = aadhaar_data.get("father_first_name") or ""
        _vlm_f_last  = aadhaar_data.get("father_last_name")  or ""
        if _vlm_f_first and _vlm_f_last:
            f_first  = _vlm_f_first.upper()
            f_middle = (aadhaar_data.get("father_middle_name") or "").upper()
            f_last   = _vlm_f_last.upper()
        else:
            _father_full = (
                aadhaar_data.get("father_name")
                or state.get("grandfather_name", "")
            )
            f_first, f_middle, f_last = split_name(_father_full)
            # split_name already applies the single-name rule (last = initial).
            # Extra fallback: if last still empty, use grandfather_name initial.
            if f_first and not f_last:
                _gf_name = state.get("grandfather_name", "").strip()
                f_last = _gf_name[0].upper() if _gf_name else f_first[0]

        # Mother name — chat is primary (always collected as required field).
        # Aadhaar rarely prints mother's name, so it's a fallback only.
        # Same VLM trust rule as father: only use VLM pre-split when both
        # first AND last are non-null.
        #
        # Splitting rules for mother name:
        #   1 word  "DIVYA"         → first="DIVYA",  middle="",  last=father_initial (fallback)
        #   2 words "DIVYA G"       → first="DIVYA",  middle="",  last="G"  (initial is last name)
        #   3+words "DIVYA G KUMAR" → first="DIVYA",  middle="G", last="KUMAR"
        #   Middle name only exists when there's a word between first and last.
        #
        # Fallback chain:
        #   1. VLM pre-split from Aadhaar (only if both first + last non-null)
        #   2. split by word count from chat mother_name (primary — always collected)
        #   3. split from aadhaar mother_name (rare fallback)
        _vlm_m_first = aadhaar_data.get("mother_first_name") or ""
        _vlm_m_last  = aadhaar_data.get("mother_last_name")  or ""
        if _vlm_m_first and _vlm_m_last:
            m_first  = _vlm_m_first.upper()
            m_middle = (aadhaar_data.get("mother_middle_name") or "").upper()
            m_last   = _vlm_m_last.upper()
        else:
            _mother_full = (
                state.get("mother_name")
                or aadhaar_data.get("mother_name", "")
            )
            _mother_parts = [p.upper() for p in _mother_full.strip().split() if p]
            if len(_mother_parts) == 0:
                m_first = m_middle = m_last = ""
            elif len(_mother_parts) == 1:
                # Single word — first name only, last name = father's initial (set below)
                m_first  = _mother_parts[0]
                m_middle = ""
                m_last   = ""
            elif len(_mother_parts) == 2:
                # Two words — first name + initial/last name (no middle)
                # e.g. "DIVYA G" → first="DIVYA", middle="", last="G"
                m_first  = _mother_parts[0]
                m_middle = ""
                m_last   = _mother_parts[1]
            else:
                # Three or more words — first, middle(s), last
                # e.g. "DIVYA G KUMAR" → first="DIVYA", middle="G", last="KUMAR"
                m_first  = _mother_parts[0]
                m_middle = " ".join(_mother_parts[1:-1])
                m_last   = _mother_parts[-1]

            # For single-word names where last name is still empty,
            # use first letter of father's name as last name initial.
            # Final fallback: use first letter of the mother's own first name.
            if not m_last:
                _father_name = aadhaar_data.get("father_name", "").strip()
                if _father_name:
                    m_last = _father_name[0].upper()
                elif m_first:
                    m_last = m_first[0]
        
        # DOB: Aadhaar is primary — it is mandatory and always present.
        # Driving license is secondary (uploaded only as optional age proof).
        # Note: DOB is never collected through chat — flow_manager has no dob field,
        #       and even if user_profile has a dob from casual chat mention, it is
        #       unreliable (user-typed) so we deliberately ignore it here.
        # Cross-check: if both docs are present and agree → use Aadhaar value.
        #              if they differ → still trust Aadhaar (official ID).
        #              if Aadhaar has no dob → fall back to driving license.
        aadhaar_dob  = aadhaar_data.get("dob", "")
        dl_dob       = driving_license_data.get("dob", "")
        dob = aadhaar_dob or dl_dob
        if aadhaar_dob and dl_dob and aadhaar_dob != dl_dob:
            print(f"[finalize] DOB mismatch — Aadhaar: {aadhaar_dob!r}, DL: {dl_dob!r} — using Aadhaar")

        # Normalize DOB to DD/MM/YYYY (NSDL form mask format).
        # VLM may return various formats: "23/02/2007", "23-02-2007", "2007-02-23".
        def _normalize_dob(d: str) -> str:
            if not d:
                return ""
            d = d.strip()
            # Already DD/MM/YYYY
            import re as _re
            if _re.match(r"^\d{2}/\d{2}/\d{4}$", d):
                return d
            # DD-MM-YYYY → DD/MM/YYYY
            if _re.match(r"^\d{2}-\d{2}-\d{4}$", d):
                return d.replace("-", "/")
            # YYYY-MM-DD (ISO) → DD/MM/YYYY
            m = _re.match(r"^(\d{4})-(\d{2})-(\d{2})$", d)
            if m:
                return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
            # YYYY/MM/DD → DD/MM/YYYY
            m = _re.match(r"^(\d{4})/(\d{2})/(\d{2})$", d)
            if m:
                return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
            return d  # return as-is if unknown format

        dob = _normalize_dob(dob)
        
        # Aadhaar number — read directly from Aadhaar extraction.
        # VLM returns field as "aadhar_number" (may also be "aadhaar_number").
        # Format may be masked: "XXXX XXXX 1234" → strip spaces/dashes before splitting.
        # first_8: positions 0-7  (may be "XXXXXXXX" if masked — that's correct for NSDL form)
        # last_4:  positions 8-11 (always visible even on masked cards)
        aadhaar_raw = (
            aadhaar_data.get("aadhar_number")
            or aadhaar_data.get("aadhaar_number")
            or ""
        )
        aadhaar_number  = aadhaar_raw.replace(" ", "").replace("-", "")
        aadhaar_first_8 = aadhaar_number[:8]  if len(aadhaar_number) >= 8  else ""
        aadhaar_last_4  = aadhaar_number[-4:] if len(aadhaar_number) >= 4  else ""
        
        # Map delivery mode to automation_agent format
        delivery_mode = state.get("delivery_mode", "")
        delivery_option = "physical" if "physical" in delivery_mode.lower() else "soft"
        
        # Build complete data.json
        automation_data = {
            "first_name": first,
            "last_name": last,
            "middle_name": middle,
            "dob": dob,
            "email": (
                # Use exactly what the user typed/confirmed in chat — no case modification.
                # state["email"] is set in two ways:
                #   email_source="account" → user confirmed their login email (from _account_email)
                #   email_source="new"     → user typed a custom email (preserved as-is)
                state.get("email", "")
            ),
            # phone: use exactly what the user provided in chat (10-digit, +91 stripped by regex)
            "phone": state.get("mobile", ""),
            "aadhaar_first_8": aadhaar_first_8,
            "aadhaar_last_4": aadhaar_last_4,
            "name_on_aadhaar": aadhaar_data.get("name", ""),
            "gender": aadhaar_data.get("gender", ""),
            "father_first_name": f_first,
            "father_last_name": f_last,
            "mother_first_name": m_first,
            "mother_middle_name": m_middle,
            "mother_last_name": m_last,
            "residential_status": (
                # Pure chat — dedicated flow step (radio choice).
                # Values: "Resident", "Non-resident", "Resident but not ordinarily resident"
                # form_filler does exact radio match on this value.
                state.get("residential_status", "Resident")
            ),
            "source_of_income": (
                # Pure chat — dedicated flow step (radio choice).
                # May contain Tamil suffix e.g. "Salary | சம்பளம்"
                # form_filler strips Tamil via .split("|")[0].strip() before clicking.
                state.get("source_of_income", "No income")
            ),
            "address_for_comm": (
                # Pure chat — dedicated flow step (radio choice).
                # May contain Tamil suffix e.g. "Residence | வீடு"
                # form_filler strips Tamil via .split("|")[0].strip() before clicking.
                state.get("address_for_comm", "Residence")
            ),
            # ── Address fields — all from Aadhaar extraction only.
            # Never collected in chat. VLM splits address exactly as printed on card.
            # Note: form_filler fills #rCountry with area_locality (it's the Town/City
            #       field on NSDL form, despite the misleading element ID).
            "flat_room_door":  aadhaar_data.get("flat_room_door", ""),
            "building_village": aadhaar_data.get("building_village", ""),
            "road_street_post": aadhaar_data.get("road_street_post", ""),
            "area_locality":   aadhaar_data.get("area_locality", ""),
            "country":         aadhaar_data.get("country", "India"),
            "state":           aadhaar_data.get("state", ""),
            "pin_code":        aadhaar_data.get("pincode", ""),
            # verifier_place — place of signing, best approximation is the
            # district or locality from Aadhaar address
            "verifier_place": (
                aadhaar_data.get("district")
                or aadhaar_data.get("area_locality", "")
            ),
            "verifier_designation": "",   # left blank — "Self" selected via dropdown
            "delivery_option": delivery_option,
            "photo_file": "",
            "signature_file": "",
            "aadhaar_pdf": "",
            "birth_cert_pdf": "",  # Used for driving license (age proof document)
        }
        
        print(f"      ✓ Merged {len([v for v in automation_data.values() if v])} non-empty fields")
        
        # ── Step 4: Copy files to automation_agent/docs/ ─────────────────────
        print(f"\n[5/7] 📁 Copying files to automation_agent/docs/...")
        
        automation_agent_dir = Path(__file__).parent.parent.parent / "automation_agent"
        docs_dir = automation_agent_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Map extracted document types to automation_agent fields
        # Required: Aadhaar, Photo, Signature
        # Optional: Driving License (as age proof, mapped to birth_cert_pdf field)
        doc_type_mapping = {
            "aadhaar": {"field": "aadhaar_pdf",      "target": "jaadhar.pdf"},
            "photograph": {"field": "photo_file",    "target": "jphoto.jpeg"},
            "signature": {"field": "signature_file", "target": "jsign.jpeg"},
            "driving_license": {"field": "birth_cert_pdf", "target": "jbirthcert.pdf"},
        }
        
        # De-duplicate: keep only the LAST entry per doc_type, skip other_document
        # First build from flow state collected_docs
        seen = {}
        for doc in state.get("collected_docs", []):
            dt = doc.get("doc_type", "").lower()
            if dt and dt != "other_document":
                seen[dt] = doc

        # If collected_docs is empty (different session), infer from upload_dir filenames
        if not seen:
            _FNAME_TO_TYPE = {
                "aadhaar": "aadhaar", "aadhar": "aadhaar", "jaadhar": "aadhaar",
                "photo": "photograph", "jphoto": "photograph",
                "sign": "signature",   "jsign": "signature",
                "driving": "driving_license",
            }
            for f in upload_dir.glob("*"):
                if not f.is_file():
                    continue
                fname = f.name.lower()
                for keyword, dtype in _FNAME_TO_TYPE.items():
                    if keyword in fname and dtype not in seen:
                        seen[dtype] = {"doc_type": dtype, "filename": f.name}
                        break
            if seen:
                print(f"      ℹ️ collected_docs empty — inferred from filenames: {list(seen.keys())}")
        
        files_copied = 0
        for doc_type, doc in seen.items():
            filename = doc.get("filename", "")
            
            if not filename or doc_type not in doc_type_mapping:
                print(f"      ⚠️ Skipping unknown doc type: {doc_type} ({filename})")
                continue
            
            source_path = upload_dir / filename
            if not source_path.exists():
                # Try scanning the directory for a file starting with the doc_type prefix
                matches = list(upload_dir.glob(f"{doc_type}_*"))
                if matches:
                    source_path = sorted(matches)[-1]  # most recent
                    print(f"      ℹ️ Using scanned match: {source_path.name}")
                else:
                    print(f"      ⚠️ File not found: {filename}")
                    continue
            
            mapping = doc_type_mapping[doc_type]
            target_name = mapping["target"]
            field_name = mapping["field"]
            
            target_path = docs_dir / target_name
            shutil.copy2(source_path, target_path)
            automation_data[field_name] = f"docs/{target_name}"
            files_copied += 1
            print(f"      ✓ {doc_type.upper()}: {source_path.name} → {target_name}")
        
        print(f"      Total files copied: {files_copied}")
        
        # ── Step 5: Write automation_agent/INPUT.json ─────────────────────────
        print(f"\n[6/7] 💾 Writing automation_agent/INPUT.json...")

        import datetime as _dt
        # Stamp with metadata so we know when and from which session it was built
        automation_data["_last_updated"] = _dt.datetime.now().isoformat()
        automation_data["_session_id"]   = session_id

        input_json_path = automation_agent_dir / "INPUT.json"
        with open(input_json_path, "w", encoding="utf-8") as f:
            json.dump(automation_data, f, indent=4, ensure_ascii=False)

        print(f"      ✓ Written to {input_json_path}")
        print(f"      ℹ️ Data is preserved in INPUT.json after automation completes")

        # Also write to data.json for backward compatibility
        data_json_path = automation_agent_dir / "data.json"
        with open(data_json_path, "w", encoding="utf-8") as f:
            json.dump(automation_data, f, indent=4, ensure_ascii=False)
        
        # ── Step 6: Trigger automation_agent/main.py ─────────────────────────
        print(f"\n[7/7] 🤖 Triggering automation_agent...")
        
        # Check if automation should be triggered or just prepared
        trigger_automation = request_data.get("trigger_automation", False)
        
        if trigger_automation:
            # Call the automation_agent server (running on port 8003)
            automation_server_url = os.getenv("AUTOMATION_AGENT_URL", "http://localhost:8003")
            try:
                async with httpx.AsyncClient(timeout=360.0) as client:
                    print(f"      🤖 Calling automation server at {automation_server_url}/run ...")
                    resp = await client.post(
                        f"{automation_server_url}/run",
                        json={"data": automation_data, "session_id": session_id},
                    )
                
                if resp.status_code == 200:
                    result = resp.json()
                    print(f"      ✓ Automation server returned: {result.get('status')}")
                    return {
                        "status": "success",
                        "message": "✅ Application submitted successfully!",
                        "session_id": session_id,
                        "automation_triggered": True,
                        "payment_info": {
                            "url": result.get("payment_url"),
                            **result.get("payment_info", {}),
                        },
                        "data_prepared": automation_data,
                    }
                elif resp.status_code == 409:
                    return {
                        "status": "error",
                        "message": "⚠️ Automation is already running. Please wait for it to finish.",
                        "session_id": session_id,
                        "automation_triggered": False,
                    }
                else:
                    err = resp.json().get("detail", "Automation failed")
                    print(f"      ❌ Automation server error: {err}")
                    return {
                        "status": "partial",
                        "message": f"⚠️ Automation failed: {err}",
                        "session_id": session_id,
                        "automation_triggered": True,
                        "automation_error": err,
                        "data_prepared": automation_data,
                    }

            except httpx.ConnectError:
                return {
                    "status": "error",
                    "message": (
                        "⚠️ Automation agent is offline.\n\n"
                        "Start it with:\n"
                        "```\ncd automation_agent\n"
                        ".venv\\Scripts\\activate\n"
                        "uvicorn server:app --port 8003\n```"
                    ),
                    "session_id": session_id,
                    "automation_triggered": False,
                    "data_prepared": automation_data,
                }
            except Exception as e:
                print(f"      ❌ Error calling automation server: {e}")
                return {
                    "status": "partial",
                    "message": f"⚠️ Could not reach automation server: {str(e)}",
                    "session_id": session_id,
                    "automation_triggered": False,
                    "automation_error": str(e),
                    "data_prepared": automation_data,
                }
        else:
            # Just prepare data, don't trigger automation
            print(f"      ℹ️ Data prepared (automation not triggered)")
            return {
                "status": "success",
                "message": "✅ Application data prepared. Start automation_agent server and click Submit.",
                "session_id": session_id,
                "automation_triggered": False,
                "data_prepared": automation_data,
                "input_file": str(input_json_path)
            }
    
    except Exception as e:
        import traceback
        print(f"\n❌ Finalize application error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
