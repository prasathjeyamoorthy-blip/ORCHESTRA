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

# URL of the document upload agent (Flask, port 5001)
DOC_AGENT_URL = "http://localhost:5001/api/upload"

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
        "step_labels": _STEP_LABELS.get(step, {"en": step, "ta": step}),
        "completed_fields": completed,
        "missing_for_step": missing_for_step,
        "language": s.get("preferred_language", "en"),
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

# Document upload agent URL — running on port 8001
DOC_AGENT_URL = os.getenv("DOC_AGENT_URL", "http://localhost:8001/api/upload")

@router.post("/upload")
async def upload_document(
    session_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    message: str = Form(default=""),
):
    # Save file locally using {username}_{doctype} naming
    dest = UPLOAD_DIR / session_id
    dest.mkdir(parents=True, exist_ok=True)

    # Build stored filename: {username}_{doctype}.{ext}
    from agent.flow_manager import FlowManager as _FM
    _fm = _FM(session_id)
    _username = (_fm.state.get("full_name") or "user").split()[0].lower()
    import re as _re
    _username = _re.sub(r'[^a-z0-9]', '', _username) or "user"
    _ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    stored_filename = f"{_username}_{doc_type.lower().replace(' ', '_')}{_ext}"
    file_path = dest / stored_filename

    file_bytes = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # ── Forward to document upload agent for extraction + verification ──
    extraction_result = {}
    agent_error = None
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                DOC_AGENT_URL,
                data={"session_id": session_id, "doc_type": doc_type},
                files={"file": (file.filename, file_bytes, file.content_type or "application/octet-stream")},
            )
        if response.status_code == 200:
            extraction_result = response.json()
            print(f"\n✅ Extraction result for [{doc_type}] session [{session_id}]:")
            import json as _json
            print(_json.dumps(extraction_result, indent=2, ensure_ascii=False))
        else:
            agent_error = response.json().get("error", "Document agent returned an error")
            print(f"\n❌ Document agent error [{doc_type}]: {agent_error}")
    except httpx.ConnectError:
        agent_error = "Document extraction service is offline. File saved — extraction skipped."
        print(f"\n⚠️  Document agent is offline at {DOC_AGENT_URL} — is the Flask server running on port 8001?")
    except Exception as e:
        agent_error = f"Document extraction failed: {str(e)}"
        print(f"\n❌ Document extraction exception: {e}")

    # ── Extract form fields from the accompanying message text ──
    if message.strip():
        from agent.flow_manager import FlowManager
        fm = FlowManager(session_id)
        if fm.has_active_flow():
            merge_form_fields(fm, message)

    # ── Update conversation flow ──
    flow_result = handle_document_upload(
        session_id=session_id,
        filename=stored_filename,
        doc_type=doc_type,
    )

    # ── Build response ──
    chat_message = flow_result["answer"]
    if agent_error:
        chat_message += f"\n\n> ⚠️ {agent_error}"

    return {
        "filename": file.filename,
        "session_id": session_id,
        "message": chat_message,
        "complete": flow_result.get("complete", False),
        # Full extraction payload for frontend use
        "extraction": extraction_result if extraction_result else None,
        "verified": extraction_result.get("verified", False),
        "validation_errors": extraction_result.get("validation_errors", []),
    }