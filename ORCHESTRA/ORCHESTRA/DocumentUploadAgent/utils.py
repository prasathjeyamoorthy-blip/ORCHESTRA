import re
from datetime import datetime, date


def normalize_name(name: str) -> str:
    """Lowercase, remove dots and extra spaces."""
    if not name:
        return ""
    name = name.lower()
    name = name.replace(".", "")
    # collapse multiple spaces
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def normalize_dob(dob_str: str) -> str:
    """Convert various date formats to YYYY-MM-DD."
    Supported formats: %d/%m/%Y, %d-%m-%Y, %Y-%m-%d
    Returns normalized string or empty if invalid.
    """
    if not dob_str or not isinstance(dob_str, str):
        return ""
    dob_str = dob_str.strip()
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(dob_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # attempt to parse with dateutil if available
    try:
        from dateutil import parser
        dt = parser.parse(dob_str, dayfirst=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


from typing import Optional

def calculate_age(dob_normalized: str) -> Optional[int]:
    """Return age in years from normalized dob YYYY-MM-DD."""
    if not dob_normalized:
        return None
    try:
        dob = datetime.strptime(dob_normalized, "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age
