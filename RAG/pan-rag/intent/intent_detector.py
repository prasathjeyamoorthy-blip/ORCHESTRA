"""
intent/intent_detector.py — Production-level intent classifier
"""

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


# ── Safety patterns ───────────────────────────────────────────────
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

# ── PAN domain — broad regex ──────────────────────────────────────
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
    r"tax|taxation|refund|filing|assessment|"
    # Flow continuation — "what next", "what should i give/submit/upload"
    r"document|documents|submit|upload|attach|proof|"
    r"next\s+step|what\s+next|what\s+should\s+i|how\s+do\s+i\s+proceed|"
    r"what\s+do\s+i\s+(need|have\s+to|give|submit|upload|provide)|"
    r"what\s+are\s+(all\s+the\s+)?(documents|proofs|files|requirements))\b",
    re.IGNORECASE
)

# ── Flow response — short structured replies that are NEVER junk ──
_FLOW_RESPONSE = re.compile(
    r"^("
    r"\d{1,2}"
    r"|option\s*\d"
    r"|yes|no|ok|okay|sure|ready|done|yep|yup|yeah|nope|nah"
    r"|indian|foreign|company|huf|firm|citizen|nri|overseas"
    r"|online|offline|physical|digital"
    r"|monthly|annual|annually|yearly"
    r"|salaried|business|student|fresher|unemployed|retired|homemaker"
    r"|[A-Z]{5}[0-9]{4}[A-Z]"
    r"|\d{12}"
    r")\s*[.!?]?\s*$",
    re.IGNORECASE
)

# ── Memory / personal info questions ─────────────────────────────
_MEMORY_PATTERN = re.compile(
    r"\b(my\s+(name|income|salary|email|mother|father|pan|aadhaar|address|age|dob|date\s+of\s+birth)|"
    r"what\s+(is|are|was|were)\s+my|do\s+you\s+(know|remember|recall|have)|"
    r"you\s+(know|remember|said|told)|what\s+did\s+(i|you)\s+say|"
    r"did\s+i\s+(tell|give|share|mention|provide)\s+you|"
    r"did\s+you\s+(get|receive|save|store|note)\s+my|"
    r"have\s+i\s+(told|given|shared|mentioned|provided)\s+you|"
    r"did\s+i\s+share|"
    r"i\s+(told|said|mentioned|gave|shared|provided))\b",
    re.IGNORECASE
)

# ── Context continuation ──────────────────────────────────────────
_CONTINUATION = re.compile(
    r"^(ok|okay|ready|sure|proceed|continue|go\s+ahead|"
    r"yes\s+please|let'?s\s+go|do\s+it|sounds\s+good|"
    r"got\s+it|understood|alright|fine|noted|"
    r"what\s+next|next\s+step|now\s+what|ok\s+next|"
    r"next\s+what|what\s+now|and\s+then|then\s+what|"
    r"i\s+am\s+ready|i'm\s+ready|i\s+will|i'll)\s*[.!?]?\s*$",
    re.IGNORECASE
)

# ── Social keyword lists ──────────────────────────────────────────
GREETING_KEYWORDS = [
    "hi", "hello", "hey", "hii", "hiii", "helo", "hallow",
    "good morning", "good afternoon", "good evening", "good night",
    "what's up", "whats up", "sup", "howdy", "greetings",
    "namaste", "vanakkam", "hai",
    # casual address words — treat as greeting, not unrelated
    "bro", "dude", "mate", "buddy", "man", "bhai", "da", "machan",
    "yo", "ayo", "bruh",
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


def detect_intent(query: str, session_history: list = None) -> Intent:
    """
    Classify the intent of a user message.

    Context-aware: session_history prevents short flow replies
    from being misclassified as JUNK or UNRELATED.
    """
    if not query or not query.strip():
        return Intent.JUNK

    cleaned     = query.strip()
    q           = cleaned.lower()
    has_history = bool(session_history)

    # 1. Abuse
    if _matches_patterns(q, ABUSE_PATTERNS):
        return Intent.ABUSE

    # 2. Roleplay / prompt injection
    if _matches_patterns(q, ROLEPLAY_PATTERNS):
        return Intent.ROLEPLAY

    # 3. Flow response — structured short replies are always PAN_QUERY
    if _FLOW_RESPONSE.match(cleaned):
        return Intent.PAN_QUERY

    # 4. Junk — only when no history and truly meaningless
    if not has_history and _is_junk(cleaned):
        return Intent.JUNK

    # 5. Identity
    if _matches_keywords(q, IDENTITY_KEYWORDS):
        return Intent.IDENTITY

    # 6. Farewell
    if _matches_keywords(q, FAREWELL_KEYWORDS):
        return Intent.FAREWELL

    # 7. Gratitude
    if _matches_keywords(q, GRATITUDE_KEYWORDS):
        return Intent.GRATITUDE

    # 8. Greeting — only if short and no PAN content
    if _matches_keywords(q, GREETING_KEYWORDS) and not PAN_DOMAIN_PATTERN.search(q):
        return Intent.GREETING

    # 9. Memory / personal info questions
    if _MEMORY_PATTERN.search(q):
        return Intent.PAN_QUERY

    # 10. PAN domain — direct keyword match
    if PAN_DOMAIN_PATTERN.search(q):
        return Intent.PAN_QUERY

    # 11. Semantic PAN detection — skip LLM classifier, use keyword fallback
    #     (classifier adds latency; BM25 retrieval handles domain filtering)

    # 12. Clarification
    if _matches_keywords(q, CLARIFICATION_KEYWORDS):
        return Intent.CLARIFICATION

    # 13. Resume / context continuation — check BEFORE followup so "continue from where"
    #     doesn't get swallowed by the "continue" followup keyword
    _RESUME_PATTERN = re.compile(
        r"\b("
        r"where\s+(we|i|did\s+we|did\s+i)\s+\w+|"
        r"where\s+were\s+we|where\s+was\s+i|"
        r"continue\s+(from|where|our|the)|resume|pick\s+up\s+where|"
        r"last\s+(time|session|chat|conversation|we\s+spoke|we\s+talked)|"
        r"next\s+what\s+to\s+do|what\s+to\s+do\s+next|"
        r"what\s+(should|do)\s+i\s+do\s+next|"
        r"what\s+is\s+(the\s+)?next\s+step|"
        r"what\s+next|now\s+what|"
        r"(get|go)\s+back\s+to"
        r")\b",
        re.IGNORECASE
    )
    if _RESUME_PATTERN.search(q):
        return Intent.PAN_QUERY

    # 14. Followup
    if _matches_keywords(q, FOLLOWUP_KEYWORDS):
        return Intent.FOLLOWUP

    # 15. Unrelated
    return Intent.UNRELATED


def _matches_keywords(text: str, keywords: list) -> bool:
    """Match keywords as whole words only (not substrings)."""
    words = set(re.findall(r"[a-z']+", text.lower()))
    for kw in keywords:
        # Multi-word keywords: check as substring phrase
        if ' ' in kw:
            if kw in text:
                return True
        else:
            # Single-word: must be a whole word
            if kw in words:
                return True
    return False


def _matches_patterns(text: str, patterns: list) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _is_junk(text: str) -> bool:
    """Conservative junk check — only truly meaningless input."""
    stripped = text.strip()

    # Single character (not a letter or digit)
    if len(stripped) <= 1 and not stripped.isalnum():
        return True

    # Pure symbols / emoji spam
    special = sum(1 for c in stripped if not c.isalnum() and not c.isspace())
    if len(stripped) > 0 and special / len(stripped) > 0.7:
        return True

    # Keyboard mash: long word with no vowels
    words = stripped.split()
    junk_words = 0
    for word in words:
        w = re.sub(r'[^a-zA-Z]', '', word)
        if len(w) > 5 and sum(1 for c in w.lower() if c in 'aeiou') == 0:
            junk_words += 1
    if words and junk_words / len(words) > 0.6:
        return True

    return False


def requires_rag(intent: Intent) -> bool:
    return intent in (Intent.PAN_QUERY, Intent.FOLLOWUP, Intent.CLARIFICATION)
