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
        "ration card": ["voter id"],
        "address proof": ["residence certificate", "income certificate"],
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


def process_documents(aadhaar_pdf: str, ration_pdf: str = None, address_pdf: str = None) -> dict:
    # extract
    aadhaar_results = extractor.extract_from_pdf(aadhaar_pdf)
    ration_results = extractor.extract_from_pdf(ration_pdf) if ration_pdf else []
    address_results = extractor.extract_from_pdf(address_pdf) if address_pdf else []

    # debugging/logging can be helpful when something is misclassified
    # (rations showing up as Voter ID, address proof shown as "Other", etc.)
    print("Aadhaar pages returned:", aadhaar_results)
    print("Ration pages returned:", ration_results)
    print("Address pages returned:", address_results)

    aadhaar_data = find_certificate(aadhaar_results, "Aadhaar") or {}
    ration_data = find_certificate(ration_results, "Ration Card") or {}
    address_data = find_certificate(address_results, "Address Proof") or {}

    # if we failed to find an address proof but we _did_ get something back
    # from the extractor, then keep the first page as a fallback so that the
    # returned JSON shows what the VLM actually produced.  This makes debugging
    # much easier when the classifier mis‑labels a document as Aadhaar (which
    # is what happened in the example above).
    if not address_data and address_results:
        address_data = address_results[0]
        # note: caller may want to know that this was a fallback
        address_data["_fallback_from"] = address_data.get("certificate_type", "<unknown>")

    validation = validator.validate_documents(aadhaar_data, ration_data, address_data)
    confidence_score = validator.compute_confidence(validation)

    # helper for the combined summary
    def _merge(aadhaar, ration, address):
        return {
            "username": (
                 aadhaar.get("name") or
                address.get("name")
                or
                 ration.get("name")
                or ""
            ),
            "aadhaar_number": aadhaar.get("aadhaar_number",""),
            "dob": (
                aadhaar.get("dob")
                or ration.get("dob")
                or address.get("dob")
                or ""
            ),
            "father_name": (
                aadhaar.get("father_name")
                or ration.get("father_name")
                or address.get("father_name")
                or ""
            ),
            "religion": (
                address.get("religion") or
                aadhaar.get("religion")
                or ration.get("religion")
                or ""
            ),
            "community": (
                address.get("community")
                or aadhaar.get("community")
                or ration.get("community")
                or ""
            ),
            "state": (
                aadhaar.get("state")
                or ration.get("state")
                or address.get("state")
                or ""
            ),
            "district": (
                aadhaar.get("district")
                or ration.get("district")
                or address.get("district")
                or ""
            ),
            "taluk": (
                address.get("taluk") or
                aadhaar.get("taluk")
                or ration.get("taluk")
                or ""
            ),
            "phone_number": aadhaar.get("phone_number", ""),
            "ration_card_number": ration.get("ration_card_number", ""),
            "address": (
                f"{aadhaar['door_no']}, {aadhaar['street']}, {aadhaar['area']}, {aadhaar['city']}, {aadhaar['state']} - {aadhaar['pincode']}"
                or ""
            ),
            "door_no": (
                aadhaar.get("door_no") or
                ration.get("door_no")
                or address.get("door_no", "")
            ),
            "street_name": (
                aadhaar.get("street") or
                address.get("street") or
                
                ration.get("street")
                or ""
            ),
            "area": (
                address.get("area") or
                aadhaar.get("area") or
                ration.get("area")
                or ""
            ),
            "pincode": (
                aadhaar.get("pincode") or
                address.get("pincode") 
                or ration.get("pincode","")
                
            ),
            #"from_date": address.get("from_date", ""),
            #"to_date": address.get("to_date", ""),
            #"count_of_residence_years": address.get("count_of_residence_years", "")
        }

    combined = _merge(aadhaar_data, ration_data, address_data)

    output = {
        "aadhaar_data": aadhaar_data,
        "ration_data": ration_data,
        "address_data": address_data,
        "combined": combined,
        # expose raw result lists in case the caller needs them
        "aadhaar_results": aadhaar_results,
        "ration_results": ration_results,
        "address_results": address_results,
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

    