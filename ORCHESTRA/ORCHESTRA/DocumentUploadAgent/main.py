import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import extractor, validator
    

def _normalise_dob(dob_str: str) -> str:
    """Normalise any DOB format the VLM returns to DD/MM/YYYY.
    
    Handles: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD-Mon-YYYY, DD Mon YYYY,
    bare 4-digit year (returned as-is with a warning).
    """
    if not dob_str:
        return ""
    s = str(dob_str).strip()
    # Bare 4-digit year — can't make a full date from it
    if re.fullmatch(r'\d{4}', s):
        return s  # return as-is; the portal will reject it — handled in rescert.py
    fmts = (
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%d-%b-%Y", "%d/%b/%Y", "%d %b %Y",
        "%d-%B-%Y", "%d/%B/%Y", "%d %B %Y",
        "%d/%m/%y", "%d-%m-%y",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return s  # return original if nothing matched


def find_certificate(results: list, cert_type: str) -> Optional[dict]:
    """Find certificate by type name.

    The VLM classifier is not perfect and often returns a similar
    certificate type (for example a Ration Card going through the
    "Voter ID" branch).  This helper now contains a small set of
    aliases that reflect those common misclassifications so that
    callers don’t end up with an empty dictionary when the response
    is still the desired document.

    - For PAN, also accepts Voter ID as alternative (legacy behaviour).
    - Ration Card may be mislabelled as Voter ID.
    - Address Proof is sometimes classified as a Residence or Income
      certificate by the VLM model.
    """
    # map certificate types to a list of acceptable alternate labels
    aliases = {
        "ration card": ["voter id", "ration", "ration card", "family card"],
        "address proof": ["residence certificate", "income certificate"],
        "caste certificate": ["income certificate", "residence certificate", "community certificate"],
    }

    for item in results:
        item_type = item.get("certificate_type", "").lower()
        cert_lower = cert_type.lower()

        # Exact match or one of the known aliases
        if item_type == cert_lower or item_type in aliases.get(cert_lower, []):
            return item

        # PAN can also be Voter ID (legacy behaviour)
        if cert_lower == "pan" and item_type == "voter id":
            return item

    return None


def process_documents(
    aadhaar_pdf: str = None,
    ration_pdf: str = None,
    address_pdf: str = None,
    caste_pdf: str = None,
    pre_aadhaar: list = None,
    pre_ration: list = None,
    pre_address: list = None,
    pre_caste: list = None
) -> dict:
    # Debug: Print file paths & pre-extracted availability
    print(f"DEBUG: aadhaar_pdf = {aadhaar_pdf} (pre-extracted: {bool(pre_aadhaar)})")
    print(f"DEBUG: ration_pdf = {ration_pdf} (pre-extracted: {bool(pre_ration)})")
    print(f"DEBUG: address_pdf = {address_pdf} (pre-extracted: {bool(pre_address)})")
    print(f"DEBUG: caste_pdf = {caste_pdf} (pre-extracted: {bool(pre_caste)})")
    
    def _extract_safe(path):
        if not path:
            return []
        try:
            return extractor.extract_from_pdf(path)
        except Exception as e:
            print(f"DEBUG: Error extracting {path}: {e}")
            return []

    # Map inputs: use pre-extracted if available, otherwise queue for parallel extraction
    targets = {
        "aadhaar": (pre_aadhaar, aadhaar_pdf),
        "ration":  (pre_ration, ration_pdf),
        "address": (pre_address, address_pdf),
        "caste":   (pre_caste, caste_pdf),
    }

    results = {}
    futures = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        for key, (pre_data, pdf_path) in targets.items():
            if pre_data:
                # Reuse pre-extracted results directly
                print(f"[process_documents] Reusing pre-extracted data for {key}")
                results[key] = pre_data if isinstance(pre_data, list) else [pre_data]
            elif pdf_path:
                # Submit for parallel VLM extraction
                print(f"[process_documents] Submitting parallel extraction for {key}: {pdf_path}")
                futures[key] = executor.submit(_extract_safe, pdf_path)
            else:
                results[key] = []

        # Gather parallel extraction results
        for key, future in futures.items():
            results[key] = future.result()

    aadhaar_results = results["aadhaar"]
    ration_results  = results["ration"]
    address_results = results["address"]
    caste_results   = results["caste"]


    # debugging/logging can be helpful when something is misclassified
    # (rations showing up as Voter ID, address proof shown as "Other", etc.)
    print("Aadhaar pages returned:", aadhaar_results)
    print("Ration pages returned:", ration_results)
    print("Address pages returned:", address_results)
    print("Caste pages returned:", caste_results)

    aadhaar_data = find_certificate(aadhaar_results, "Aadhaar") or {}
    ration_data = find_certificate(ration_results, "Ration Card") or {}
    
    # Handle case where Ration Card data uses "number" instead of "ration_card_number"
    if ration_data and "number" in ration_data and not ration_data.get("ration_card_number"):
        ration_data["ration_card_number"] = ration_data.get("number", "")
    
    address_data = find_certificate(address_results, "Address Proof") or {}
    caste_data = find_certificate(caste_results, "Caste Certificate") or {}

    # if we failed to find an address proof but we _did_ get something back
    # from the extractor, then keep the first page as a fallback so that the
    # returned JSON shows what the VLM actually produced.  This makes debugging
    # much easier when the classifier mis‑labels a document as Aadhaar (which
    # is what happened in the example above).
    if not address_data and address_results:
        address_data = address_results[0]
        # note: caller may want to know that this was a fallback
        address_data["_fallback_from"] = address_data.get("certificate_type", "<unknown>")

    # Same fallback logic for Ration Card
    if not ration_data and ration_results:
        ration_data = ration_results[0]
        ration_data["_fallback_from"] = ration_data.get("certificate_type", "<unknown>")

    # Same fallback logic for Caste Certificate
    if not caste_data and caste_results:
        caste_data = caste_results[0]
        caste_data["_fallback_from"] = caste_data.get("certificate_type", "<unknown>")

    validation = validator.validate_documents(aadhaar_data, ration_data, address_data)
    confidence_score = validator.compute_confidence(validation)

    # helper for the combined summary - with resolution-based priority
    def _get_resolution(doc):
        """Get resolution from document, default to 0 if not available"""
        return doc.get("_resolution", {}).get("total_pixels", 0) if doc else 0

    def _merge_with_resolution_priority(aadhaar, ration, address, caste=None):
        """Merge documents with priority based on resolution.

        Documents are sorted by resolution (highest first), and fields are
        taken from the highest resolution document that has that field.
        Caste Certificate contributes religion, community, and caste-specific fields.
        """
        # Create list of (document, resolution, doc_type) sorted by resolution descending
        docs_with_res = []
        if aadhaar:
            docs_with_res.append((aadhaar, _get_resolution(aadhaar), "Aadhaar"))
        if ration:
            docs_with_res.append((ration, _get_resolution(ration), "Ration"))
        if address:
            docs_with_res.append((address, _get_resolution(address), "Address"))
        if caste:
            docs_with_res.append((caste, _get_resolution(caste), "Caste"))

        # Sort by resolution (highest first)
        docs_with_res.sort(key=lambda x: x[1], reverse=True)

        print(f"Document priority order (by resolution): {[d[2] for d in docs_with_res]}")
        
        # Helper function to get field value with resolution priority
        def get_field_priority(*field_names):
            """Get field value from highest resolution document that has it"""
            for doc, _, _ in docs_with_res:
                for field in field_names:
                    val = doc.get(field)
                    if val:
                        return val
            return ""
        
        # Helper function to get field from specific document types (for fields that are document-specific)
        def get_aadhaar_field(field):
            return aadhaar.get(field, "") if aadhaar else ""

        def get_ration_field(field):
            return ration.get(field, "") if ration else ""

        def get_address_field(field):
            return address.get(field, "") if address else ""

        def get_caste_field(field):
            return caste.get(field, "") if caste else ""

        # Get name from highest resolution document that has it
        name = get_field_priority("name", "username")

        father_name = get_field_priority("father_name")
        raw_door_no  = get_field_priority("door_no")
        raw_street   = get_field_priority("street", "street_name")

        # Sanitise: if VLM put the guardian name (C/O / S/O) into address fields, clear them.
        def _looks_like_name(val):
            if not val:
                return False
            val_lower = val.strip().lower()
            # Exact match with father_name
            if father_name and val_lower == father_name.strip().lower():
                return True
            # Starts with S. / C. / D. / W. followed by a name (e.g. "S. Ashish")
            if re.match(r'^[scdw]\.\s+[a-z]', val_lower):
                return True
            return False

        door_no     = "" if _looks_like_name(raw_door_no) else raw_door_no
        street_name = "" if _looks_like_name(raw_street)  else raw_street

        # Build address string from resolution-priority winners (not hardcoded Aadhaar)
        addr_door   = door_no
        addr_street = street_name
        addr_area   = get_field_priority("area")
        addr_city   = get_field_priority("city")
        addr_state  = get_field_priority("state")
        addr_pin    = get_field_priority("pincode")
        address_parts = [p for p in [addr_door, addr_street, addr_area, addr_city, addr_state] if p]
        address_str = (", ".join(address_parts) + (" - " + addr_pin if addr_pin else "")) if address_parts else ""

        # dl_number: check address-proof doc first, then check any doc (DL may be classified as Address Proof)
        dl_number = get_address_field("dl_number") or get_field_priority("dl_number")

        # village: use area from Aadhaar as the best approximation of revenue village
        village = get_aadhaar_field("area") or get_field_priority("area")

        return {
            "username": name,
            "name":          name,
            "aadhaar_number": get_aadhaar_field("aadhaar_number"),
            "dl_number":     dl_number,
            "dob":           _normalise_dob(get_field_priority("dob")),
            "father_name":   father_name,
            "gender":        get_field_priority("gender"),
            "religion":      get_field_priority("religion") or get_caste_field("religion"),
            "community":     get_field_priority("community") or get_caste_field("community"),
            "caste":         get_caste_field("caste"),
            "state":         addr_state,
            "district":      get_field_priority("district"),
            "taluk":         get_field_priority("taluk"),
            "village":       village,
            "area":          addr_area,
            "city":          addr_city,
            "phone_number":  get_aadhaar_field("phone_number"),
            "email":         get_field_priority("email"),
            "ration_card_number": get_ration_field("number"),
            "address":       address_str,
            "door_no":       door_no,
            "street_name":   street_name,
            "pincode":       addr_pin,
        }

    combined = _merge_with_resolution_priority(aadhaar_data, ration_data, address_data, caste_data)

    # Get resolution info for each document
    aadhaar_resolution = aadhaar_data.get("_resolution", {}).get("total_pixels", 0)
    ration_resolution = ration_data.get("_resolution", {}).get("total_pixels", 0)
    address_resolution = address_data.get("_resolution", {}).get("total_pixels", 0)
    
    print(f"Document resolutions (total pixels):")
    print(f"  Aadhaar: {aadhaar_resolution}")
    print(f"  Ration Card: {ration_resolution}")
    print(f"  Address: {address_resolution}")

    output = {
        "aadhaar_data": aadhaar_data,
        "ration_data": ration_data,
        "address_data": address_data,
        "caste_data": caste_data,
        "combined": combined,
        # expose raw result lists in case the caller needs them
        "aadhaar_results": aadhaar_results,
        "ration_results": ration_results,
        "address_results": address_results,
        "caste_results": caste_results,
        "validation": {
            "name_similarity": validation.get("name_similarity", 0),
            "name_match": validation.get("name_match", False),
            "dob_match": validation.get("dob_match", False),
            "age_match": validation.get("age_match", False),
            "pairwise_similarity_scores": validation.get("pairwise_scores", {})
        },
        "confidence_score": confidence_score
    }
    return output

    