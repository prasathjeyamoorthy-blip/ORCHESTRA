# agent/receptionist.py
import re
from agent.service_flows import detect_service, get_service, SERVICES
from agent.flow_manager import FlowManager


# ── Off-topic detector ────────────────────────────────────────────
# When user is mid-flow but asks an informational/unrelated question,
# return None so RAG handles it — don't force a flow response.
_OFF_TOPIC_PATTERN = re.compile(
    r"^(why|what|how\s+does|how\s+is|what\s+is|what\s+are|"
    r"should\s+i|do\s+i\s+need|is\s+it|are\s+there|"
    r"tell\s+me|explain|describe|difference|benefit|reason|"
    r"purpose|importance|advantage|when\s+should|who\s+needs|"
    r"what\s+happens|what\s+if|how\s+long|how\s+much|"
    r"what\s+is\s+the\s+fee|i\s+want\s+to\s+know|"
    r"i\s+want\s+to\s+understand|curious)",
    re.IGNORECASE
)

# Short inputs that are clearly flow responses (numbers, yes/no, names)
_FLOW_RESPONSE_PATTERN = re.compile(
    r"^(\d+|yes|no|ok|okay|sure|ready|done|"
    r"indian|foreign|company|huf|firm|citizen|"
    r"[A-Z]{5}[0-9]{4}[A-Z]|"   # PAN number
    r"\d{12}|"                    # Aadhaar number
    r".{1,60})$",                 # anything short enough to be a step answer
    re.IGNORECASE
)

# ── Cancellation detector ─────────────────────────────────────────
_CANCEL_PATTERN = re.compile(
    r"^(nah|nope|no|stop|cancel|quit|exit|nevermind|never mind|"
    r"forget it|forget this|leave it|not now|not interested|"
    r"i changed my mind|go back|abort|end|close|done for now|"
    r"skip|skip this|i don't want|i dont want|not anymore)\b",
    re.IGNORECASE
)

# ── Upload-now / deferral detector ───────────────────────────────
# Catches: "i will upload afterwards", "upload later", "let me upload now",
# "i want to upload", "upload the documents", "ready to upload" etc.
_UPLOAD_NOW_PATTERN = re.compile(
    r"(upload|submit|attach|send|provide|share|give).{0,40}(now|later|afterwards|after|soon|first|document|file|proof|aadhaar|photo)"
    r"|"
    r"(later|afterwards|after\s+this|after\s+that|will\s+do\s+it|do\s+it\s+later).{0,30}(upload|submit|document|file)"
    r"|"
    r"\b(i\s+will\s+upload|let\s+me\s+upload|i\s+want\s+to\s+upload|ready\s+to\s+upload|upload\s+now|upload\s+the\s+doc)",
    re.IGNORECASE
)

def _is_upload_now(question: str) -> bool:
    return bool(_UPLOAD_NOW_PATTERN.search(question.strip()))

def _is_cancellation(question: str) -> bool:
    return bool(_CANCEL_PATTERN.match(question.strip()))


def _is_off_topic_during_flow(question: str) -> bool:
    """
    Returns True if the question is informational/off-topic
    and should bypass the active flow to go to RAG.
    """
    q = question.strip()
    # If it starts with a question word → off-topic
    if _OFF_TOPIC_PATTERN.match(q):
        return True
    # If it's long and contains question marks → likely informational
    if len(q) > 80 and '?' in q:
        return True
    return False


def handle_message(
    question: str,
    session_id: str,
    language: str = "en",
    rag_answer: str = None,
) -> dict | None:
    flow = FlowManager(session_id)

    if flow.has_active_flow():
        # Cancellation — user wants to stop the flow
        if _is_cancellation(question):
            flow.state["service_id"] = None
            flow.state["complete"] = True
            flow.save()
            return {
                "answer"   : "No problem! I've stopped the application process. Feel free to ask me anything else about PAN services whenever you're ready.",
                "sources"  : [],
                "followups": [],
                "guided"   : False,
                "close_form": True,
            }

        # Upload intent mid-flow — open the panel only if this service has documents
        if _is_upload_now(question):
            service = get_service(flow.state.get("service_id", ""))
            if service.get("documents"):
                return {
                    "answer"     : "Sure! Opening the upload panel for you now.",
                    "sources"    : [],
                    "followups"  : [],
                    "guided"     : True,
                    "open_upload": True,
                }

        # Let informational questions bypass the flow → go to RAG
        if _is_off_topic_during_flow(question):
            return None
        return _continue_flow(flow, question, language)

    service_id = detect_service(question)
    if service_id:
        flow.start_flow(service_id)
        return _start_flow_response(flow, language)

    return None


def _start_flow_response(flow: FlowManager, language: str) -> dict:
    service = get_service(flow.state["service_id"])
    step    = flow.get_current_step()
    name    = service["name"]
    form    = service["form"]

    if step == "applicant_type":
        answer = (
            f"Sure! Let's get your **{name}** sorted.\n\n"
            f"Quick question — which of these applies to you?\n\n"
            f"**1.** Indian Citizen\n"
            f"**2.** Indian Company / HUF / Firm\n"
            f"**3.** Foreign Citizen or Entity\n\n"
            f"Just reply with 1, 2, or 3 and we'll take it from there."
        )

    elif step == "pan_number":
        answer = (
            f"On it! To get started with **{name}**, I'll need your existing PAN number.\n\n"
            f"It's a 10-character code — looks like **ABCDE1234F**. Go ahead and share it."
        )

    elif step == "aadhaar_number":
        answer = (
            f"To link your Aadhaar with PAN, I just need two things from you:\n\n"
            f"**1.** Your PAN number\n"
            f"**2.** Your Aadhaar number\n\n"
            f"Let's start — what's your PAN number?"
        )

    elif step == "documents":
        answer = _ask_for_documents(flow)

    else:
        answer = f"Let's get started with **{name}**!\n\n" + _ask_for_documents(flow)

    return {
        "answer"   : answer,
        "sources"  : [],
        "followups": [],
        "guided"   : True,
        "step"     : step,
        "service"  : flow.state["service_id"],
    }


def _continue_flow(flow: FlowManager, user_input: str, language: str) -> dict:
    step       = flow.get_current_step()
    service_id = flow.state["service_id"]

    # ── Applicant type ───────────────────────────────────────────
    if step == "applicant_type":
        inp = user_input.strip()
        if "1" in inp or "indian citizen" in inp.lower():
            flow.state["applicant_type"] = "indian_citizen"
            flow.advance_step()
            flow.save()
            answer = "Got it — applying as an **Indian Citizen**.\n\n" + _ask_for_documents(flow)

        elif "2" in inp or "company" in inp.lower() or "huf" in inp.lower():
            flow.state["applicant_type"] = "indian_entity"
            flow.advance_step()
            flow.save()
            answer = "Got it — applying as an **Indian Company / HUF / Firm**.\n\n" + _ask_for_documents(flow)

        elif "3" in inp or "foreign" in inp.lower():
            flow.start_flow("pan_apply_foreign")
            answer = (
                "Got it — for foreign citizens and entities we use **Form 49AA**.\n\n"
                + _ask_for_documents(flow)
            )

        else:
            answer = (
                "Hmm, I didn't catch that. Could you pick one of these?\n\n"
                "**1.** Indian Citizen\n"
                "**2.** Indian Company / HUF / Firm\n"
                "**3.** Foreign Citizen or Entity"
            )

        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── PAN number ───────────────────────────────────────────────
    elif step == "pan_number":
        pan = _extract_pan(user_input)
        if pan:
            flow.state["pan_number"] = pan
            flow.advance_step()
            flow.save()
            next_step = flow.get_current_step()

            if next_step == "aadhaar_number":
                answer = f"Got your PAN — **{pan}**.\n\nNow I need your **Aadhaar number** (12 digits). Go ahead!"
            elif next_step == "documents":
                answer = f"PAN **{pan}** noted!\n\n" + _ask_for_documents(flow)
            elif next_step == "summary" or flow.is_complete():
                answer = _generate_summary(flow)
            else:
                answer = f"PAN **{pan}** saved. Let's keep going!"
        else:
            answer = (
                "That doesn't look like a valid PAN number.\n\n"
                "PAN is a 10-character alphanumeric code — for example, **ABCDE1234F**.\n"
                "Could you double-check and try again?"
            )

        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── Aadhaar number ───────────────────────────────────────────
    elif step == "aadhaar_number":
        aadhaar = _extract_aadhaar(user_input)
        if aadhaar:
            flow.state["aadhaar_number"] = aadhaar
            flow.advance_step()
            flow.save()
            answer = _generate_summary(flow)
        else:
            answer = (
                "That doesn't look like a valid Aadhaar number.\n\n"
                "Aadhaar is a 12-digit number — like **1234 5678 9012**.\n"
                "Please check and enter it again."
            )

        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── Correction type ──────────────────────────────────────────
    elif step == "correction_type":
        flow.state["correction_type"] = user_input
        flow.advance_step()
        flow.save()
        answer = (
            f"Noted — we'll correct: **{user_input}**.\n\n"
            + _ask_for_documents(flow)
        )
        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── Documents ────────────────────────────────────────────────
    elif step == "documents":
        inp = user_input.strip().lower()
        if inp in ("yes", "y", "yeah", "yep", "sure", "ok", "okay", "ready"):
            # Signal frontend to open upload panel
            return {
                "answer"      : "Great! The upload panel is now open. Please upload your **Aadhaar Card**, **Driving License**, and **Passport-size Photograph** one at a time.",
                "sources"     : [],
                "followups"   : [],
                "guided"      : True,
                "step"        : step,
                "open_upload" : True,
            }
        answer = (
            "Whenever you're ready, just reply **Yes** and I'll open the upload panel for you.\n\n"
            + _ask_for_documents(flow)
        )
        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── Summary / complete ───────────────────────────────────────
    elif step == "summary" or flow.is_complete():
        answer = _generate_summary(flow)
        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": "summary"}

    return None


def handle_document_upload(session_id: str, filename: str, doc_type: str) -> dict:
    flow = FlowManager(session_id)

    if not flow.has_active_flow():
        return {
            "answer"  : "Document received! If you'd like to start a PAN service, just let me know what you need help with.",
            "guided"  : False,
            "complete": False,
        }

    flow.record_document(filename, doc_type)
    pending = flow.get_pending_docs()
    service = get_service(flow.state["service_id"])
    rules   = service.get("smart_rules", {})

    smart_note = ""
    for keyword, covers in rules.items():
        if keyword in doc_type.lower():
            labels = [service["documents"][c]["label"] for c in covers if c in service["documents"]]
            smart_note = f"\n\nYour {doc_type} covers: **{', '.join(labels)}** — nice, that saves you some steps!"

    if not pending:
        answer = (
            f"**{filename}** received!{smart_note}\n\n"
            f"That's everything we need. Here's a summary of your application:\n\n"
            + _generate_summary(flow)
        )
        return {"answer": answer, "guided": True, "complete": True}

    next_doc = pending[0]
    options  = "\n".join([f"- {o}" for o in next_doc["options"]])
    answer   = (
        f"**{filename}** uploaded!{smart_note}\n\n"
        f"One more — I still need your **{next_doc['label']}**.\n\n"
        f"Accepted formats:\n{options}\n\n"
        f"Upload it whenever you're ready."
    )
    return {"answer": answer, "guided": True, "complete": False}


# ── Helpers ──────────────────────────────────────────────────────

def _ask_for_documents(flow: FlowManager) -> str:
    pending = flow.get_pending_docs()

    if not pending:
        return "All documents are in — you're good to go!"

    DOC_EXPLANATIONS = {
        "identity_proof":       "Confirms who you are — mandatory KYC for all PAN applications under Income Tax rules.",
        "address_proof":        "Your address is permanently recorded on the PAN database and used for official correspondence.",
        "dob_proof":            "Your date of birth is permanently linked to your PAN and used across tax filing and bank KYC.",
        "address_proof_foreign":"Establishes your country of residence for tax treaty and compliance purposes.",
        "address_proof_india":  "Helps with faster processing and local correspondence if you have an Indian address.",
        "photograph":           "Printed on your physical PAN card and used for visual identity verification at banks and government offices.",
        "correction_proof":     "Required to verify the change and prevent fraud in the Income Tax database.",
    }

    lines = ["Here's what I need from you:\n"]
    for i, doc in enumerate(pending, 1):
        optional = " (optional)" if doc.get("optional") else ""
        options  = ", ".join(doc["options"])
        why      = DOC_EXPLANATIONS.get(doc["key"], "Required for your PAN application.")
        lines.append(f"### {i}. {doc['label']}{optional}")
        lines.append(f"> {why}")
        lines.append(f"Accepted: {options}\n")

    lines.append("---")
    lines.append("Ready to upload? Reply **Yes** and I'll open the upload panel for you.")
    return "\n".join(lines)


def _generate_summary(flow: FlowManager) -> str:
    service   = get_service(flow.state["service_id"])
    collected = flow.get_collected_docs()

    lines = [
        f"Here's a summary of what we've collected:\n",
        f"**Service:** {service['name']}",
        f"**Form:** {service['form']}",
    ]

    if flow.state.get("pan_number"):
        lines.append(f"**PAN:** {flow.state['pan_number']}")

    if flow.state.get("aadhaar_number"):
        lines.append(f"**Aadhaar:** {flow.state['aadhaar_number']}")

    if flow.state.get("applicant_type"):
        lines.append(f"**Applicant:** {flow.state['applicant_type'].replace('_', ' ').title()}")

    if collected:
        lines.append(f"\n**Documents ({len(collected)}):**")
        for doc in collected:
            lines.append(f"- {doc['filename']} ({doc['doc_type']})")

    if flow.state["service_id"] == "aadhaar_link":
        lines.append(
            f"\n**What to do next:**\n"
            f"1. Go to incometax.gov.in\n"
            f"2. Click on 'Link Aadhaar'\n"
            f"3. Enter PAN: **{flow.state.get('pan_number', '—')}**\n"
            f"4. Enter Aadhaar: **{flow.state.get('aadhaar_number', '—')}**\n"
            f"5. Pay the ₹1000 fee and submit"
        )
    else:
        lines.append(
            f"\nYou're all set! Our team will review your documents and move forward with the **{service['name']}**. "
            f"We'll keep you posted."
        )

    return "\n".join(lines)


def _extract_pan(text: str) -> str | None:
    import re
    match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text.upper())
    return match.group(0) if match else None


def _extract_aadhaar(text: str) -> str | None:
    import re
    digits = re.sub(r'\D', '', text)
    return digits if len(digits) == 12 else None
