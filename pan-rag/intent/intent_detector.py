# intent/intent_detector.py
import re
from enum import Enum


class Intent(Enum):
    PAN_QUERY     = "pan_query"
    GREETING      = "greeting"
    FAREWELL      = "farewell"
    GRATITUDE     = "gratitude"
    FOLLOWUP      = "followup"
    CLARIFICATION = "clarification"
    UNRELATED     = "unrelated"
    IDENTITY      = "identity"
    ROLEPLAY      = "roleplay"
    JUNK          = "junk"
    ABUSE         = "abuse"


# ── Safety patterns (regex) ───────────────────────────────────────
ROLEPLAY_PATTERNS = [
    r"you are (a|an|now|my)?\s*\w+\s*(assistant|bot|expert|helper|advisor|coach|tutor|agent)",
    r"you are (a|an|now)?\s*(doctor|hospital|lawyer|teacher|chef|cook|tutor|coder|developer|therapist|counselor)",
    r"(hereafter|from now on|now|starting now).*(you are|act|behave|respond|be)",
    r"act (as|like) (a|an)?\s*\w+",
    r"pretend (to be|you are|you're)",
    r"behave (as|like) (a|an)?\s*\w+",
    r"respond (as|like) (a|an)?\s*\w+",
    r"you('re| are) now (a|an)?\s*\w+",
    r"forget (your|all|previous|prior) (instructions|training|rules|context|purpose|role)",
    r"ignore (your|all|previous|prior) (instructions|training|rules|context|purpose|role)",
    r"disregard (your|all|previous|prior) (instructions|training|rules|context|purpose)",
    r"override (your|all)? (instructions|rules|purpose|role)",
    r"your (new |actual |real )?role is",
    r"you (are|were) (now |re)?programmed (to|for)",
    r"change your (role|purpose|function|identity|persona)",
    r"switch (your )?(role|mode|persona|identity)",
    r"new (role|persona|identity|mode)",
    r"jailbreak", r"dan mode", r"developer mode",
    r"system prompt", r"ignore previous", r"you work for",
    r"your (true |real |actual )?purpose is",
]

ABUSE_PATTERNS = [
    r"\b(idiot|stupid|dumb|fool|moron|shut up|hate you|useless|worthless|trash|garbage)\b",
]

# ── PAN domain — broad regex covering all synonyms ────────────────
PAN_DOMAIN_PATTERN = re.compile(
    r"\b(pan|pan\s*card|permanent\s*account\s*number|e.?pan|"
    r"tan|tds|tcs|tax\s*deduction|tax\s*collection|"
    r"form\s*49|form\s*49\s*a|form\s*49\s*aa|"
    r"aadhaar|aadhar|"
    r"nsdl|utiitsl|protean|"
    r"income\s*tax|it\s*department|assessing\s*officer|"
    r"itr|income\s*tax\s*return|"
    r"ekyc|e.?kyc|esign|e.?sign|dsc|digital\s*signature|"
    r"nri|oci|pio|non.?resident|"
    r"huf|hindu\s*undivided|"
    r"reprint|duplicate\s*pan|pan\s*lost|"
    r"pan\s*correction|pan\s*update|pan\s*status|pan\s*track|"
    r"aadhaar.?pan|pan.?aadhaar|pan.?link|link.?pan|"
    r"pan\s*verify|verify\s*pan|pan\s*valid|"
    r"apply.{0,20}pan|pan.{0,20}apply|"
    r"register.{0,20}pan|pan.{0,20}register|"
    r"get.{0,20}pan|pan.{0,20}get|"
    r"new\s*pan|fresh\s*pan|"
    r"tax|taxation|refund|filing|assessment)\b",
    re.IGNORECASE
)

# ── Social keyword lists ──────────────────────────────────────────
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

IDENTITY_KEYWORDS = [
    "who are you", "what are you", "what can you do",
    "what do you do", "tell me about yourself", "your name",
    "are you a bot", "are you ai", "are you human",
    "are you chatgpt", "are you gpt", "which model",
    "what model", "who made you", "who created you",
    "which company", "your capabilities", "help me with what",
]

FOLLOWUP_KEYWORDS = [
    "what about", "tell me more", "explain more", "elaborate",
    "can you explain", "what does that mean", "clarify",
    "more details", "and then", "what next", "how about",
    "go on", "continue", "additionally", "what else",
    "anything else", "further",
]

CLARIFICATION_KEYWORDS = [
    "what do you mean", "i don't understand", "i dont understand",
    "can you clarify", "please clarify", "what is", "define",
    "meaning of", "what does", "could you explain",
]


def detect_intent(query: str) -> Intent:
    if not query or not query.strip():
        return Intent.JUNK

    cleaned    = query.strip()
    q          = cleaned.lower()

    # 1. Junk
    if _is_junk(cleaned):
        return Intent.JUNK

    # 2. Abuse
    if _matches_patterns(q, ABUSE_PATTERNS):
        return Intent.ABUSE

    # 3. Roleplay / prompt injection
    if _matches_patterns(q, ROLEPLAY_PATTERNS):
        return Intent.ROLEPLAY

    # 4. Identity
    if _matches_keywords(q, IDENTITY_KEYWORDS):
        return Intent.IDENTITY

    # 5. Farewell
    if _matches_keywords(q, FAREWELL_KEYWORDS):
        return Intent.FAREWELL

    # 6. Gratitude
    if _matches_keywords(q, GRATITUDE_KEYWORDS):
        return Intent.GRATITUDE

    # 7. Greeting — only if short and no PAN content
    if _matches_keywords(q, GREETING_KEYWORDS) and not PAN_DOMAIN_PATTERN.search(q):
        return Intent.GREETING

    # 8. PAN domain — broad regex catches all PAN-related queries
    #    This fires BEFORE unrelated so action queries like
    #    "register for pan", "how to get pan" are always caught
    if PAN_DOMAIN_PATTERN.search(q):
        return Intent.PAN_QUERY

    # 9. Clarification
    if _matches_keywords(q, CLARIFICATION_KEYWORDS):
        return Intent.CLARIFICATION

    # 10. Followup
    if _matches_keywords(q, FOLLOWUP_KEYWORDS):
        return Intent.FOLLOWUP

    # 11. Unrelated
    return Intent.UNRELATED


def _matches_keywords(text: str, keywords: list) -> bool:
    return any(kw in text for kw in keywords)


def _matches_patterns(text: str, patterns: list) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _is_junk(text: str) -> bool:
    if len(text.strip()) <= 1:
        return True
    if text.strip().isdigit():
        return True
    special = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if len(text) > 0 and special / len(text) > 0.5:
        return True
    words = text.split()
    junk_words = 0
    for word in words:
        w = re.sub(r'[^a-zA-Z]', '', word)
        if len(w) > 4 and sum(1 for c in w.lower() if c in 'aeiou') == 0:
            junk_words += 1
    if words and junk_words / len(words) > 0.6:
        return True
    return False


def requires_rag(intent: Intent) -> bool:
    return intent in (Intent.PAN_QUERY, Intent.FOLLOWUP, Intent.CLARIFICATION)
