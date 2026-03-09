import json
import sys

import extractor, validator


from typing import Optional

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


def process_documents(aadhaar_pdf: str, ration_pdf: str = None, address_pdf: str = None, caste_pdf: str = None) -> dict:
    # Debug: Print file paths
    print(f"DEBUG: aadhaar_pdf = {aadhaar_pdf}")
    print(f"DEBUG: ration_pdf = {ration_pdf}")
    print(f"DEBUG: address_pdf = {address_pdf}")
    print(f"DEBUG: caste_pdf = {caste_pdf}")
    
    # extract
    aadhaar_results = extractor.extract_from_pdf(aadhaar_pdf)
    ration_results = extractor.extract_from_pdf(ration_pdf) if ration_pdf else []
    address_results = extractor.extract_from_pdf(address_pdf) if address_pdf else []
    
    # Handle caste extraction with better error handling
    caste_results = []
    if caste_pdf:
        try:
            caste_results = extractor.extract_from_pdf(caste_pdf)
        except Exception as e:
            print(f"DEBUG: Error extracting caste PDF: {e}")
            caste_results = []
    else:
        print("DEBUG: No caste_pdf provided")

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

    def _merge_with_resolution_priority(aadhaar, ration, address):
        """Merge documents with priority based on resolution.
        
        Documents are sorted by resolution (highest first), and fields are 
        taken from the highest resolution document that has that field.
        """
        # Create list of (document, resolution, doc_type) sorted by resolution descending
        docs_with_res = []
        if aadhaar:
            docs_with_res.append((aadhaar, _get_resolution(aadhaar), "Aadhaar"))
        if ration:
            docs_with_res.append((ration, _get_resolution(ration), "Ration"))
        if address:
            docs_with_res.append((address, _get_resolution(address), "Address"))
        
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
        
        # Get name from highest resolution document that has it
        name = get_field_priority("name", "username")
        
        return {
            "username": name,
            "aadhaar_number": get_aadhaar_field("aadhaar_number"),
            "dob": get_field_priority("dob"),
            "father_name": get_field_priority("father_name"),
            "religion": get_field_priority("religion"),
            "community": get_field_priority("community"),
            "state": get_field_priority("state"),
            "district": get_field_priority("district"),
            "taluk": get_field_priority("taluk"),
            "phone_number": get_aadhaar_field("phone_number"),
            "ration_card_number": get_ration_field("number"),
            "address": (
                f"{get_aadhaar_field('door_no')}, {get_aadhaar_field('street')}, {get_aadhaar_field('area')}, {get_aadhaar_field('city')}, {get_aadhaar_field('state')} - {get_aadhaar_field('pincode')}"
                or ""
            ),
            "door_no": get_field_priority("door_no"),
            "street_name": get_field_priority("street", "street_name"),
            "area": get_field_priority("area"),
            "pincode": get_field_priority("pincode"),
        }

    combined = _merge_with_resolution_priority(aadhaar_data, ration_data, address_data)

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

    