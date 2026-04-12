# agent/receptionist.py
from agent.service_flows import detect_service, get_service, SERVICES
from agent.flow_manager import FlowManager


def handle_message(
    question: str,
    session_id: str,
    language: str = "en",
    rag_answer: str = None,
) -> dict | None:
    """
    Main receptionist logic.
    Returns a guided response dict if agent handles it.
    Returns None if RAG should handle it normally.
    """

    flow = FlowManager(session_id)

    # ── Case 1: User has an active flow → continue it ───────────
    if flow.has_active_flow():
        return _continue_flow(flow, question, language)

    # ── Case 2: Detect a new service request ────────────────────
    service_id = detect_service(question)
    if service_id:
        flow.start_flow(service_id)
        return _start_flow_response(flow, language)

    # ── Case 3: No service detected → let RAG handle it ─────────
    return None


def _start_flow_response(flow: FlowManager, language: str) -> dict:
    """Generate the opening message for a new service flow."""
    service = get_service(flow.state["service_id"])
    step    = flow.get_current_step()

    name    = service["name"]
    form    = service["form"]

    if step == "applicant_type":
        answer = (
            f"I'd be happy to help you with **{name}**! 😊\n\n"
            f"This uses **{form}**.\n\n"
            f"First, are you applying as:\n"
            f"1. Indian Citizen\n"
            f"2. Indian Company / HUF / Firm\n"
            f"3. Foreign Citizen / Entity\n\n"
            f"Please type 1, 2, or 3."
        )

    elif step == "pan_number":
        answer = (
            f"I'll help you with **{name}**! 😊\n\n"
            f"Please share your **existing PAN number** to get started."
        )

    elif step == "aadhaar_number":
        answer = (
            f"To link your Aadhaar with PAN, I'll need:\n"
            f"1. Your **PAN number**\n"
            f"2. Your **Aadhaar number**\n\n"
            f"Please share your PAN number first."
        )

    elif step == "documents":
        answer = _ask_for_documents(flow)

    else:
        answer = f"Let's get started with **{name}**! 😊 {_ask_for_documents(flow)}"

    return {
        "answer"   : answer,
        "sources"  : [],
        "followups": [],
        "guided"   : True,
        "step"     : step,
        "service"  : flow.state["service_id"],
    }


def _continue_flow(flow: FlowManager, user_input: str, language: str) -> dict:
    """Continue an existing service flow based on user input."""
    step       = flow.get_current_step()
    service_id = flow.state["service_id"]

    # ── Applicant type step ──────────────────────────────────────
    if step == "applicant_type":
        inp = user_input.strip()
        if "1" in inp or "indian citizen" in inp.lower():
            flow.state["applicant_type"] = "indian_citizen"
            flow.advance_step()
            flow.save()
            answer = _ask_for_documents(flow)

        elif "2" in inp or "company" in inp.lower() or "huf" in inp.lower():
            flow.state["applicant_type"] = "indian_entity"
            flow.advance_step()
            flow.save()
            answer = _ask_for_documents(flow)

        elif "3" in inp or "foreign" in inp.lower():
            # Switch to foreign flow
            flow.start_flow("pan_apply_foreign")
            answer = (
                "Got it! For foreign citizens/entities we use **Form 49AA**.\n\n"
                + _ask_for_documents(flow)
            )

        else:
            answer = (
                "Please select:\n"
                "1. Indian Citizen\n"
                "2. Indian Company / HUF / Firm\n"
                "3. Foreign Citizen / Entity"
            )

        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── PAN number step ──────────────────────────────────────────
    elif step == "pan_number":
        pan = _extract_pan(user_input)
        if pan:
            flow.state["pan_number"] = pan
            flow.advance_step()
            flow.save()
            next_step = flow.get_current_step()

            if next_step == "aadhaar_number":
                answer = f"✅ PAN number **{pan}** noted!\n\nNow please share your **Aadhaar number**."
            elif next_step == "documents":
                answer = f"✅ PAN number **{pan}** noted!\n\n" + _ask_for_documents(flow)
            elif next_step == "summary" or flow.is_complete():
                answer = _generate_summary(flow)
            else:
                answer = f"✅ PAN number **{pan}** noted! Let's continue."
        else:
            answer = (
                "I couldn't detect a valid PAN number. "
                "PAN is a 10-character code like **ABCDE1234F**.\n"
                "Please enter your PAN number."
            )

        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── Aadhaar number step ──────────────────────────────────────
    elif step == "aadhaar_number":
        aadhaar = _extract_aadhaar(user_input)
        if aadhaar:
            flow.state["aadhaar_number"] = aadhaar
            flow.advance_step()
            flow.save()
            answer = _generate_summary(flow)
        else:
            answer = (
                "I couldn't detect a valid Aadhaar number. "
                "Aadhaar is a 12-digit number like **1234 5678 9012**.\n"
                "Please enter your Aadhaar number."
            )

        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── Correction type step ─────────────────────────────────────
    elif step == "correction_type":
        flow.state["correction_type"] = user_input
        flow.advance_step()
        flow.save()
        answer = (
            f"Got it — correcting: **{user_input}**.\n\n"
            + _ask_for_documents(flow)
        )
        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── Documents step ───────────────────────────────────────────
    elif step == "documents":
        # User might be typing about docs but not uploading yet
        # Just remind them what's needed
        answer = (
            "Please upload your documents using the upload button. 📎\n\n"
            + _ask_for_documents(flow)
        )
        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": step}

    # ── Summary / complete ───────────────────────────────────────
    elif step == "summary" or flow.is_complete():
        answer = _generate_summary(flow)
        return {"answer": answer, "sources": [], "followups": [], "guided": True, "step": "summary"}

    return None


def handle_document_upload(
    session_id: str,
    filename: str,
    doc_type: str,
) -> dict:
    """Called when user uploads a document."""
    flow = FlowManager(session_id)

    if not flow.has_active_flow():
        return {
            "answer"  : "✅ Document received! If you'd like to start a PAN service, just let me know what you need help with.",
            "guided"  : False,
            "complete": False,
        }

    flow.record_document(filename, doc_type)
    pending = flow.get_pending_docs()
    service = get_service(flow.state["service_id"])
    rules   = service.get("smart_rules", {})

    # Check if Aadhaar smart rule applied
    smart_note = ""
    for keyword, covers in rules.items():
        if keyword in doc_type.lower():
            labels = [service["documents"][c]["label"] for c in covers if c in service["documents"]]
            smart_note = f"\n\n✨ Great news! Your {doc_type} covers: **{', '.join(labels)}**"

    if not pending:
        # All docs collected
        answer = (
            f"✅ **{filename}** received!{smart_note}\n\n"
            f"🎉 All documents collected! Let me summarise your application.\n\n"
            + _generate_summary(flow)
        )
        return {"answer": answer, "guided": True, "complete": True}

    # Still more docs needed
    next_doc = pending[0]
    options  = "\n".join([f"   • {o}" for o in next_doc["options"]])
    answer   = (
        f"✅ **{filename}** received!{smart_note}\n\n"
        f"Still needed — **{next_doc['label']}**:\n{options}\n\n"
        f"Please upload this document to continue."
    )
    return {"answer": answer, "guided": True, "complete": False}


# ── Helper functions ─────────────────────────────────────────────
def _ask_for_documents(flow: FlowManager) -> str:
    """Generate a message listing all required documents."""
    pending = flow.get_pending_docs()
    service = get_service(flow.state["service_id"])

    if not pending:
        return "All documents have been collected! ✅"

    lines = ["Please upload the following documents 📎:\n"]
    for i, doc in enumerate(pending, 1):
        optional = " *(optional)*" if doc.get("optional") else ""
        options  = ", ".join(doc["options"])
        lines.append(f"**{i}. {doc['label']}**{optional}")
        lines.append(f"   Accepted: {options}\n")

    lines.append("You can upload them one by one using the upload button.")
    return "\n".join(lines)


def _generate_summary(flow: FlowManager) -> str:
    """Generate a final summary of the collected information."""
    service   = get_service(flow.state["service_id"])
    collected = flow.get_collected_docs()

    lines = [
        f"## 📋 Application Summary\n",
        f"**Service:** {service['name']}",
        f"**Form:** {service['form']}\n",
    ]

    if flow.state.get("pan_number"):
        lines.append(f"**PAN Number:** {flow.state['pan_number']}")

    if flow.state.get("aadhaar_number"):
        lines.append(f"**Aadhaar Number:** {flow.state['aadhaar_number']}")

    if flow.state.get("applicant_type"):
        lines.append(f"**Applicant Type:** {flow.state['applicant_type'].replace('_', ' ').title()}")

    if collected:
        lines.append(f"\n**Documents Uploaded ({len(collected)}):**")
        for doc in collected:
            lines.append(f"  ✅ {doc['filename']} ({doc['doc_type']})")

    if flow.state["service_id"] == "aadhaar_link":
        lines.append(
            f"\n**Next Steps:**\n"
            f"To complete Aadhaar-PAN linking:\n"
            f"1. Visit incometax.gov.in\n"
            f"2. Go to Link Aadhaar section\n"
            f"3. Enter PAN: {flow.state.get('pan_number', '—')}\n"
            f"4. Enter Aadhaar: {flow.state.get('aadhaar_number', '—')}\n"
            f"5. Pay ₹1000 fee and submit"
        )
    else:
        lines.append(
            f"\n**Next Steps:**\n"
            f"Your application details are ready. "
            f"Our team will review your documents and proceed with the {service['name']}. "
            f"You will be notified once the application is submitted."
        )

    return "\n".join(lines)


def _extract_pan(text: str) -> str | None:
    """Extract PAN number from text."""
    import re
    match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text.upper())
    return match.group(0) if match else None


def _extract_aadhaar(text: str) -> str | None:
    """Extract Aadhaar number from text."""
    import re
    digits = re.sub(r'\D', '', text)
    return digits if len(digits) == 12 else None