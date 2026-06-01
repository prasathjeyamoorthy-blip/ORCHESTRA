"""
cross_validator.py
──────────────────
Cross-validates extracted data across all uploaded documents for a PAN application.

Documents supported:
  - aadhaar        : name, dob, gender, address fields
  - driving_license: name, dob, state
  - photograph     : face quality checks

Rules applied:
  1. Name consistency  — name on Aadhaar must match name on Driving License
  2. DOB consistency   — DOB on Aadhaar must match DOB on Driving License
  3. Photo liveness    — photograph must have a face (can't cross-check identity,
                         but ensures it's a real photo not a document scan)
  4. Confidence gate   — if any doc has low confidence, flag for manual review
  5. Document type     — each doc must be the correct type (not a random image)

Usage:
    from cross_validator import CrossValidator

    cv = CrossValidator()
    cv.add("aadhaar",         aadhaar_extracted_dict)
    cv.add("driving_license", dl_extracted_dict)
    cv.add("photograph",      photo_extracted_dict)

    result = cv.validate()
    # result.passed       → bool
    # result.errors       → list[str]  (hard failures — block submission)
    # result.warnings     → list[str]  (soft issues — flag for review)
    # result.cross_checks → list[dict] (detailed per-check results)
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_name(name: Optional[str]) -> str:
    """Lowercase, strip titles/punctuation, collapse whitespace."""
    if not name:
        return ""
    name = name.lower()
    # Remove common titles
    for title in ("mr.", "mrs.", "ms.", "dr.", "shri", "smt.", "kumari", "s/o", "d/o", "w/o", "c/o"):
        name = name.replace(title, "")
    # Remove non-alpha except spaces
    name = re.sub(r"[^a-z\s]", "", name)
    return " ".join(name.split())


def _name_similarity(a: str, b: str) -> float:
    """
    Token-based similarity: what fraction of tokens in the shorter name
    appear in the longer name. Returns 0.0–1.0.
    """
    a_tokens = set(_normalise_name(a).split())
    b_tokens = set(_normalise_name(b).split())
    if not a_tokens or not b_tokens:
        return 0.0
    shorter = a_tokens if len(a_tokens) <= len(b_tokens) else b_tokens
    longer  = a_tokens if len(a_tokens) >  len(b_tokens) else b_tokens
    overlap = shorter & longer
    return len(overlap) / len(shorter)


def _normalise_dob(dob: Optional[str]) -> Optional[str]:
    """Normalise DOB to DD/MM/YYYY. Handles DD-MM-YYYY and YYYY-MM-DD."""
    if not dob:
        return None
    dob = dob.strip()
    # Already DD/MM/YYYY
    if re.match(r"^\d{2}/\d{2}/\d{4}$", dob):
        return dob
    # DD-MM-YYYY
    if re.match(r"^\d{2}-\d{2}-\d{4}$", dob):
        return dob.replace("-", "/")
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", dob)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    return dob  # return as-is if unrecognised


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class CrossValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)       # hard failures
    warnings: list[str] = field(default_factory=list)     # soft flags
    cross_checks: list[dict] = field(default_factory=list) # per-check detail

    def to_dict(self) -> dict:
        return {
            "passed":       self.passed,
            "errors":       self.errors,
            "warnings":     self.warnings,
            "cross_checks": self.cross_checks,
        }


# ── CrossValidator ────────────────────────────────────────────────────────────

class CrossValidator:
    """
    Accumulates extracted document data and runs cross-validation rules.

    Call .add(doc_type, extracted_dict) for each uploaded document,
    then call .validate() to get a CrossValidationResult.
    """

    # Minimum name similarity score to consider names matching
    NAME_MATCH_THRESHOLD = 0.6

    def __init__(self):
        self._docs: dict[str, dict] = {}

    def add(self, doc_type: str, extracted: dict):
        """Register extracted data for a document type."""
        self._docs[doc_type.lower()] = extracted or {}

    def has(self, doc_type: str) -> bool:
        return doc_type.lower() in self._docs

    # ── Public entry point ────────────────────────────────────────
    def validate(self) -> CrossValidationResult:
        errors:   list[str] = []
        warnings: list[str] = []
        checks:   list[dict] = []

        self._check_document_types(errors, warnings, checks)
        self._check_name_consistency(errors, warnings, checks)
        self._check_dob_consistency(errors, warnings, checks)
        self._check_photo_quality(errors, warnings, checks)
        self._check_confidence_levels(errors, warnings, checks)

        return CrossValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            cross_checks=checks,
        )

    # ── Individual checks ─────────────────────────────────────────

    def _check_document_types(self, errors, warnings, checks):
        """Each document must be the correct type."""
        type_map = {
            "aadhaar":         "aadhaar",
            "driving_license": "driving_license",
            "photograph":      None,  # no document_type field for photos
        }
        for doc_key, expected_type in type_map.items():
            if not self.has(doc_key) or expected_type is None:
                continue
            doc = self._docs[doc_key]
            detected = (doc.get("document_type") or "").lower()
            passed = detected == expected_type
            checks.append({
                "check":    f"document_type:{doc_key}",
                "passed":   passed,
                "expected": expected_type,
                "detected": detected,
            })
            if not passed:
                errors.append(
                    f"Uploaded file for '{doc_key}' appears to be '{detected or 'unknown'}', "
                    f"not a {expected_type.replace('_', ' ')}. Please re-upload the correct document."
                )

    def _check_name_consistency(self, errors, warnings, checks):
        """Name on Aadhaar must match name on Driving License."""
        if not (self.has("aadhaar") and self.has("driving_license")):
            return

        aadhaar_name = self._docs["aadhaar"].get("name") or ""
        dl_name      = self._docs["driving_license"].get("name") or ""

        if not aadhaar_name or not dl_name:
            warnings.append(
                "Could not verify name consistency — name missing from one or more documents."
            )
            checks.append({"check": "name_consistency", "passed": None, "reason": "missing_data"})
            return

        score  = _name_similarity(aadhaar_name, dl_name)
        passed = score >= self.NAME_MATCH_THRESHOLD

        checks.append({
            "check":         "name_consistency",
            "passed":        passed,
            "aadhaar_name":  aadhaar_name,
            "dl_name":       dl_name,
            "similarity":    round(score, 2),
            "threshold":     self.NAME_MATCH_THRESHOLD,
        })

        if not passed:
            errors.append(
                f"Name mismatch: Aadhaar shows '{aadhaar_name}' but Driving License shows '{dl_name}'. "
                f"All documents must have the same name. Please re-upload matching documents."
            )
        elif score < 0.85:
            # Names match but not perfectly — flag for manual review
            warnings.append(
                f"Name is similar but not identical: Aadhaar '{aadhaar_name}' vs DL '{dl_name}'. "
                f"This may be flagged for manual review."
            )

    def _check_dob_consistency(self, errors, warnings, checks):
        """DOB on Aadhaar must match DOB on Driving License."""
        if not (self.has("aadhaar") and self.has("driving_license")):
            return

        aadhaar_dob = _normalise_dob(self._docs["aadhaar"].get("dob"))
        dl_dob      = _normalise_dob(self._docs["driving_license"].get("dob"))

        if not aadhaar_dob or not dl_dob:
            warnings.append(
                "Could not verify date of birth consistency — DOB missing from one or more documents."
            )
            checks.append({"check": "dob_consistency", "passed": None, "reason": "missing_data"})
            return

        passed = aadhaar_dob == dl_dob
        checks.append({
            "check":       "dob_consistency",
            "passed":      passed,
            "aadhaar_dob": aadhaar_dob,
            "dl_dob":      dl_dob,
        })

        if not passed:
            errors.append(
                f"Date of birth mismatch: Aadhaar shows '{aadhaar_dob}' but Driving License shows '{dl_dob}'. "
                f"DOB must match across all documents."
            )

    def _check_photo_quality(self, errors, warnings, checks):
        """Photograph must have exactly one face, centered, plain background."""
        if not self.has("photograph"):
            return

        photo = self._docs["photograph"]
        has_face        = photo.get("has_face", False)
        face_count      = photo.get("face_count", 0)
        face_centered   = photo.get("face_centered", False)
        plain_bg        = photo.get("plain_background", False)
        has_sunglasses  = photo.get("has_sunglasses", False)
        eyes_visible    = photo.get("eyes_visible", True)

        photo_errors = []
        if not has_face:
            photo_errors.append("No face detected in photograph")
        if face_count > 1:
            photo_errors.append(f"Multiple faces detected ({face_count}) — solo photo required")
        if not face_centered:
            photo_errors.append("Face not centered in photograph")
        if not plain_bg:
            photo_errors.append("Photograph background must be plain white")
        if has_sunglasses:
            photo_errors.append("Remove sunglasses from photograph")
        if not eyes_visible:
            photo_errors.append("Eyes must be clearly visible in photograph")

        passed = len(photo_errors) == 0
        checks.append({
            "check":  "photograph_quality",
            "passed": passed,
            "issues": photo_errors,
        })
        errors.extend(photo_errors)

    def _check_confidence_levels(self, errors, warnings, checks):
        """Flag any document with low extraction confidence for manual review."""
        for doc_key, doc in self._docs.items():
            confidence = (doc.get("confidence") or "").lower()
            if confidence == "low":
                warnings.append(
                    f"Low confidence reading on {doc_key.replace('_', ' ')} — "
                    f"please re-upload a clearer image for accurate processing."
                )
                checks.append({
                    "check":      f"confidence:{doc_key}",
                    "passed":     False,
                    "confidence": confidence,
                })
            elif confidence == "medium":
                warnings.append(
                    f"Medium confidence on {doc_key.replace('_', ' ')} — "
                    f"document was read but may have minor inaccuracies."
                )
                checks.append({
                    "check":      f"confidence:{doc_key}",
                    "passed":     True,
                    "confidence": confidence,
                })


# ── Session-level accumulator (used by app.py) ────────────────────────────────

class SessionDocumentStore:
    """
    Stores extracted document data per session so cross-validation
    can be triggered once all documents are uploaded.

    Usage in app.py:
        store = SessionDocumentStore()
        store.save(session_id, "aadhaar", extracted_dict)
        ...
        if store.all_uploaded(session_id, ["aadhaar", "driving_license", "photograph"]):
            result = store.cross_validate(session_id)
    """

    def __init__(self):
        self._sessions: dict[str, dict[str, dict]] = {}

    def save(self, session_id: str, doc_type: str, extracted: dict):
        self._sessions.setdefault(session_id, {})[doc_type.lower()] = extracted

    def get(self, session_id: str, doc_type: str) -> Optional[dict]:
        return self._sessions.get(session_id, {}).get(doc_type.lower())

    def all_uploaded(self, session_id: str, required: list[str]) -> bool:
        uploaded = set(self._sessions.get(session_id, {}).keys())
        return all(r.lower() in uploaded for r in required)

    def cross_validate(self, session_id: str) -> CrossValidationResult:
        cv = CrossValidator()
        for doc_type, extracted in self._sessions.get(session_id, {}).items():
            cv.add(doc_type, extracted)
        return cv.validate()

    def clear(self, session_id: str):
        self._sessions.pop(session_id, None)
