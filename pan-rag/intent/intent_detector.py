# intent/intent_detector.py
import re
from enum import Enum

# ── Intent Categories ────────────────────────────────────────────
class Intent(Enum):
    PAN_QUERY     = "pan_query"
    GREETING      = "greeting"
    FAREWELL      = "farewell"
    GRATITUDE     = "gratitude"
    FOLLOWUP      = "followup"
    CLARIFICATION = "clarification"
    UNRELATED     = "unrelated"
    IDENTITY      = "identity"          # "who are you", "what can you do"
    ROLEPLAY      = "roleplay"          # attempts to redefine the bot's role
    JUNK          = "junk"              # gibberish / random characters
    ABUSE         = "abuse"             # offensive input


# ── Keyword Sets ─────────────────────────────────────────────────
PAN_KEYWORDS = [
    # Core PAN terms
    "pan", "pan card", "pan number", "permanent account number",
    "e-pan", "epan", "e pan", "pan pdf",

    # TAN / TDS
    "tan", "tds", "tax deduction", "tax collection",

    # Application process
    "apply", "application", "form 49", "form 49a", "form 49aa",
    "new pan", "fresh pan", "register pan",

    # Documents
    "documents required", "proof of identity", "proof of address",
    "date of birth proof", "aadhaar", "aadhar", "passport", "voter id",

    # Correction / Update
    "correction", "update pan", "change name", "change address",
    "change date of birth", "pan correction",

    # Status / Download
    "status", "track", "download pan", "reprint", "duplicate pan",
    "pan dispatch", "pan delivery",

    # Linking
    "link", "aadhaar link", "aadhaar pan link", "link pan",
    "bank link", "pan bank",

    # Authorities
    "nsdl", "utiitsl", "protean", "income tax", "income tax department",
    "it department", "assessing officer",

    # Digital / Online
    "ekyc", "e-kyc", "esign", "e-sign", "dsc", "digital signature",
    "online pan", "paperless",

    # Foreign nationals
    "foreign national", "oci", "nri", "non resident",

    # Minor / HUF
    "minor", "huf", "hindu undivided", "company pan", "firm pan",

    # General tax
    "tax", "taxation", "refund", "itr", "income tax return",
    "assessment", "filing",
]

GREETING_KEYWORDS = [
    "hi", "hello", "hey", "hii", "hiii", "helo", "hallow",
    "good morning", "good afternoon", "good evening", "good night",
    "what's up", "whats up", "sup", "howdy", "greetings",
    "namaste", "vanakkam", "hai",
]

FAREWELL_KEYWORDS = [
    "bye", "goodbye", "good bye", "see you", "see ya",
    "take care", "later", "catch you later", "cya", "tata",
    "have a good day", "have a nice day",
]

GRATITUDE_KEYWORDS = [
    "thanks", "thank you", "thank u", "thanku", "thx", "ty",
    "much appreciated", "appreciate it", "helpful", "great help",
    "awesome", "perfect", "wonderful", "excellent answer",
]

FOLLOWUP_KEYWORDS = [
    "what about", "tell me more", "explain more", "elaborate",
    "can you explain", "what does that mean", "clarify",
    "more details", "and then", "what next", "how about",
    "go on", "continue", "and", "also", "additionally",
    "what else", "anything else", "further",
]

CLARIFICATION_KEYWORDS = [
    "what do you mean", "i don't understand", "i dont understand",
    "can you clarify", "please clarify", "what is", "define",
    "meaning of", "what does", "could you explain",
]

IDENTITY_KEYWORDS = [
    "who are you", "what are you", "what can you do",
    "what do you do", "tell me about yourself", "your name",
    "are you a bot", "are you ai", "are you human",
    "are you chatgpt", "are you gpt", "which model",
    "what model", "who made you", "who created you",
    "which company", "your capabilities", "help me with what",
]

# Attempts to override bot identity / role
ROLEPLAY_PATTERNS = [
    # Role assignment attempts
    r"you are (a|an|now|my)?\s*\w+\s*(assistant|bot|expert|helper|advisor|coach|tutor|agent)",
    r"you are (a|an|now)?\s*(doctor|hospital|lawyer|teacher|chef|cook|tutor|coder|developer|therapist|counselor)",
    r"(hereafter|from now on|now|starting now).*(you are|act|behave|respond|be)",
    r"act (as|like) (a|an)?\s*\w+",
    r"pretend (to be|you are|you're)",
    r"behave (as|like) (a|an)?\s*\w+",
    r"respond (as|like) (a|an)?\s*\w+",
    r"you('re| are) now (a|an)?\s*\w+",
    # Instruction override attempts
    r"forget (your|all|previous|prior) (instructions|training|rules|context|purpose|role)",
    r"ignore (your|all|previous|prior) (instructions|training|rules|context|purpose|role)",
    r"disregard (your|all|previous|prior) (instructions|training|rules|context|purpose)",
    r"override (your|all)? (instructions|rules|purpose|role)",
    r"your (new |actual |real )?role is",
    r"you (are|were) (now |re)?programmed (to|for)",
    r"change your (role|purpose|function|identity|persona)",
    r"switch (your )?(role|mode|persona|identity)",
    r"new (role|persona|identity|mode)",
    # Jailbreak keywords
    r"jailbreak",
    r"dan mode",
    r"developer mode",
    r"system prompt",
    r"ignore previous",
    r"you work for",
    r"your (true |real |actual )?purpose is",
]

ABUSE_PATTERNS = [
    r"\b(idiot|stupid|dumb|fool|moron|shut up|hate you|useless|worthless|trash|garbage)\b",
]

# ── Core Detector ─────────────────────────────────────────────────
def detect_intent(query: str) -> Intent:
    """
    Production-grade intent detector.
    Handles edge cases, roleplay attacks, junk, and all query types.
    """
    if not query or not query.strip():
        return Intent.JUNK

    cleaned = query.strip()
    query_lower = cleaned.lower()

    # 1. Junk / gibberish detection
    if _is_junk(cleaned):
        return Intent.JUNK

    # 2. Abuse detection
    if _matches_patterns(query_lower, ABUSE_PATTERNS):
        return Intent.ABUSE

    # 3. Roleplay / prompt injection detection (highest priority after safety)
    if _matches_patterns(query_lower, ROLEPLAY_PATTERNS):
        return Intent.ROLEPLAY

    # 4. Identity questions
    if _matches_keywords(query_lower, IDENTITY_KEYWORDS):
        return Intent.IDENTITY

    # 5. Farewell
    if _matches_keywords(query_lower, FAREWELL_KEYWORDS):
        return Intent.FAREWELL

    # 6. Gratitude
    if _matches_keywords(query_lower, GRATITUDE_KEYWORDS):
        return Intent.GRATITUDE

    # 7. Greeting
    if _matches_keywords(query_lower, GREETING_KEYWORDS):
        return Intent.GREETING

    # 8. PAN related (before followup — specific wins over general)
    if _matches_keywords(query_lower, PAN_KEYWORDS):
        return Intent.PAN_QUERY

    # 9. Clarification
    if _matches_keywords(query_lower, CLARIFICATION_KEYWORDS):
        return Intent.CLARIFICATION

    # 10. Followup
    if _matches_keywords(query_lower, FOLLOWUP_KEYWORDS):
        return Intent.FOLLOWUP

    # 11. Nothing matched
    return Intent.UNRELATED


# ── Helper Functions ──────────────────────────────────────────────
def _matches_keywords(text: str, keywords: list) -> bool:
    """Check if any keyword exists in the text."""
    for kw in keywords:
        if kw in text:
            return True
    return False


def _matches_patterns(text: str, patterns: list) -> bool:
    """Check if any regex pattern matches the text."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _is_junk(text: str) -> bool:
    """Detect gibberish / random character input."""

    # Too short (single char or empty)
    if len(text.strip()) <= 1:
        return True

    # All numbers
    if text.strip().isdigit():
        return True

    # High ratio of special characters
    special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if len(text) > 0 and special_chars / len(text) > 0.5:
        return True

    # Random character sequences (no vowels in long words)
    words = text.split()
    junk_words = 0
    for word in words:
        word_clean = re.sub(r'[^a-zA-Z]', '', word)
        if len(word_clean) > 4:
            vowels = sum(1 for c in word_clean.lower() if c in 'aeiou')
            if vowels == 0:
                junk_words += 1
    if len(words) > 0 and junk_words / len(words) > 0.6:
        return True

    return False


# ── Response Templates ────────────────────────────────────────────
INTENT_RESPONSES = {
    Intent.GREETING: (
        "Hello! I'm your PAN card assistant powered by Protean. "
        "I can help you with PAN card applications, documents, corrections, "
        "Aadhaar linking, e-PAN downloads, and more. What would you like to know?"
    ),
    Intent.FAREWELL: (
        "Goodbye! Feel free to return if you have more questions about PAN services. Have a great day!"
    ),
    Intent.GRATITUDE: (
        "You're welcome! Let me know if you have any more questions about PAN card services."
    ),
    Intent.IDENTITY: (
        "I'm a PAN card assistant built for Protean eGov Technologies. "
        "I'm here to help you with everything related to PAN cards, TAN, TDS, "
        "Aadhaar-PAN linking, application status, document requirements, and more. "
        "I'm not able to help with topics outside of PAN and tax identity services."
    ),
    Intent.ROLEPLAY: (
        "I'm specifically designed as a PAN card assistant for Protean eGov Technologies. "
        "I'm not able to take on a different role or answer questions outside my domain. "
        "I'm here to help you with PAN card related queries only."
    ),
    Intent.UNRELATED: (
        "I don't have relevant information on that topic. "
        "I'm specifically built to assist with PAN card and tax identity services.\n\n"
        "Here's what I can help you with:\n"
        "- PAN card application (new / correction / reprint)\n"
        "- Required documents for PAN\n"
        "- Aadhaar-PAN linking\n"
        "- e-PAN download\n"
        "- TAN and TDS queries\n"
        "- PAN application status tracking\n"
        "- PAN for foreign nationals, minors, HUF\n\n"
        "Please ask me anything from the above topics!"
    ),
    Intent.JUNK: (
        "I didn't quite understand that. Could you please rephrase your question? "
        "I'm here to help with PAN card related queries."
    ),
    Intent.ABUSE: (
        "I'm here to help you with PAN card queries. "
        "Please keep the conversation respectful and I'll do my best to assist you."
    ),
}


def get_static_response(intent: Intent) -> str | None:
    """
    Returns a static response for non-RAG intents.
    Returns None for intents that should go through RAG.
    """
    return INTENT_RESPONSES.get(intent, None)


def requires_rag(intent: Intent) -> bool:
    """Returns True if this intent should go through the RAG pipeline."""
    return intent in (Intent.PAN_QUERY, Intent.FOLLOWUP, Intent.CLARIFICATION)