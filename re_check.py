import re
from datetime import datetime

# -------------------------------
# 🔹 1. CLEANING FUNCTIONS
# -------------------------------

def clean_text(text):
    if not text:
        return ""
    return text.strip()

def remove_spaces(text):
    return text.replace(" ", "")

# -------------------------------
# 🔹 2. NORMALIZATION (OCR Fixes)
# -------------------------------

def normalize_pan(pan):
    if not pan:
        return ""
    pan = pan.upper()
    pan = pan.replace("0", "O")  # OCR fix
    return pan

# -------------------------------
# 🔹 3. BASIC VALIDATIONS
# -------------------------------

def validate_length(text, min_len=1, max_len=100):
    return min_len <= len(text) <= max_len

def validate_numeric(value):
    return str(value).isdigit()

# -------------------------------
# 🔹 4. REGEX VALIDATIONS
# -------------------------------

def validate_aadhaar(aadhaar):
    aadhaar = remove_spaces(aadhaar)
    return bool(re.fullmatch(r"\d{12}", aadhaar))

def validate_pan(pan):
    pan = normalize_pan(pan)
    return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan))

def validate_mobile(mobile):
    return bool(re.fullmatch(r"[6-9]\d{9}", mobile))

def validate_email(email):
    return bool(re.fullmatch(r"[\w\.-]+@[\w\.-]+\.\w+", email))

def validate_pincode(pincode):
    return bool(re.fullmatch(r"\d{6}", pincode))

# -------------------------------
# 🔹 5. DATE VALIDATION
# -------------------------------

def validate_dob(dob):
    formats = ["%d/%m/%Y", "%d-%m-%Y","%Y-%m-%d", "%Y-%m-%d"]
    for fmt in formats:
        try:
            datetime.strptime(dob, fmt)
            return True
        except:
            continue
    return False

# -------------------------------
# 🔹 6. ENUM VALIDATION
# -------------------------------

def validate_gender(gender):
    if not gender:
        return False
    return gender.lower() in ["male", "female", "other"]

# -------------------------------
# 🔹 7. CROSS-FIELD VALIDATION
# -------------------------------

def calculate_age(dob):
    try:
        dob_obj = datetime.strptime(dob, "%d/%m/%Y")
        today = datetime.today()
        return today.year - dob_obj.year - ((today.month, today.day) < (dob_obj.month, dob_obj.day))
    except:
        return None

def validate_age_dob(age, dob):
    calculated_age = calculate_age(dob)
    if calculated_age is None:
        return False
    return abs(calculated_age - int(age)) <= 1  # allow slight mismatch

# -------------------------------
# 🔹 8. MASTER VALIDATION PIPELINE
# -------------------------------

def validate_document(data):
    """
    data = {
        "aadhaar": "",
        "pan": "",
        "mobile": "",
        "email": "",
        "dob": "",
        "age": "",
        "gender": "",
        "pincode": "",
        "name": ""
    }
    """

    results = {}

    # Cleaning
    data = {k: clean_text(str(v)) for k, v in data.items() if v is not None}

    # Individual validations
    results["aadhaar_valid"] = validate_aadhaar(data.get("aadhaar", ""))
    # results["pan_valid"] = validate_pan(data.get("pan", ""))
    results["mobile_valid"] = validate_mobile(data.get("mobile", ""))
    # results["email_valid"] = validate_email(data.get("email", ""))
    results["dob_valid"] = validate_dob(data.get("dob", ""))
    results["gender_valid"] = validate_gender(data.get("gender", ""))
    # results["pincode_valid"] = validate_pincode(data.get("pincode", ""))
    results["name_valid"] = validate_length(data.get("name", ""), 2, 100)

    # Cross validation
    # if "age" in data and "dob" in data:
    #     results["age_dob_match"] = validate_age_dob(data.get("age"), data.get("dob"))

    # Overall decision
    results["overall_valid"] = all(results.values())

    return results

# -------------------------------
# 🔹 9. EXAMPLE USAGE
# -------------------------------

if __name__ == "__main__":
    sample_data = {
        "aadhaar": "123412341234",
        "pan": "ABCDE1234F",
        "mobile": "9876543210",
        "email": "test@gmail.com",
        "dob": "15/08/2000",
        "age": "24",
        "gender": "Male",
        "pincode": "600001",
        "name": "Javid Ali"
    }

    result = validate_document(sample_data)
    print(result)