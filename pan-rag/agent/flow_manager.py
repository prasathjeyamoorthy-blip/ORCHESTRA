# agent/flow_manager.py
import json
import re
from pathlib import Path
from agent.service_flows import get_service, detect_service

SESSIONS_DIR = Path(__file__).parent.parent / "storage" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class FlowManager:
    """
    Manages the step-by-step guided flow for each user session.
    State is saved to disk AND mirrored to Upstash Redis so collected
    details (name, salary, docs, etc.) survive server restarts.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = self._load()
        # If no local file, try to recover from Upstash (server restart)
        if not self._path().exists():
            self.load_from_memory()

    # ── State persistence ────────────────────────────────────────
    def _path(self) -> Path:
        return SESSIONS_DIR / f"{self.session_id}.json"

    def _load(self) -> dict:
        path = self._path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {
            "session_id"         : self.session_id,
            "service_id"         : None,
            "current_step"       : None,
            "collected_docs"     : [],
            "pending_docs"       : [],
            "covered_categories" : [],
            "applicant_type"     : None,
            "pan_number"         : None,
            "aadhaar_number"     : None,
            "correction_type"    : None,
            "complete"           : False,
            # PAN application form fields
            "submission_mode"    : None,   # Q2: how to submit docs
            "delivery_mode"      : None,   # Q2b: physical+soft / soft only
            "aadhaar_photo"      : None,   # Q3: yes/no
            "source_of_income"   : None,   # Q4: checkbox (multiple)
            "address_for_comm"   : None,   # Q5: Residence/Office/RA
            "residential_status" : None,   # Q6: Resident/Non-resident/RNOR
            "rep_assessee"       : None,   # Q7: Yes/No — Appointing Representative Assessee
            # Personal details (collected in details_collection step)
            "full_name"          : None,   # Full name as in Aadhaar
            "mother_name"        : None,   # Mother's name
            "email"              : None,   # Email for correspondence
            "email_source"       : None,   # "account" | "new"
            "salary"             : None,   # Annual income / salary
            # Confirmation flow
            "details_confirmed"  : False,  # True once user confirms the summary
            "pending_modification": None,  # field name user wants to change
            "doc_confirmation_pending": False,
        }

    def save(self):
        """Save to disk and mirror to Upstash."""
        self._path().write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        self._persist_to_memory()

    def _persist_to_memory(self):
        try:
            from memory.memory_manager import MemoryManager
            mm = MemoryManager()
            snapshot = {
                "applicant_type"  : self.state.get("applicant_type"),
                "pan_number"      : self.state.get("pan_number"),
                "aadhaar_number"  : self.state.get("aadhaar_number"),
                "collected_docs"  : self.state.get("collected_docs", []),
                "service_id"      : self.state.get("service_id"),
                "current_step"    : self.state.get("current_step"),
                "complete"        : self.state.get("complete", False),
                "submission_mode" : self.state.get("submission_mode"),
                "delivery_mode"   : self.state.get("delivery_mode"),
                "aadhaar_photo"   : self.state.get("aadhaar_photo"),
                "source_of_income": self.state.get("source_of_income"),
                "address_for_comm": self.state.get("address_for_comm"),
                "residential_status": self.state.get("residential_status"),
                "rep_assessee"    : self.state.get("rep_assessee"),
                "full_name"       : self.state.get("full_name"),
                "mother_name"     : self.state.get("mother_name"),
                "email"           : self.state.get("email"),
                "email_source"    : self.state.get("email_source"),
                "salary"          : self.state.get("salary"),
                "details_confirmed": self.state.get("details_confirmed", False),
                "doc_confirmation_pending": self.state.get("doc_confirmation_pending", False),
            }
            if any(v for v in snapshot.values() if v):
                mm._setex(
                    f"flow:details:{self.session_id}",
                    60 * 60 * 24 * 7,
                    json.dumps(snapshot),
                )
        except Exception:
            pass

    def load_from_memory(self):
        try:
            from memory.memory_manager import MemoryManager
            mm = MemoryManager()
            data = mm._get(f"flow:details:{self.session_id}")
            if data:
                snapshot = json.loads(data)
                for field in (
                    "applicant_type", "pan_number", "aadhaar_number",
                    "collected_docs", "service_id", "current_step",
                    "complete", "doc_confirmation_pending",
                ):
                    val = snapshot.get(field)
                    if val is not None and not self.state.get(field):
                        self.state[field] = val
        except Exception:
            pass

    # ── Flow control ─────────────────────────────────────────────
    def has_active_flow(self) -> bool:
        return self.state["service_id"] is not None and not self.state["complete"]

    def start_flow(self, service_id: str):
        service = get_service(service_id)
        self.state["service_id"]         = service_id
        self.state["current_step"]       = service["steps"][0]
        self.state["pending_docs"]       = list(service["documents"].keys())
        self.state["collected_docs"]     = []
        self.state["covered_categories"] = []
        self.state["complete"]           = False
        self.save()

    def get_current_step(self) -> str:
        return self.state["current_step"]

    def advance_step(self):
        service = get_service(self.state["service_id"])
        steps   = service["steps"]
        current = self.state["current_step"]
        if current in steps:
            idx = steps.index(current)
            if idx + 1 < len(steps):
                self.state["current_step"] = steps[idx + 1]
            else:
                self.state["complete"] = True
        self.save()

    # ── Document tracking ────────────────────────────────────────
    def record_document(self, filename: str, doc_type: str):
        service   = get_service(self.state["service_id"])
        rules     = service.get("smart_rules", {})

        self.state["collected_docs"].append({
            "filename": filename,
            "doc_type": doc_type,
        })

        doc_lower = doc_type.lower()
        categories_covered = []
        for keyword, covers in rules.items():
            if keyword in doc_lower:
                categories_covered.extend(covers)
        if not categories_covered:
            categories_covered = [doc_type]

        for cat in categories_covered:
            if cat not in self.state["covered_categories"]:
                self.state["covered_categories"].append(cat)

        self.state["pending_docs"] = [
            doc for doc in self.state["pending_docs"]
            if doc not in self.state["covered_categories"]
        ]

        if not self.state["pending_docs"] and self.state["current_step"] == "documents":
            self.advance_step()

        self.save()

    def get_pending_docs(self) -> list[dict]:
        service = get_service(self.state["service_id"])
        docs    = service.get("documents", {})
        return [
            {"key": k, **v}
            for k, v in docs.items()
            if k in self.state["pending_docs"]
        ]

    def get_collected_docs(self) -> list:
        return self.state["collected_docs"]

    def is_complete(self) -> bool:
        return self.state["complete"]
