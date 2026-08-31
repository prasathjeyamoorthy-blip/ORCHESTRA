import re
from typing import Tuple

_IN_SCOPE_KEYWORDS = re.compile(
    r"\b("
    r"residence|certificate|esevai|e-sevai|tnega|revenue|address|proof|self-declaration|declaration|"
    r"apply|application|document|documents|photo|smart card|ration|aadhaar|pan|passport|voter|driving|"
    r"fee|fees|cost|charge|rs|₹|60|service|id|75|"
    r"hi|hello|hey|bro|vanakkam|thanks|thank you|nandri|"
    r"doubts|doubt|question|help|clarify|ask|who are you|my name|who made you|are you sure|why|how|what|where"
    r")\b",
    re.IGNORECASE
)

_OUT_OF_SCOPE_KEYWORDS = re.compile(
    r"\b("
    r"python|java|c\+\+|javascript|code|script|program|algorithm|fibonacci|leetcode|"
    r"joke|jokes|poem|story|song|movie|cinema|actor|cricket|football|match|world cup|score|ipl|"
    r"recipe|pizza|cook|food|restaurant|capital|country|city|president|prime minister|"
    r"income certificate|caste certificate|community certificate|first graduate|voter id apply|passport apply|"
    r"math|solve|calculate|equation|physics|chemistry|biology|weather|news"
    r")\b",
    re.IGNORECASE
)

def is_residence_certificate_topic(message: str) -> bool:
    text = message.strip().lower()
    if not text:
        return True
    if "residence" in text:
        return True
    if _OUT_OF_SCOPE_KEYWORDS.search(text) and "residence" not in text:
        return False
    if _IN_SCOPE_KEYWORDS.search(text):
        return True
    if len(text.split()) <= 4:
        return True
    return False

def check_guardrail(message: str) -> Tuple[bool, str]:
    """
    Checks if the incoming user message is allowed.
    Returns (is_allowed, refusal_response).
    If is_allowed is False, the request must NOT reach the agent.
    """
    if not is_residence_certificate_topic(message):
        refusal = (
            "I am designed exclusively to assist with TNeGA Residence Certificate applications, "
            "required documents, and service fees. I cannot answer questions about unrelated topics. "
            "How can I help you with your Residence Certificate today?"
        )
        return False, refusal
    return True, ""
