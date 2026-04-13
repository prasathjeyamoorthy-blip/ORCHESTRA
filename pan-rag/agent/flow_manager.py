# agent/flow_manager.py
import json
from pathlib import Path
from agent.service_flows import get_service, detect_service

SESSIONS_DIR = Path(__file__).parent.parent / "storage" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class FlowManager:
    """
    Manages the step-by-step guided flow for each user session.
    Saves state to disk so users can continue across sessions.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = self._load()

    # ── State persistence ────────────────────────────────────────
    def _path(self) -> Path:
        return SESSIONS_DIR / f"{self.session_id}.json"

    def _load(self) -> dict:
        path = self._path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {
            "session_id"         : self.session_id,
            "service_id"         : None,   # which service is active
            "current_step"       : None,   # which step we're on
            "collected_docs"     : [],     # docs uploaded so far
            "pending_docs"       : [],     # docs still needed
            "covered_categories" : [],     # doc categories already satisfied
            "applicant_type"     : None,   # indian / foreign
            "pan_number"         : None,
            "aadhaar_number"     : None,
            "correction_type"    : None,
            "complete"           : False,
        }

    def save(self):
        self._path().write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

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
        service  = get_service(self.state["service_id"])
        steps    = service["steps"]
        current  = self.state["current_step"]
        if current in steps:
            idx = steps.index(current)
            if idx + 1 < len(steps):
                self.state["current_step"] = steps[idx + 1]
            else:
                self.state["complete"] = True
        self.save()

    # ── Document tracking ────────────────────────────────────────
    def record_document(self, filename: str, doc_type: str):
        """
        Record an uploaded document.
        Applies smart rules (e.g. Aadhaar covers 3 categories).
        """
        service  = get_service(self.state["service_id"])
        rules    = service.get("smart_rules", {})

        self.state["collected_docs"].append({
            "filename": filename,
            "doc_type": doc_type,
        })

        # Apply smart rules
        doc_lower = doc_type.lower()
        categories_covered = []
        for keyword, covers in rules.items():
            if keyword in doc_lower:
                categories_covered.extend(covers)

        # If no smart rule matched, it covers its own stated category
        if not categories_covered:
            categories_covered = [doc_type]

        # Mark categories as covered
        for cat in categories_covered:
            if cat not in self.state["covered_categories"]:
                self.state["covered_categories"].append(cat)

        # Update pending docs
        self.state["pending_docs"] = [
            doc for doc in self.state["pending_docs"]
            if doc not in self.state["covered_categories"]
        ]

        # If no more pending docs, advance to next step
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