"""
pan_config_builder.py
=====================
Builds pan_config.json from data collected by pan-rag:
  1. FlowManager state  — answers from the chat flow (confirmed details)
  2. Redis extraction cache — Aadhaar fields extracted from the uploaded document
  3. Supabase user_profiles — persistent profile data

Usage (from the Orchestra folder):
    python pan_config_builder.py --session-id <session_id> --user-id <user_id>
    python pan_config_builder.py --session-id <sid> --user-id <uid> --output my_config.json

The script writes/updates pan_config.json with every field it can derive.
Fields it cannot fill (mobile, title, AO codes, etc.) are left as-is
so you can fill them manually or in a later step.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ── path setup so we can import pan-rag modules ──────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "pan-rag"))
from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / "pan-rag" / ".env")

DEFAULT_CONFIG = Path(__file__).parent / "pan_config.json"


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _split_name(full: str) -> tuple[str, str, str]:
    """
    Split name following NSDL form rules:

    1 word      "Lohit"    → first="LOHIT",  middle="LOHIT",  last="LOHIT"
    2 words     "G Lohit"  → first="G",       middle="LOHIT",  last="G"
                             (initial/first word repeated as last name)
    3+ words    "A B C"    → first="A", middle="B", last="C"
    """
    if not full:
        return "", "", ""
    parts = [p.upper() for p in full.strip().split()]
    if len(parts) == 1:
        return parts[0], parts[0], parts[0]
    if len(parts) == 2:
        return parts[0], parts[1], parts[0]
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def _gender_code(raw: str) -> str:
    """'Male'/'M' → 'M', 'Female'/'F' → 'F', 'Transgender'/'T' → 'T'"""
    if not raw:
        return ""
    g = raw.strip().lower()
    return {"male": "M", "m": "M", "female": "F", "f": "F",
            "transgender": "T", "t": "T"}.get(g, raw.upper()[:1])


def _aadhaar_digits(raw: str) -> str:
    """Remove spaces/dashes from Aadhaar number."""
    return re.sub(r"[^0-9]", "", raw or "")


def _source_of_income_map(raw: str) -> str:
    """
    Map pan-rag source_of_income choices to Orchestra choices.
    pan-rag: 'Salary | சம்பளம்'  →  Orchestra: 'Salary'
    """
    if not raw:
        return ""
    # Strip Tamil part if present (format "English | Tamil")
    english = raw.split("|")[0].strip()
    _map = {
        "Salary": "Salary",
        "Income from Business / Profession": "Income from Business / Profession",
        "Income from House property": "Income from House property",
        "Income from Other sources": "Income from Other sources",
        "Capital Gains": "Capital Gains",
        "No income": "No income",
    }
    # Match ignoring case for robustness
    for key, val in _map.items():
        if english.lower() == key.lower():
            return val
    return english


def _submission_mode_to_paperless(raw: str) -> bool:
    """
    'Aadhaar-based Online (eKYC)' → True (paperless)
    Others → False (physical/upload)
    """
    return "ekyc" in (raw or "").lower() or "aadhaar" in (raw or "").lower()


def _address_type(raw: str) -> str:
    """
    'Residence | வீடு' → 'Residence'
    'Office | அலுவலகம்' → 'Office'
    """
    if not raw:
        return ""
    english = raw.split("|")[0].strip()
    _map = {
        "Residence": "Residence",
        "Office": "Office",
        "Representative Assessee (RA)": "Representative Assessee (RA)",
    }
    for key, val in _map.items():
        if english.lower() == key.lower():
            return val
    return english


def _residential_status(raw: str) -> str:
    """Normalize residential status value."""
    if not raw:
        return ""
    english = raw.split("|")[0].strip()
    _map = {
        "Resident": "Resident",
        "Non-resident": "Non-resident",
        "Resident but not ordinarily resident": "Resident but not ordinarily resident",
    }
    for key, val in _map.items():
        if english.lower() == key.lower():
            return val
    return english


def _category_from_applicant_type(raw: str) -> str:
    """
    pan-rag applicant_type → Orchestra category
    'Indian Citizen / Individual' or 'indian_citizen' → 'Individual'
    'Indian Company / HUF / Entity' or 'indian_entity' → 'Company'
    'Foreign Individual / Entity' or 'foreign' → 'Individual' (for 49AA)
    """
    r = (raw or "").lower()
    if "company" in r or "huf" in r or "entity" in r or "indian_entity" in r:
        return "Company"
    return "Individual"


def _yn_to_bool(val) -> bool:
    """'Yes'/True/1 → True, everything else → False"""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("yes", "true", "1", "y")
    return bool(val)


# ════════════════════════════════════════════════════════════════════════════
#  DATA LOADERS
# ════════════════════════════════════════════════════════════════════════════

def load_flow_state(session_id: str, user_id: str) -> dict:
    """Load FlowManager state from disk."""
    try:
        from agent.flow_manager import FlowManager
        fm = FlowManager(session_id, user_id)
        return fm.state
    except Exception as e:
        print(f"[builder] Could not load FlowManager state: {e}")
        return {}


def load_aadhaar_extraction(session_id: str) -> dict:
    """Load Aadhaar extraction result from Redis cache."""
    try:
        from memory.memory_manager import MemoryManager
        mm = MemoryManager()
        raw = mm._get(f"extraction:{session_id}:aadhaar")
        if raw:
            return json.loads(raw)
    except Exception as e:
        print(f"[builder] Could not load Aadhaar extraction from Redis: {e}")
    return {}


def load_user_profile(user_id: str) -> dict:
    """Load user profile from Supabase."""
    try:
        from agent.user_profile import get_user_profile
        profile = get_user_profile(user_id)
        return profile or {}
    except Exception as e:
        print(f"[builder] Could not load Supabase profile: {e}")
    return {}


def load_document_paths(session_id: str) -> dict:
    """
    Find uploaded document files stored under pan-rag/storage/uploads/{session_id}/.
    Returns a dict: { 'aadhaar': '/path/to/file', 'photograph': ..., 'signature': ... }
    """
    upload_dir = _REPO_ROOT / "pan-rag" / "storage" / "uploads" / session_id
    paths = {}
    if not upload_dir.exists():
        return paths

    # Each file is named {doc_type}_{timestamp}.{ext} (set during upload)
    _TYPE_MAP = {
        "aadhaar":        "aadhaar_pdf",
        "photograph":     "photo_file",
        "signature":      "signature_file",
        "driving_license": "driving_license_file",
    }
    for file in sorted(upload_dir.iterdir()):
        fname = file.name.lower()
        for doc_type, key in _TYPE_MAP.items():
            if fname.startswith(doc_type) and key not in paths:
                paths[key] = str(file.resolve())
                break

    return paths


# ════════════════════════════════════════════════════════════════════════════
#  CORE MAPPER
# ════════════════════════════════════════════════════════════════════════════

def build_config(session_id: str, user_id: str) -> dict:
    """
    Assemble pan_config.json applicant + resume sections from all available sources.
    Priority: FlowManager (freshest) > Redis Aadhaar extraction > Supabase profile
    """
    flow   = load_flow_state(session_id, user_id)
    aadhaar = load_aadhaar_extraction(session_id)
    profile = load_user_profile(user_id)
    doc_paths = load_document_paths(session_id)

    print(f"\n[builder] Sources loaded:")
    print(f"  FlowManager fields  : {[k for k,v in flow.items() if v and not k.startswith('_')]}")
    print(f"  Aadhaar extraction  : {list(aadhaar.keys())}")
    print(f"  Supabase profile    : {list(profile.keys())}")
    print(f"  Document paths      : {doc_paths}")

    # ── Helper: pick first non-empty value from ordered sources ──
    def _pick(*values):
        for v in values:
            if v is not None and str(v).strip():
                return v
        return ""

    # ══════════════════════════════════════════════════════════════
    #  SECTION 1 — Name (from Aadhaar extraction first, then flow)
    #  Aadhaar extraction returns split names; flow stores as single string
    # ══════════════════════════════════════════════════════════════
    # Aadhaar-extracted split names (most reliable)
    first_a  = (aadhaar.get("first_name")  or "").strip().upper()
    middle_a = (aadhaar.get("middle_name") or "").strip().upper()
    last_a   = (aadhaar.get("last_name")   or "").strip().upper()

    # Flow / profile full_name (single string — split as fallback)
    flow_full = _pick(flow.get("full_name"), profile.get("full_name"))
    first_f, middle_f, last_f = _split_name(flow_full)

    first  = _pick(first_a,  first_f)
    middle = _pick(middle_a, middle_f)
    last   = _pick(last_a,   last_f)

    # ── Declaration name = full name in UPPER ──────────────────
    decl_parts = [p for p in [first, middle, last] if p]
    declaration_name = " ".join(decl_parts)

    # ══════════════════════════════════════════════════════════════
    #  SECTION 2 — Personal (DOB, gender, Aadhaar)
    # ══════════════════════════════════════════════════════════════
    dob    = _pick(aadhaar.get("dob"),           profile.get("dob"))
    gender = _gender_code(_pick(aadhaar.get("gender"), profile.get("gender")))

    raw_aadhaar = _pick(aadhaar.get("aadhaar_number"), flow.get("aadhaar_number"))
    aadhaar_digits = _aadhaar_digits(raw_aadhaar)
    aadhaar_last_4 = aadhaar_digits[-4:] if len(aadhaar_digits) >= 4 else ""
    aadhaar_first_8 = aadhaar_digits[:8] if len(aadhaar_digits) >= 8 else ""
    name_on_aadhaar = declaration_name  # name as it appears on Aadhaar

    # ══════════════════════════════════════════════════════════════
    #  SECTION 3 — Father's name (from Aadhaar)
    # ══════════════════════════════════════════════════════════════
    # pan-rag calls it grandfather_name — on the PAN form this is
    # "Father's / Grandfather's name" for patrilineal identification.
    # Aadhaar extraction provides actual father name fields.
    father_first  = (aadhaar.get("father_first_name")  or "").strip().upper()
    father_middle = (aadhaar.get("father_middle_name") or "").strip().upper()
    father_last   = (aadhaar.get("father_last_name")   or "").strip().upper()

    # Fallback: pan-rag's grandfather_name is the paternal ancestor field
    if not father_first and not father_last:
        gf_raw = _pick(flow.get("grandfather_name"), profile.get("grandfather_name"))
        if gf_raw:
            father_first, father_middle, father_last = _split_name(gf_raw)

    # ══════════════════════════════════════════════════════════════
    #  SECTION 4 — Mother's name (from flow / profile)
    # ══════════════════════════════════════════════════════════════
    mother_raw = _pick(flow.get("mother_name"), profile.get("mother_name"))
    mother_first, mother_middle, mother_last = _split_name(mother_raw)

    # ══════════════════════════════════════════════════════════════
    #  SECTION 5 — Contact
    # ══════════════════════════════════════════════════════════════
    email  = _pick(flow.get("email"),  profile.get("email"))
    mobile = _pick(
        flow.get("mobile"),
        profile.get("mobile"),
        profile.get("phone"),       # phone column in user_profiles
    )

    # title stored in pan_preferences JSONB
    pan_prefs_profile = profile.get("pan_preferences") or {}
    if isinstance(pan_prefs_profile, str):
        import json as _j
        try:
            pan_prefs_profile = _j.loads(pan_prefs_profile)
        except Exception:
            pan_prefs_profile = {}

    title = _pick(
        flow.get("title"),
        pan_prefs_profile.get("title"),
    )

    # ══════════════════════════════════════════════════════════════
    #  SECTION 6 — Address (from Aadhaar extraction)
    # ══════════════════════════════════════════════════════════════
    address_flat     = (aadhaar.get("flat_door_building") or "").strip()
    address_building = ""   # Aadhaar doesn't split building separately
    address_street   = (aadhaar.get("road_street_block") or "").strip()
    address_area     = (aadhaar.get("post_office")
                        or aadhaar.get("area_locality_city") or "").strip()
    address_city     = (aadhaar.get("area_locality_city")
                        or aadhaar.get("district") or "").strip()
    address_state    = (aadhaar.get("state") or "").strip().upper()
    address_pin      = (aadhaar.get("pincode") or "").strip()

    # Verification place = city from Aadhaar address (best guess)
    verification_place = address_city

    # ══════════════════════════════════════════════════════════════
    #  SECTION 7 — Application preferences (from flow)
    # ══════════════════════════════════════════════════════════════
    source_of_income     = _source_of_income_map(_pick(flow.get("source_of_income"),
                                                       profile.get("source_of_income")))
    address_for_comm     = _address_type(_pick(flow.get("address_for_comm"),
                                               profile.get("address_for_comm")))
    residential_status   = _residential_status(_pick(flow.get("residential_status"),
                                                     profile.get("residential_status")))
    aadhaar_photo_consent = _yn_to_bool(_pick(str(flow.get("aadhaar_photo", "")),
                                              str(profile.get("aadhaar_photo", ""))))

    raw_sub_mode  = _pick(flow.get("submission_mode"), profile.get("submission_mode"))
    paperless     = _submission_mode_to_paperless(raw_sub_mode)

    rep_assessee  = _yn_to_bool(_pick(str(flow.get("rep_assessee", "")),
                                      str(profile.get("rep_assessee", ""))))

    category      = _category_from_applicant_type(
                        _pick(flow.get("applicant_type"), profile.get("applicant_type")))

    # ══════════════════════════════════════════════════════════════
    #  SECTION 8 — Document file paths (set from upload directory)
    # ══════════════════════════════════════════════════════════════
    photo_file      = doc_paths.get("photo_file",      "")
    signature_file  = doc_paths.get("signature_file",  "")
    aadhaar_pdf     = doc_paths.get("aadhaar_pdf",     "")

    # ══════════════════════════════════════════════════════════════
    #  SECTION 9 — Resume (token, email, dob for session resume)
    # ══════════════════════════════════════════════════════════════
    # These are populated if the user is resuming an existing application.
    # Leave blank for a fresh application.
    resume_token = flow.get("_resume_token", "")
    resume_email = email
    resume_dob   = dob

    # ══════════════════════════════════════════════════════════════
    #  ASSEMBLE final config dict
    # ══════════════════════════════════════════════════════════════
    config = {
        "resume": {
            "token_number": resume_token,
            "email":        resume_email,
            "dob":          resume_dob,
        },
        "applicant": {
            # ── Form type ──────────────────────────────────────────
            "application_type": "49A",        # Indian citizen — always 49A
            "category":         category,      # Individual / Company
            "submission_mode":  raw_sub_mode,  # keep original label for reference
            "paperless":        paperless,     # True = Aadhaar eKYC

            # ── Title ─────────────────────────────────────────────
            "title": title,

            # ── Name ──────────────────────────────────────────────
            "last_name":   last,
            "first_name":  first,
            "middle_name": middle,

            # ── Personal ──────────────────────────────────────────
            "dob":    dob,
            "email":  email,
            "mobile": mobile,   # not yet collected

            # ── Gender + Aadhaar ──────────────────────────────────
            "gender":              gender,
            "aadhaar_number":      aadhaar_digits,
            "aadhaar_first_8":     aadhaar_first_8,
            "aadhaar_last_4":      aadhaar_last_4,
            "name_on_aadhaar":     name_on_aadhaar,
            "aadhaar_photo_consent": aadhaar_photo_consent,

            # ── Father / grandfather ──────────────────────────────
            "father_last":   father_last,
            "father_first":  father_first,
            "father_middle": father_middle,

            # ── Mother ────────────────────────────────────────────
            "mother_last":   mother_last,
            "mother_first":  mother_first,
            "mother_middle": mother_middle,

            # ── Name on PAN card ──────────────────────────────────
            "name_on_card": "father",   # default — can be overridden

            # ── Address ───────────────────────────────────────────
            "address_flat":     address_flat,
            "address_building": address_building,
            "address_street":   address_street,
            "address_area":     address_area,
            "address_city":     address_city,
            "address_state":    address_state,
            "address_pin":      address_pin,
            "address_country":  "INDIA",

            # ── Application preferences ───────────────────────────
            "source_of_income":  source_of_income,
            "address_for_comm":  address_for_comm,
            "residential_status": residential_status,
            "representative_assessee": rep_assessee,

            # ── AO Codes (filled by Aadhaar eKYC auto-fill on portal) ──
            "ao_area_code":  "",
            "ao_type":       "",
            "ao_range_code": "",
            "ao_number":     "",
            "ao_state":      address_state,
            "ao_city":       address_city.upper(),

            # ── Proofs (paperless eKYC = Aadhaar for all) ─────────
            "proof_identity": "Aadhaar Card",
            "proof_address":  "Aadhaar Card",
            "proof_dob":      "Aadhaar Card",

            # ── Declaration ───────────────────────────────────────
            "declaration_name":    declaration_name,
            "verification_place":  verification_place,

            # ── Document file paths ───────────────────────────────
            "photo_file":     photo_file,
            "signature_file": signature_file,
            "aadhaar_pdf":    aadhaar_pdf,

            # ── Not yet collected (leave blank) ───────────────────
            "tel_std_code":   "",
            "tel_number":     "",
            "passport_number": "",
            "taxpayer_id":    "",
        },
        "server": {
            "otp_port": 5055
        }
    }

    return config


# ════════════════════════════════════════════════════════════════════════════
#  WRITE + REPORT
# ════════════════════════════════════════════════════════════════════════════

def write_config(config: dict, output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"\n✅ pan_config.json written to: {output_path}")


def report(config: dict) -> None:
    """Print a human-readable summary of what was mapped and what's missing."""
    a = config["applicant"]

    MAPPED    = []
    MISSING   = []
    MANUAL    = []   # collected but might need verification

    def _chk(label, value, source=""):
        note = f"  ← {source}" if source else ""
        if value:
            MAPPED.append(f"  ✅  {label}: {value}{note}")
        else:
            MISSING.append(f"  ❌  {label}")

    _chk("first_name",          a["first_name"],          "Aadhaar / flow")
    _chk("middle_name",         a["middle_name"],          "Aadhaar / flow")
    _chk("last_name",           a["last_name"],            "Aadhaar / flow")
    _chk("dob",                 a["dob"],                  "Aadhaar")
    _chk("gender",              a["gender"],               "Aadhaar")
    _chk("aadhaar_number",      a["aadhaar_number"],       "Aadhaar scan")
    _chk("email",               a["email"],                "flow")
    _chk("father_first",        a["father_first"],         "Aadhaar / flow (grandfather_name)")
    _chk("father_last",         a["father_last"],          "Aadhaar / flow (grandfather_name)")
    _chk("mother_first",        a["mother_first"],         "flow")
    _chk("mother_last",         a["mother_last"],          "flow")
    _chk("address_flat",        a["address_flat"],         "Aadhaar")
    _chk("address_street",      a["address_street"],       "Aadhaar")
    _chk("address_city",        a["address_city"],         "Aadhaar")
    _chk("address_state",       a["address_state"],        "Aadhaar")
    _chk("address_pin",         a["address_pin"],          "Aadhaar")
    _chk("source_of_income",    a["source_of_income"],     "flow")
    _chk("address_for_comm",    a["address_for_comm"],     "flow")
    _chk("residential_status",  a["residential_status"],   "flow")
    _chk("aadhaar_photo_consent", str(a["aadhaar_photo_consent"]), "flow")
    _chk("paperless",           str(a["paperless"]),       "flow (submission_mode)")
    _chk("photo_file",          a["photo_file"],           "uploaded document")
    _chk("signature_file",      a["signature_file"],       "uploaded document")
    _chk("aadhaar_pdf",         a["aadhaar_pdf"],          "uploaded document")

    MANUAL.append(f"  ⚠️   title           — not collected yet (Mr/Mrs/Ms)")
    MANUAL.append(f"  ⚠️   mobile          — not collected yet")
    if not a["father_first"]:
        MANUAL.append(f"  ⚠️   father_name     — not in Aadhaar extraction; provide grandfather_name in chat")
    MANUAL.append(f"  ⚠️   ao_area_code    — auto-filled by Aadhaar eKYC on portal (leave blank)")
    MANUAL.append(f"  ⚠️   verification_place — derived from address city: {a['ao_city']}")

    print("\n" + "═" * 60)
    print("  MAPPED  (will be pre-filled in pan_config.json)")
    print("═" * 60)
    print("\n".join(MAPPED) or "  (none)")

    if MISSING:
        print("\n" + "═" * 60)
        print("  MISSING  (still blank — needs manual input)")
        print("═" * 60)
        print("\n".join(MISSING))

    print("\n" + "═" * 60)
    print("  MANUAL / REVIEW")
    print("═" * 60)
    print("\n".join(MANUAL))
    print()


# ════════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Build pan_config.json from pan-rag collected data"
    )
    parser.add_argument("--session-id", required=True, help="pan-rag session ID")
    parser.add_argument("--user-id",    required=True, help="Supabase auth user ID")
    parser.add_argument("--output", default=str(DEFAULT_CONFIG),
                        help=f"Output path (default: {DEFAULT_CONFIG})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print config without writing to file")
    args = parser.parse_args()

    print(f"\n[builder] Building pan_config.json")
    print(f"          session_id : {args.session_id}")
    print(f"          user_id    : {args.user_id}")

    config = build_config(args.session_id, args.user_id)

    report(config)

    if args.dry_run:
        print("\n[dry-run] Final config:")
        print(json.dumps(config, indent=4, ensure_ascii=False))
        return

    write_config(config, Path(args.output))


if __name__ == "__main__":
    main()
