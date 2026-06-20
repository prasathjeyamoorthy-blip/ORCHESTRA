"""
populate_config.py
==================
Reads Aadhaar extraction output from the documentuploadagent
and populates pan_config.json with the extracted values.

Usage:
    # From a saved extraction JSON file:
    python populate_config.py --from-file aadhaar_extraction.json

    # From the live document upload agent API:
    python populate_config.py --from-api http://localhost:5001 --aadhaar path/to/aadhaar.jpg

    # Dry run (print result, don't write):
    python populate_config.py --from-file aadhaar_extraction.json --dry-run
"""

import argparse
import json
import os
import sys
import requests


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "pan_config.json")

# Fields that are NOT auto-populated from Aadhaar — user must fill these manually
MANUAL_FIELDS = {
    "email",
    "mobile",
    "tel_std_code",
    "tel_number",
    "source_of_income",
    "residential_status",
    "passport_number",
    "taxpayer_id",
    "representative_assessee",
    "ao_area_code",
    "ao_type",
    "ao_range_code",
    "ao_number",
    "verification_place",
    "document_upload_path",
    "title",
    "application_type",
    "category",
    "submission_mode",
    "paperless",
    "aadhaar_photo_consent",
    "name_on_card",
}


def gender_to_code(gender: str | None) -> str:
    """Convert 'Male'/'Female'/'Transgender' → 'M'/'F'/'T'."""
    if not gender:
        return ""
    g = gender.strip().lower()
    return {"male": "M", "female": "F", "transgender": "T"}.get(g, "")


def state_to_upper(state: str | None) -> str:
    return (state or "").strip().upper()


def aadhaar_digits_only(aadhaar: str | None) -> str:
    """Strip spaces/dashes from Aadhaar number."""
    if not aadhaar:
        return ""
    return "".join(c for c in aadhaar if c.isdigit())


def build_declaration_name(first: str, middle: str, last: str) -> str:
    parts = [p.strip().upper() for p in [first, middle, last] if p and p.strip()]
    return " ".join(parts)


def map_aadhaar_to_config(extracted: dict) -> dict:
    """
    Map AadhaarData fields → pan_config.json applicant fields.

    extracted: the 'extracted' dict from the document upload agent response,
               which matches the AadhaarData pydantic model fields.
    """
    first  = extracted.get("first_name") or ""
    middle = extracted.get("middle_name") or ""
    last   = extracted.get("last_name") or ""

    f_first  = extracted.get("father_first_name") or ""
    f_middle = extracted.get("father_middle_name") or ""
    f_last   = extracted.get("father_last_name") or ""

    # Mother's name is not on Aadhaar — leave as-is in config
    city = (
        extracted.get("area_locality_city")
        or extracted.get("district")
        or ""
    ).strip()

    ao_city = (
        extracted.get("district")
        or extracted.get("area_locality_city")
        or ""
    ).strip().upper()

    return {
        # ── Name ──────────────────────────────────────────────
        "first_name":  first.upper(),
        "middle_name": middle.upper(),
        "last_name":   last.upper(),

        # ── Personal ──────────────────────────────────────────
        "dob":            extracted.get("dob") or "",
        "gender":         gender_to_code(extracted.get("gender")),
        "aadhaar_number": aadhaar_digits_only(extracted.get("aadhaar_number")),

        # ── Father ────────────────────────────────────────────
        "father_first":  f_first.upper(),
        "father_middle": f_middle.upper(),
        "father_last":   f_last.upper(),

        # ── Address ───────────────────────────────────────────
        "address_flat":     (extracted.get("flat_door_building") or "").strip(),
        "address_building": "",   # Aadhaar doesn't split building separately
        "address_street":   (extracted.get("road_street_block") or "").strip(),
        "address_area":     (extracted.get("post_office") or city).strip(),
        "address_city":     city,
        "address_state":    state_to_upper(extracted.get("state")),
        "address_pin":      (extracted.get("pincode") or "").strip(),
        "address_country":  "INDIA",

        # ── AO Code hints (state/city only — codes need manual lookup) ──
        "ao_state": state_to_upper(extracted.get("state")),
        "ao_city":  ao_city,

        # ── Declaration ───────────────────────────────────────
        "declaration_name": build_declaration_name(first, middle, last),

        # ── Resume section (DOB + email from Aadhaar if available) ──
        "_resume_dob":   extracted.get("dob") or "",
        "_resume_email": extracted.get("email_id") or "",
    }


def apply_to_config(config: dict, mapped: dict) -> dict:
    """Merge mapped values into config, skipping manual fields and null values."""
    applicant = config.setdefault("applicant", {})
    resume    = config.setdefault("resume", {})

    changed = []

    for key, value in mapped.items():
        if not value:
            continue  # skip nulls / empty strings

        if key == "_resume_dob":
            if not resume.get("dob"):
                resume["dob"] = value
                changed.append(f"resume.dob = {value}")
            continue

        if key == "_resume_email":
            if not resume.get("email"):
                resume["email"] = value
                changed.append(f"resume.email = {value}")
            continue

        if key in MANUAL_FIELDS:
            continue  # never overwrite manual fields

        old = applicant.get(key)
        applicant[key] = value
        if old != value:
            changed.append(f"applicant.{key}: {old!r} → {value!r}")

    return config, changed


def fetch_from_api(base_url: str, aadhaar_path: str) -> dict:
    """Upload Aadhaar to the document agent and return the extracted dict."""
    url = base_url.rstrip("/") + "/api/upload"
    with open(aadhaar_path, "rb") as f:
        filename = os.path.basename(aadhaar_path)
        resp = requests.post(
            url,
            data={"session_id": "populate_config", "doc_type": "aadhaar"},
            files={"file": (filename, f)},
            timeout=120,
        )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "error":
        raise RuntimeError(f"Agent returned error: {data.get('error')}")
    return data.get("extracted", {})


def main():
    parser = argparse.ArgumentParser(description="Populate pan_config.json from Aadhaar extraction")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-file", metavar="JSON_FILE",
                     help="Path to saved extraction JSON (the 'extracted' object from /api/upload response)")
    src.add_argument("--from-api", metavar="BASE_URL",
                     help="Base URL of document upload agent, e.g. http://localhost:5001")
    parser.add_argument("--aadhaar", metavar="IMAGE_PATH",
                        help="Aadhaar image path (required with --from-api)")
    parser.add_argument("--config", default=CONFIG_PATH,
                        help=f"Path to pan_config.json (default: {CONFIG_PATH})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print changes without writing to file")
    args = parser.parse_args()

    # ── Load extraction data ──────────────────────────────────
    if args.from_file:
        with open(args.from_file, encoding="utf-8") as f:
            raw = json.load(f)
        # Support both the full API response and just the 'extracted' sub-object
        extracted = raw.get("extracted", raw)
    else:
        if not args.aadhaar:
            parser.error("--aadhaar is required when using --from-api")
        print(f"Uploading {args.aadhaar} to {args.from_api} ...")
        extracted = fetch_from_api(args.from_api, args.aadhaar)

    print(f"\nExtracted fields from Aadhaar:")
    for k, v in extracted.items():
        if v:
            print(f"  {k}: {v}")

    # ── Load config ───────────────────────────────────────────
    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    # ── Map + apply ───────────────────────────────────────────
    mapped = map_aadhaar_to_config(extracted)
    config, changes = apply_to_config(config, mapped)

    print(f"\nChanges to apply ({len(changes)}):")
    for c in changes:
        print(f"  ✓ {c}")

    if not changes:
        print("  (no changes — config already up to date)")
        return

    if args.dry_run:
        print("\n[dry-run] Config NOT written. Final applicant section would be:")
        print(json.dumps(config["applicant"], indent=4, ensure_ascii=False))
        return

    # ── Write ─────────────────────────────────────────────────
    with open(args.config, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print(f"\n✅ pan_config.json updated at {args.config}")
    print("\nFields still requiring manual input:")
    for field in sorted(MANUAL_FIELDS):
        val = config["applicant"].get(field)
        if not val and val != False:
            print(f"  ⚠️  applicant.{field}")


if __name__ == "__main__":
    main()
