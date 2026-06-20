# intent/followup_suggester.py

FOLLOWUP_MAP = {
    "apply": [
        "What documents do I need for a new PAN?",
        "How long does it take to get the card?",
        "Can I track my application after submitting?",
    ],
    "document": [
        "Can Aadhaar cover all three proofs at once?",
        "What if I don't have a passport or voter ID?",
        "Do the documents need to be self-attested?",
    ],
    "aadhaar": [
        "What happens if I miss the Aadhaar-PAN linking deadline?",
        "How do I check if my Aadhaar is already linked?",
        "Is there a fee for linking Aadhaar with PAN?",
    ],
    "status": [
        "How long does delivery usually take after approval?",
        "What do I do if my application gets rejected?",
        "Can I get an e-PAN while waiting for the physical card?",
    ],
    "correction": [
        "Which documents do I need for a name correction?",
        "Can I correct my date of birth on PAN?",
        "How long does a correction request take to process?",
    ],
    "epan": [
        "Is e-PAN accepted for bank KYC?",
        "How do I open the e-PAN PDF — it's password protected?",
        "Can I use e-PAN for income tax filing?",
    ],
    "fee": [
        "How do I pay the PAN application fee?",
        "Is there a fee for downloading e-PAN?",
        "What's the fee for a correction or reprint?",
    ],
    "tan": [
        "What's the difference between PAN and TAN?",
        "Who actually needs a TAN?",
        "How do I apply for TAN?",
    ],
    "nri": [
        "Which form do NRIs use — 49A or 49AA?",
        "What address proof works for NRI applicants?",
        "Can an NRI apply for PAN from abroad?",
    ],
    "reprint": [
        "How do I apply for a duplicate PAN card?",
        "What if my PAN number is unknown after losing the card?",
        "How long does a reprint take?",
    ],
    "default": [
        "How do I apply for a new PAN card?",
        "What documents are required for PAN?",
        "How do I link Aadhaar with PAN?",
    ],
}


def get_followup_suggestions(question: str, answer: str) -> list[str]:
    """Return contextually relevant followup suggestions."""
    combined = (question + " " + answer).lower()
    for topic, suggestions in FOLLOWUP_MAP.items():
        if topic != "default" and topic in combined:
            return suggestions
    return FOLLOWUP_MAP["default"]
