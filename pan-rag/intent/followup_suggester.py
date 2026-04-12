# intent/followup_suggester.py

# Followup suggestions mapped to PAN topics
FOLLOWUP_MAP = {
    "apply": [
        "What documents do I need to apply for PAN?",
        "How long does it take to get a PAN card?",
        "Can I apply for PAN online?",
    ],
    "document": [
        "Can I use Aadhaar as proof of identity?",
        "What if I don't have a passport?",
        "Are scanned copies of documents accepted?",
    ],
    "aadhaar": [
        "What is the deadline to link Aadhaar with PAN?",
        "What happens if I don't link Aadhaar with PAN?",
        "How do I check if my Aadhaar is linked to PAN?",
    ],
    "status": [
        "How long does PAN card delivery take?",
        "What if my PAN application is rejected?",
        "Can I track my PAN card by SMS?",
    ],
    "correction": [
        "What documents are needed for PAN correction?",
        "How long does PAN correction take?",
        "Can I correct my PAN details online?",
    ],
    "epan": [
        "Is e-PAN valid as a physical PAN card?",
        "How do I open the e-PAN PDF?",
        "Can I use e-PAN for bank KYC?",
    ],
    "fee": [
        "What is the fee for PAN correction?",
        "Is there any fee for e-PAN download?",
        "How can I pay the PAN application fee?",
    ],
    "tan": [
        "What is the difference between PAN and TAN?",
        "Who needs to apply for TAN?",
        "How do I apply for TAN online?",
    ],
    "default": [
        "How do I apply for a new PAN card?",
        "What documents are required for PAN?",
        "How do I link Aadhaar with PAN?",
    ],
}


def get_followup_suggestions(question: str, answer: str) -> list[str]:
    """Return relevant followup suggestions based on question and answer."""
    combined = (question + " " + answer).lower()
    
    for topic, suggestions in FOLLOWUP_MAP.items():
        if topic in combined:
            return suggestions
    
    return FOLLOWUP_MAP["default"]