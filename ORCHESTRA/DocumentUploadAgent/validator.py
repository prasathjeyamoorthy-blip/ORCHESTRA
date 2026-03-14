from rapidfuzz import fuzz

import utils


def calculate_pairwise_similarity(doc1: dict, doc2: dict, name1: str, name2: str) -> dict:
    """Calculate name similarity between two documents."""
    n1 = utils.normalize_name(doc1.get("name", ""))
    n2 = utils.normalize_name(doc2.get("name", ""))
    
    if n1 and n2:
        sim = fuzz.ratio(n1, n2)
        return {
            f"{name1}_vs_{name2}_name_similarity": sim,
            f"{name1}_vs_{name2}_match": sim >= 85
        }
    return {
        f"{name1}_vs_{name2}_name_similarity": 0,
        f"{name1}_vs_{name2}_match": False
    }


def validate_documents(aadhaar_data: dict, ration_data: dict, address_data: dict = None) -> dict:
    """Validate fields between Aadhaar, Ration Card and Address Proof data.

    Returns a dict containing similarity and match flags.
    """
    if address_data is None:
        address_data = {}

    result = {
        "name_similarity": 0,
        "name_match": False,
        "dob_match": False,
        "age_match": False,
        "pairwise_scores": {}
    }

    # Pairwise similarity scores
    pair_aa_rat = calculate_pairwise_similarity(aadhaar_data, ration_data, "Aadhaar", "Ration Card")
    result["pairwise_scores"].update(pair_aa_rat)

    if address_data:
        pair_aa_addr = calculate_pairwise_similarity(aadhaar_data, address_data, "Aadhaar", "Address")
        result["pairwise_scores"].update(pair_aa_addr)
        
        pair_rat_addr = calculate_pairwise_similarity(ration_data, address_data, "Ration", "Address")
        result["pairwise_scores"].update(pair_rat_addr)

    # NAME - compare across all available documents
    name_a = utils.normalize_name(aadhaar_data.get("name", ""))
    name_r = utils.normalize_name(ration_data.get("username", "")) or utils.normalize_name(ration_data.get("name", ""))
    name_addr = utils.normalize_name(address_data.get("username", "")) or utils.normalize_name(address_data.get("name", ""))

    similarities = []
    if name_a and name_r:
        similarities.append(fuzz.ratio(name_a, name_r))
    if name_a and name_addr:
        similarities.append(fuzz.ratio(name_a, name_addr))
    if name_r and name_addr:
        similarities.append(fuzz.ratio(name_r, name_addr))

    if similarities:
        avg_similarity = sum(similarities) / len(similarities)
        result["name_similarity"] = int(avg_similarity)
        result["name_match"] = avg_similarity >= 85
    else:
        result["name_similarity"] = 0
        result["name_match"] = False

    # DOB - compare across all available documents
    dob_a = utils.normalize_dob(aadhaar_data.get("dob", ""))
    dob_r = utils.normalize_dob(ration_data.get("dob", ""))
    dob_addr = utils.normalize_dob(address_data.get("dob", ""))

    dob_matches = [dob_a, dob_r, dob_addr]
    dob_matches = [d for d in dob_matches if d]  # filter out empty

    if len(dob_matches) > 1:
        # check if all non-empty dobs match
        result["dob_match"] = all(d == dob_matches[0] for d in dob_matches)
    else:
        result["dob_match"] = False

    # AGE - compare across all available documents
    age_a = utils.calculate_age(dob_a) if dob_a else None
    age_r = utils.calculate_age(dob_r) if dob_r else None
    age_addr = utils.calculate_age(dob_addr) if dob_addr else None

    ages = [age_a, age_r, age_addr]
    ages = [a for a in ages if a is not None]  # filter out None

    if len(ages) > 1:
        # check if all non-None ages match
        result["age_match"] = all(a == ages[0] for a in ages)
    else:
        result["age_match"] = False

    return result


def compute_confidence(validation: dict) -> float:
    """Compute weighted confidence score from validation dict.

    Weights: name 50%, dob 30%, age 20%.
    """
    score = 0.0
    score += (validation.get("name_similarity", 0) / 100.0) * 50
    score += (1.0 if validation.get("dob_match") else 0.0) * 30
    score += (1.0 if validation.get("age_match") else 0.0) * 20
    # return as percentage
    return score