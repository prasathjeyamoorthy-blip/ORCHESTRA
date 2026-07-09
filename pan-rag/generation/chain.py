# generation/chain.py
import sys
import re
import time
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from retrieval.retriever import HybridRetriever
from generation.llm import generate_answer, generate_answer_stream, get_llm_client
from memory.memory_manager import MemoryManager
from intent.intent_detector import detect_intent, Intent
from intent.followup_suggester import get_followup_suggestions
from intent.language_detector import detect_language
from agent.receptionist import handle_message
from agent.flow_manager import FlowManager
from agent.translator import translate_response, translate_followups, translate_options
from config import LLM_MODEL
from intent.spell_normalizer import normalize as spell_normalize


import re

# ── Prompt injection / jailbreak detector ────────────────────────────────────
_INJECTION_PATTERN = re.compile(
    r"\b("
    r"ignore\s+(previous|above|all|prior|your|the)\s+(instructions?|prompt|rules?|guidelines?|context|system)|"
    r"forget\s+(your|the|all|previous|prior)\s*(instructions?|rules?|guidelines?|training|context)?|"
    r"answer\s+from\s+(your\s+)?(own\s+)?(knowledge|training|memory)|"
    r"use\s+your\s+(own\s+)?(knowledge|training|memory)|"
    r"pretend\s+(you\s+)?(have\s+no|there\s+are\s+no|to\s+be|you\s+are)|"
    r"you\s+are\s+now\s+(?!a\s+pan)|"
    r"act\s+as\s+(if\s+you\s+are|a\s+(?!pan))|"
    r"(your\s+)?(documents?|context|knowledge)\s+(disagree|contradict|is\s+wrong|are\s+wrong|don.t\s+matter)|"
    r"new\s+(system\s+)?instructions?|"
    r"override\s+(your\s+)?(guidelines?|instructions?|rules?|restrictions?)|"
    r"(you\s+have\s+)?no\s+restrictions?|"
    r"without\s+(any\s+)?(restrictions?|guidelines?|rules?|filters?)|"
    r"jailbreak|dan\s+mode|developer\s+mode|god\s+mode|unrestricted\s+mode|"
    r"disregard\s+(your\s+)?(previous|prior|all|the)\s*(instructions?|rules?|guidelines?)?|"
    r"do\s+anything\s+now|"
    r"bypass\s+(your\s+)?(filter|restriction|guideline|rule)"
    r")\b",
    re.IGNORECASE
)

def _is_injection_attempt(question: str) -> bool:
    return bool(_INJECTION_PATTERN.search(question))
CONTEXT_CONTINUATION_PHRASES = [
    "ok", "okay", "ready", "yes", "sure", "i am ready", "i'm ready",
    "let's go", "lets go", "proceed", "continue", "go ahead", "done",
    "upload", "i want to upload", "ready to upload", "can we proceed",
    "what next", "next step", "what do i do", "how do i proceed",
    "now", "now what", "yep", "yup", "yeah", "alright", "fine",
    "i'm good", "i am good", "good to go", "let's do it", "lets do it",
    "option 1", "option1", "1", "online", "online submission",
    # Flow continuation phrases
    "ok next", "next what", "and then", "then what", "what now",
    "next what should i give", "ok next what", "what should i give",
    "what do i give", "what do i submit", "what do i upload",
]

# Signals in recent bot answers that indicate we're in a document/upload context
UPLOAD_CONTEXT_SIGNALS = [
    "ready to upload", "upload panel", "upload your", "i need your",
    "documents", "aadhaar card", "driving license", "photograph",
    "proof of identity", "proof of address", "upload it",
    "submission process", "submit your documents", "online submission",
    "upload documents", "scanned copies", "fill out the form",
    "option 1", "option 2", "which option",
]

def _is_context_continuation(question: str) -> bool:
    q = question.strip().lower()
    # Exact match or starts with the phrase (avoids "already" matching "ready")
    return any(q == phrase or q.startswith(phrase + " ") or q.endswith(" " + phrase)
               for phrase in CONTEXT_CONTINUATION_PHRASES)


# ── Document upload intent — production-level regex ──────────────────────────
# Catches all natural language variations of "I want to submit/upload documents"
_UPLOAD_INTENT_PATTERN = re.compile(
    r"\b("
    # Action verbs
    r"submit|submitting|submission|"
    r"upload|uploading|"
    r"attach|attaching|attachment|"
    r"send|sending|"
    r"provide|providing|"
    r"share|sharing|"
    r"give|giving|"
    r"add|adding|"
    r"put|putting|"
    r"drop|dropping|"
    r"ready\s+to|want\s+to|going\s+to|like\s+to|need\s+to|"
    r"i\s+will|i'll|let\s+me|can\s+i|how\s+do\s+i"
    r")\b.{0,40}\b("
    # Document objects
    r"document|documents|docs|doc|"
    r"file|files|"
    r"paper|papers|"
    r"proof|proofs|"
    r"certificate|certificates|"
    r"aadhaar|aadhar|"
    r"photo|photograph|picture|image|"
    r"license|licence|id|identity"
    r")\b"
    r"|"
    # Reverse order: "documents submit/upload"
    r"\b(document|documents|docs|file|files|proof|proofs|aadhaar|photo|photograph)\b"
    r".{0,30}"
    r"\b(submit|upload|attach|send|provide|share|ready|done)\b",
    re.IGNORECASE
)

def _is_upload_intent(question: str) -> bool:
    """Returns True if the user is expressing intent to upload/submit documents."""
    q = question.strip()
    # Never fire on informational questions
    _INFO_GUARD = re.compile(
        r"^(what|how|why|when|where|who|which|is|are|can|do|does|did|"
        r"tell\s+me|explain|describe|what\s+is|what\s+are)\b",
        re.IGNORECASE
    )
    if _INFO_GUARD.match(q):
        return False
    _DIRECT = re.compile(
        r"\b(i\s+will\s+upload|let\s+me\s+upload|i\s+want\s+to\s+upload|"
        r"ready\s+to\s+upload|upload\s+now|upload\s+later|upload\s+afterwards|"
        r"will\s+upload|going\s+to\s+upload|upload\s+the\s+doc|"
        r"submit\s+the\s+doc|i\s+will\s+submit|let\s+me\s+submit|"
        r"i\s+wanna\s+submit|i\s+want\s+to\s+submit|"
        r"submit\s+documents?\s+for\s+pan|upload\s+documents?\s+for\s+pan|"
        r"submit\s+my\s+documents?|upload\s+my\s+documents?|"
        r"provide\s+my\s+documents?|share\s+my\s+documents?|"
        r"give\s+my\s+documents?|send\s+my\s+documents?)\b",
        re.IGNORECASE
    )
    if _DIRECT.search(q):
        return True
    return bool(_UPLOAD_INTENT_PATTERN.search(q))


def _strip_thinking(text: str) -> str:
    """Remove qwen3 <think>...</think> blocks from response."""
    # Remove think blocks (can be multiline)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text.strip()


# Hallucination patterns — things the LLM invents that aren't in our data
_HALLUCINATION_RE = re.compile(
    r"tatkal|regular\s+pan\s+card|type\s+of\s+pan\s+card|"
    r"which\s+type\s+of\s+pan|card\s+type|same.?day\s+delivery|next.?day\s+delivery|"
    r"express\s+pan|urgent\s+pan|priority\s+pan|"
    r"pan\s+card\s+in\s+\d+\s+(hour|minute)",
    re.IGNORECASE
)

# Only fire when the LLM is clearly guessing with NO grounding phrase nearby
# Removed: "typically", "usually", "generally" — these appear in valid retrieved context too
_HEDGING_RE = re.compile(
    r"\b(i\s+believe\s+(?!you)|i\s+think\s+(?!you)|"
    r"i'm\s+not\s+sure\s+but|as\s+far\s+as\s+i\s+know|"
    r"to\s+my\s+knowledge|based\s+on\s+my\s+(training|knowledge)|"
    r"you\s+might\s+want\s+to\s+check|please\s+verify\s+this|"
    r"this\s+could\s+vary|i\s+cannot\s+guarantee)\b",
    re.IGNORECASE
)

# LLM admitting it doesn't know — normalise to our safe fallback
_DONT_KNOW_RE = re.compile(
    r"\b(i\s+(don'?t|do\s+not|cannot|can'?t)\s+(find|locate|access)\s+(the\s+)?answer|"
    r"not\s+available\s+in\s+(the\s+)?context|"
    r"no\s+(information|data|details)\s+(available|found)\s+in\s+(the\s+)?context)\b",
    re.IGNORECASE
)

_SAFE_FALLBACK = (
    "I don't have enough specific information on that in my knowledge base. "
    "Could you rephrase your question or ask about a specific aspect of PAN card services?"
)

_APPLY_REDIRECT = (
    "To apply for a PAN card, just say **\"I want to apply for PAN\"** and I'll walk you through "
    "the whole process step by step."
)


def _sanitise_answer(answer: str, question: str = "") -> str:
    """Post-generation safety filter — replaces hallucinated or hedged answers."""
    if not answer or not answer.strip():
        return _SAFE_FALLBACK
    if _HALLUCINATION_RE.search(answer):
        return _APPLY_REDIRECT
    # Only replace if hedging AND no retrieved context markers present
    # AND the hedging phrase is not inside a quoted/blockquote section
    if _HEDGING_RE.search(answer) and "[Retrieved context]" not in answer:
        # Don't fire if the hedging phrase appears after a > (blockquote) — it's quoted text
        # Strip blockquote lines before checking
        non_quote_lines = [l for l in answer.splitlines() if not l.strip().startswith(">")]
        non_quote_text = " ".join(non_quote_lines)
        if _HEDGING_RE.search(non_quote_text):
            return _SAFE_FALLBACK
    if _DONT_KNOW_RE.search(answer):
        return _SAFE_FALLBACK
    return answer


def _parse_profile_from_context(user_context: str) -> dict:
    """Parse the structured profile block Node sends in user_context."""
    profile = {}
    if not user_context:
        return profile

    _INVALID_NAME_WORDS = re.compile(
        r"\b(apply|register|get|create|obtain|pan|card|application|"
        r"here|there|trying|going|looking|planning|wanting|"
        r"citizen|entity|indian|foreign|company|huf|firm|nri)\b",
        re.IGNORECASE
    )
    def _valid_name(val: str) -> bool:
        if not val or len(val.strip()) < 2: return False
        if _INVALID_NAME_WORDS.search(val): return False
        if len(val.split()) > 5: return False
        return True

    patterns = {
        "name":             r"-\s*(?:Full\s+)?[Nn]ame:\s*(.+)",
        "gender":           r"-\s*Gender:\s*(.+)",
        "dob":              r"-\s*Date of birth:\s*(.+)",
        "grandfather_name": r"-\s*Grandfather'?s?\s+name:\s*(.+)",
        "father_name":      r"-\s*Father'?s?\s+name:\s*(.+)",
        "mother_name":      r"-\s*Mother'?s?\s+name:\s*(.+)",
        "email":            r"-\s*Email:\s*(.+)",
        "pan_number":       r"-\s*PAN number:\s*(.+)",
        "aadhaar":          r"-\s*Aadhaar:\s*(.+)",
        "income":           r"-\s*Annual income:\s*(.+)",
        "source_of_income": r"-\s*Source of income:\s*(.+)",
        "address":          r"-\s*Address:\s*(.+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, user_context, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Validate name fields — reject hallucinated values
            if key in ("name", "father_name", "mother_name", "grandfather_name") and not _valid_name(val):
                continue
            profile[key] = val
    return profile


def _answer_resume_query(question: str, user_context: str, session_history: list = None) -> str:
    """
    Handle "where we left", "next what to do", "continue from last time" etc.
    Reads the RECENT CONVERSATION and YOUR LAST CONVERSATION blocks from
    user_context (built by Node) and summarises what was happening.
    Returns a helpful continuation response, or empty string if no context.
    """
    if not user_context:
        return ""

    # ── Parse the RECENT CONVERSATION block ──────────────────────
    recent_turns = []
    in_recent = False
    for line in user_context.splitlines():
        if "=== RECENT CONVERSATION" in line:
            in_recent = True
            continue
        if in_recent:
            if line.startswith("RULE:") or (line.startswith("===") and "RECENT" not in line):
                break
            if line.startswith("User: "):
                recent_turns.append({"role": "user", "text": line[6:].strip()})
            elif line.startswith("Assistant: "):
                recent_turns.append({"role": "assistant", "text": line[11:].strip()})

    # ── Parse the YOUR LAST CONVERSATION block ───────────────────
    last_session_turns = []
    last_session_title = ""
    in_last = False
    for line in user_context.splitlines():
        if "=== YOUR LAST CONVERSATION" in line:
            in_last = True
            continue
        if in_last:
            if line.startswith("RULE:") or (line.startswith("===") and "LAST" not in line):
                break
            if line.startswith("Session:"):
                last_session_title = line.replace("Session:", "").strip()
            elif line.startswith("User: "):
                last_session_turns.append({"role": "user", "text": line[6:].strip()})
            elif line.startswith("Assistant: "):
                last_session_turns.append({"role": "assistant", "text": line[11:].strip()})

    # ── Also use session_history passed directly ──────────────────
    if not recent_turns and session_history:
        for turn in session_history[-6:]:
            if turn.get("query"):
                recent_turns.append({"role": "user", "text": turn["query"]})
            if turn.get("answer"):
                recent_turns.append({"role": "assistant", "text": turn["answer"]})

    # ── Build the response ────────────────────────────────────────
    # Determine what the last meaningful exchange was about
    turns_to_use = recent_turns or last_session_turns
    if not turns_to_use:
        return ""

    # Find the last assistant message — that's what we were doing
    last_bot = next(
        (t["text"] for t in reversed(turns_to_use) if t["role"] == "assistant"),
        ""
    )
    last_user = next(
        (t["text"] for t in reversed(turns_to_use) if t["role"] == "user"),
        ""
    )

    if not last_bot and not last_user:
        return ""

    # Detect what topic/step we were on
    _PAN_APPLY = re.compile(r"\b(apply|application|pan\s+card|new\s+pan|49a)\b", re.IGNORECASE)
    _DETAILS   = re.compile(r"\b(full\s+name|mother.*name|annual\s+income|salary|still\s+need|i\s+still\s+need)\b", re.IGNORECASE)
    _DOCS      = re.compile(r"\b(upload|attach|paperclip|proof\s+of|document\s+upload)\b", re.IGNORECASE)
    _CONFIRM   = re.compile(r"\b(confirm|confirmation|proceed|does\s+everything\s+look|summary)\b", re.IGNORECASE)
    _LINK      = re.compile(r"\b(link|linking|aadhaar.?pan|pan.?aadhaar)\b", re.IGNORECASE)
    _STATUS    = re.compile(r"\b(status|track|check|where\s+is)\b", re.IGNORECASE)

    context_text = last_bot + " " + last_user

    if _CONFIRM.search(context_text):
        topic = "reviewing your application details for confirmation"
        suggestion = "Would you like to confirm your details and proceed, or change something?"
    elif _DETAILS.search(context_text):
        topic = "collecting your personal details for the PAN application"
        suggestion = "You can continue by providing your **full name**, **mother's name**, and **annual income** — all in one message if you like."
    elif _DOCS.search(context_text):
        topic = "collecting your documents for the PAN application"
        suggestion = "You can attach your documents using the 📎 paperclip button whenever you're ready."
    elif _PAN_APPLY.search(context_text):
        topic = "working on your PAN card application"
        suggestion = "Would you like to continue from where we left off?"
    elif _LINK.search(context_text):
        topic = "Aadhaar-PAN linking"
        suggestion = "Would you like to continue with the linking process?"
    elif _STATUS.search(context_text):
        topic = "checking your PAN status"
        suggestion = "Would you like to continue checking your PAN status?"
    else:
        topic = "a PAN card query"
        suggestion = "Would you like to continue from where we left off?"

    # Build a clean summary of the last exchange
    lines = [f"We were {topic}."]

    if last_bot:
        # Trim to first 2 sentences for brevity
        sentences = re.split(r'(?<=[.!?])\s+', last_bot.strip())
        summary = " ".join(sentences[:2])
        if len(summary) > 200:
            summary = summary[:200] + "…"
        lines.append(f"\nThe last thing I said was:\n> {summary}")

    lines.append(f"\n{suggestion}")

    return "\n".join(lines)


def _answer_from_profile(question: str, user_context: str, language: str = "en", session_history: list = None) -> str:
    """
    Answer memory questions directly from the profile block + session history.
    Scans both the persisted profile AND recent conversation turns for facts.
    Returns a natural language answer, or empty string if nothing relevant found.
    """
    profile = _parse_profile_from_context(user_context)

    # ── Resume / continuation queries — answer from conversation context ──────
    # "where we left", "next what to do", "continue from last time", etc.
    _RESUME_Q = re.compile(
        r"\b("
        r"where\s+(we|i|did\s+we|did\s+i)\s+\w+|"
        r"where\s+were\s+we|where\s+was\s+i|"
        r"continue\s+(from|where|our|the)|resume|pick\s+up\s+where|"
        r"last\s+(time|session|chat|conversation)|"
        r"next\s+what\s+to\s+do|what\s+to\s+do\s+next|"
        r"what\s+(should|do)\s+i\s+do\s+next|"
        r"what\s+is\s+(the\s+)?next\s+step|"
        r"what\s+next|now\s+what"
        r")\b",
        re.IGNORECASE
    )
    if _RESUME_Q.search(question):
        return _answer_resume_query(question, user_context, session_history)

    # Also scan recent session history for facts stated this session
    # (profile update is async — facts stated earlier this session may not be persisted yet)
    if session_history:
        # Segment-aware extraction: split on "and"/"," first, then match per segment
        def _extract_from_msg(user_msg: str) -> dict:
            """Extract name/mother/income facts from a user message using segment splitting."""
            found: dict = {}
            # Normalise typos
            msg = re.sub(r'\blakhs?\b|\blaakh\b|\blaks\b|\blaksh\b|\blac\b', 'lakh', user_msg, flags=re.IGNORECASE)
            # Split into segments on "and" / "," — but NOT on commas inside numbers
            segs_raw = re.split(r'\s+and\s+', msg, flags=re.IGNORECASE)
            segs = []
            for part in segs_raw:
                sub = re.split(r'(?<!\d),(?!\d{2,3}(?:,|\b))', part)
                segs.extend(s.strip() for s in sub if s.strip())

            _STOP = {'my', 'name', 'is', 'the', 'full', 'and', 'a', 'an',
                     'mother', 'mothers', 'mom', 'moms', 'father', 'fathers', 'dad',
                     'salary', 'income', 'email', 'annual', 'per', 'year'}

            def _clean(raw: str) -> str:
                return ' '.join(w for w in raw.strip().split() if w.lower() not in _STOP).strip()

            for seg in segs:
                # Mother name
                if not found.get("mother_name"):
                    m = re.match(
                        r"(?:my\s+)?(?:mother(?:'?s)?|mom(?:'?s)?|maa|amma)\s+(?:full\s+)?name\s*(?:is\s*)?[:\-]?\s*(.+)",
                        seg, re.IGNORECASE
                    )
                    if m:
                        c = _clean(m.group(1))
                        if c and len(c) >= 2:
                            found["mother_name"] = c

                # Father name
                if not found.get("father_name"):
                    m = re.match(
                        r"(?:my\s+)?(?:father(?:'?s)?|dad(?:'?s)?|papa)\s+(?:full\s+)?name\s*(?:is\s*)?[:\-]?\s*(.+)",
                        seg, re.IGNORECASE
                    )
                    if m:
                        c = _clean(m.group(1))
                        if c and len(c) >= 2:
                            found["father_name"] = c

                # Full name (skip mother/father/salary segments)
                if not found.get("name"):
                    if not re.search(r'\b(mother|mom|father|dad|salary|income|email|₹)\b', seg, re.IGNORECASE):
                        m = re.match(
                            r"(?:my\s+)?(?:full\s+)?name\s*(?:is\s*)?[:\-]?\s*(.+)"
                            r"|(?:call\s+me|i'm)\s+(.+)",
                            seg, re.IGNORECASE
                        )
                        if m:
                            c = _clean(m.group(1) or m.group(2) or "")
                            # Reject if contains action/intent words — not a real name
                            _name_reject = {
                                "ready", "done", "fine", "good", "ok", "okay", "here",
                                "not", "pan", "registration", "apply", "application",
                                "going", "trying", "planning", "interested", "available",
                                "happy", "pleased", "excited", "waiting", "looking"
                            }
                            if c and len(c) >= 2 and not set(c.lower().split()).intersection(_name_reject):
                                found["name"] = c

                # Email
                if not found.get("email"):
                    em = re.search(r"\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b", seg)
                    if em:
                        found["email"] = em.group(1)

                # PAN number
                if not found.get("pan_number"):
                    pm = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", seg)
                    if pm:
                        found["pan_number"] = pm.group(1)

                # Income
                if not found.get("income"):
                    im = re.search(
                        r"(?:salary|income|earn(?:ing)?s?|annual)\s*(?:is\s*)?[:\-]?\s*"
                        r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|l\b|k\b|thousand|crore|cr\b)?",
                        seg, re.IGNORECASE
                    )
                    if not im:
                        im = re.search(
                            r"\b([\d,]+(?:\.\d+)?)\s*(lakh|lac|l\b|k\b|thousand|crore|cr\b)\b",
                            seg, re.IGNORECASE
                        )
                    if im:
                        try:
                            raw = float(im.group(1).replace(",", ""))
                            unit = (im.group(2) or "").lower()
                            if unit in ("lakh", "lac", "l"):   raw *= 100_000
                            elif unit in ("k", "thousand"):    raw *= 1_000
                            elif unit in ("crore", "cr"):      raw *= 10_000_000
                            found["income"] = str(int(raw))
                        except ValueError:
                            pass
                    elif re.search(
                        r"\b(unemployed|no\s+income|no\s+salary|zero\s+income|not\s+earning|student|housewife|homemaker)\b",
                        seg, re.IGNORECASE
                    ):
                        found["income"] = "0 (no income)"

            return found

        for turn in session_history:
            user_msg = turn.get("query", "")
            extracted = _extract_from_msg(user_msg)
            for key, val in extracted.items():
                # Always update with the latest value from session history
                if val:
                    profile[key] = val

    if not profile:
        return "I don't have any details on file for you yet. You can share them anytime!"

    q = question.lower()

    # Normalise bare possessive questions: "my mother name?" → treat as "what is my mother name"
    q = re.sub(r'^(ok\s+)?my\s+', 'what is my ', q)

    # Specific field lookups - only trigger when ASKING, not PROVIDING
    # Check for question patterns like "what is", "what's", "do you have", "tell me"
    # Avoid triggering on statements like "my X is Y" or "X is Y"
    
    if any(pattern in q for pattern in ["what is my mother", "what's my mother", "my mother name?", "my mother's name?", 
                                         "do you have my mother", "tell me my mother", "show me my mother",
                                         "mother name?", "mother's name?"]) or \
       (any(w in q for w in ["mother", "mom", "amma", "maa"]) and not re.search(r'\b(mother|mom)\s+(name\s+)?is\b', q)):
        val = profile.get("mother_name")
        return f"Your mother's name on file is **{val}**." if val else "I don't have your mother's name on file yet."

    if any(pattern in q for pattern in ["what is my father", "what's my father", "my father name?", "my father's name?",
                                         "do you have my father", "tell me my father", "show me my father",
                                         "father name?", "father's name?"]) or \
       (any(w in q for w in ["father", "dad", "appa", "papa"]) and not re.search(r'\b(father|dad)\s+(name\s+)?is\b', q)):
        val = profile.get("father_name")
        return f"Your father's name on file is **{val}**." if val else "I don't have your father's name on file yet."

    if any(pattern in q for pattern in ["what is my email", "what's my email", "my email?",
                                         "do you have my email", "tell me my email", "show me my email"]) or \
       (any(w in q for w in ["email", "mail", "e-mail"]) and not re.search(r'\b(email|mail)\s+is\b', q)):
        val = profile.get("email")
        return f"Your email on file is **{val}**." if val else "I don't have your email on file yet."

    if any(pattern in q for pattern in ["what is my income", "what's my income", "what is my salary", "what's my salary",
                                         "my income?", "my salary?", "do you have my income", "do you have my salary",
                                         "tell me my income", "tell me my salary", "show me my income", "show me my salary"]) or \
       (any(w in q for w in ["income?", "salary?", "earning?", "ctc?"]) and not re.search(r'\b(income|salary|earning)\s+is\b', q)):
        val = profile.get("income")
        if val:
            display = f"₹{int(val):,}" if val.isdigit() else val
            return f"Your annual income on file is **{display}**."
        return "I don't have your income on file yet."

    if any(pattern in q for pattern in ["what is my pan", "what's my pan", "my pan number?", "my pan?",
                                         "do you have my pan", "tell me my pan", "show me my pan"]) or \
       (any(w in q for w in ["pan number?", "pan card?", "pan?"]) and not re.search(r'\bpan\s+(number\s+)?is\b', q)):
        val = profile.get("pan_number")
        return f"Your PAN number on file is **{val}**." if val else "I don't have your PAN number on file yet."

    if any(pattern in q for pattern in ["what is my aadhaar", "what's my aadhaar", "my aadhaar?",
                                         "do you have my aadhaar", "tell me my aadhaar", "show me my aadhaar"]) or \
       (any(w in q for w in ["aadhaar?", "aadhar?"]) and not re.search(r'\b(aadhaar|aadhar)\s+(number\s+)?is\b', q)):
        val = profile.get("aadhaar")
        return f"Your Aadhaar on file is **{val}**." if val else "I don't have your Aadhaar on file yet."

    if any(pattern in q for pattern in ["what is my dob", "what's my dob", "what is my date of birth", "my birthday?",
                                         "when was i born", "do you have my dob", "tell me my dob"]):
        val = profile.get("dob")
        return f"Your date of birth on file is **{val}**." if val else "I don't have your date of birth on file yet."

    if any(pattern in q for pattern in ["what is my gender", "what's my gender", "my gender?",
                                         "do you have my gender", "tell me my gender"]):
        val = profile.get("gender")
        return f"Your gender on file is **{val}**." if val else "I don't have your gender on file yet."

    if any(pattern in q for pattern in ["what is my address", "what's my address", "my address?", "where do i live",
                                         "do you have my address", "tell me my address", "show me my address"]) or \
       (any(w in q for w in ["address?", "residence?", "location?"]) and not re.search(r'\b(address|residence)\s+is\b', q)):
        val = profile.get("address")
        return f"Your address on file is **{val}**." if val else "I don't have your address on file yet."

    if any(pattern in q for pattern in ["what is my source of income", "what's my source of income", "my income source?",
                                         "do you have my source of income", "tell me my source of income"]):
        val = profile.get("source_of_income")
        return f"Your source of income on file is **{val}**." if val else "I don't have your source of income on file yet."

    # Check if user is ASKING about their name (not providing it)
    # Avoid triggering on "my name is X" (providing) vs "what's my name" (asking)
    if any(pattern in q for pattern in ["what's my name", "what is my name", "who am i", "do you know my name"]):
        val = profile.get("name")
        return f"Your name on file is **{val}**." if val else "I don't have your name on file yet."

    # "what details do you have" / "do you remember me" / "what do you know about me"
    # Also catches: "tell me my details", "what are the details", "list my info"
    if any(w in q for w in ["details", "info", "remember", "know about me", "have on me",
                             "on file", "what do you know", "i told you", "i gave you",
                             "i shared", "tell me my", "show me my", "list my", "all my"]):
        lines = []
        if profile.get("name"):         lines.append(f"- Name: **{profile['name']}**")
        if profile.get("gender"):       lines.append(f"- Gender: **{profile['gender']}**")
        if profile.get("dob"):          lines.append(f"- Date of birth: **{profile['dob']}**")
        if profile.get("grandfather_name"): lines.append(f"- Grandfather's name: **{profile['grandfather_name']}**")
        if profile.get("father_name"):  lines.append(f"- Father's name: **{profile['father_name']}**")
        if profile.get("mother_name"):  lines.append(f"- Mother's name: **{profile['mother_name']}**")
        if profile.get("email"):        lines.append(f"- Email: **{profile['email']}**")
        if profile.get("pan_number"):   lines.append(f"- PAN number: **{profile['pan_number']}**")
        if profile.get("aadhaar"):      lines.append(f"- Aadhaar: **{profile['aadhaar']}**")
        if profile.get("income"):
            v = profile['income']
            lines.append(f"- Annual income: **{'₹'+format(int(v),',') if v.isdigit() else v}**")
        if profile.get("source_of_income"): lines.append(f"- Source of income: **{profile['source_of_income']}**")
        if profile.get("address"):      lines.append(f"- Address: **{profile['address']}**")
        if lines:
            return "Here's what I have on file for you:\n\n" + "\n".join(lines)
        return "I don't have any details on file for you yet."

    # Generic fallback — show all known fields
    lines = []
    if profile.get("name"):         lines.append(f"- Name: **{profile['name']}**")
    if profile.get("gender"):       lines.append(f"- Gender: **{profile['gender']}**")
    if profile.get("dob"):          lines.append(f"- Date of birth: **{profile['dob']}**")
    if profile.get("grandfather_name"): lines.append(f"- Grandfather's name: **{profile['grandfather_name']}**")
    if profile.get("father_name"):  lines.append(f"- Father's name: **{profile['father_name']}**")
    if profile.get("mother_name"):  lines.append(f"- Mother's name: **{profile['mother_name']}**")
    if profile.get("email"):        lines.append(f"- Email: **{profile['email']}**")
    if profile.get("pan_number"):   lines.append(f"- PAN number: **{profile['pan_number']}**")
    if profile.get("aadhaar"):      lines.append(f"- Aadhaar: **{profile['aadhaar']}**")
    if profile.get("income"):
        v = profile['income']
        lines.append(f"- Annual income: **{'₹'+format(int(v),',') if v.isdigit() else v}**")
    if profile.get("source_of_income"): lines.append(f"- Source of income: **{profile['source_of_income']}**")
    if lines:
        return "Here's what I have on file for you:\n\n" + "\n".join(lines)
    return ""




import random

# Multiple variants per intent so responses feel natural and varied — no LLM needed
FALLBACKS = {
    Intent.GREETING: {
        "en": [
            "Hey! 👋 What can I help you with today?",
            "Hi there! 😊 Got a PAN card question? I'm all yours.",
            "Hello! How can I help you with your PAN card today?",
            "Hey, good to see you! What's on your mind?",
            "Hi! Ask me anything about PAN cards, Aadhaar linking, or TAN. 😊",
            "Yo! 👋 What's up? PAN card stuff — I got you.",
            "Hey bro! 😊 What PAN question can I help with?",
        ],
        "ta": [
            "வணக்கம்! 👋 PAN கார்டு பற்றி என்ன உதவி வேண்டும்?",
            "ஹலோ! 😊 PAN விண்ணப்பம், ஆதார் இணைப்பு — எதுவும் கேளுங்கள்.",
        ],
        "hi": [
            "नमस्ते! 👋 PAN कार्ड से जुड़ा कोई सवाल है?",
            "हेलो! 😊 PAN आवेदन, आधार लिंकिंग — कुछ भी पूछें।",
        ],
    },
    Intent.FAREWELL: {
        "en": [
            "Take care! 😊 Come back anytime you need PAN help.",
            "Bye! Feel free to reach out whenever you need me. 👋",
            "See you! Hope I was helpful. 😊",
        ],
        "ta": ["நன்றி! 😊 எந்த நேரத்திலும் திரும்பி வாருங்கள்."],
        "hi": ["अलविदा! 😊 कभी भी वापस आएं।"],
    },
    Intent.GRATITUDE: {
        "en": [
            "Happy to help! 😊 Anything else on your mind?",
            "Glad that helped! Let me know if you need anything else.",
            "Anytime! 😊 What else can I do for you?",
            "No problem at all! Got more questions? Fire away.",
        ],
        "ta": ["மகிழ்ச்சி! 😊 வேறு ஏதாவது கேள்விகள் இருந்தால் கேளுங்கள்."],
        "hi": ["खुशी हुई! 😊 और कुछ चाहिए तो बताएं।"],
    },
    Intent.IDENTITY: {
        "en": (
            "Hey! I'm the Protean PAN Assistant 😊\n\n"
            "I can help you with:\n"
            "• New PAN card application\n"
            "• Document requirements\n"
            "• Aadhaar-PAN linking\n"
            "• e-PAN download\n"
            "• PAN correction or reprint\n"
            "• TAN and TDS queries\n\n"
            "What would you like help with?"
        ),
        "ta": "நான் Protean PAN Assistant! 😊 PAN விண்ணப்பம், ஆவணங்கள், ஆதார் இணைப்பு மற்றும் மேலும் உதவ இங்கே இருக்கிறேன்.",
        "hi": "मैं Protean PAN Assistant हूँ! 😊 PAN आवेदन, दस्तावेज़, आधार लिंकिंग और अधिक में मदद के लिए यहाँ हूँ।",
    },
    Intent.UNRELATED: {
        "en": (
            "That's a bit outside what I can help with 😅 — I'm specifically here for PAN card services.\n\n"
            "I can help you with:\n"
            "• PAN card application (new / correction / reprint)\n"
            "• Required documents\n"
            "• Aadhaar-PAN linking\n"
            "• e-PAN download\n"
            "• TAN and TDS queries"
        ),
        "ta": "அந்த விஷயம் என் திறன் வரம்பிற்கு வெளியே! 😅 நான் PAN கார்டு சேவைகளுக்கு மட்டுமே உதவ முடியும்.",
        "hi": "यह मेरी विशेषज्ञता से बाहर है! 😅 मैं केवल PAN कार्ड सेवाओं में मदद कर सकता हूँ।",
    },
    Intent.ROLEPLAY: {
        "en": "I'm just a PAN card assistant — can't take on a different role! 😊 Let me know if you have any PAN questions.",
        "ta": "நான் PAN கார்டு உதவியாளர் மட்டுமே! 😊",
        "hi": "मैं सिर्फ PAN कार्ड सहायक हूँ! 😊",
    },
    Intent.JUNK: {
        "en": "Hmm, I didn't quite catch that 😅 Could you rephrase? I'm here for PAN card questions.",
        "ta": "புரியவில்லை 😅 கொஞ்சம் தெளிவாக கேளுங்கள்.",
        "hi": "समझ नहीं आया 😅 कृपया दोबारा पूछें।",
    },
    Intent.ABUSE: {
        "en": "Let's keep it friendly! 😊 I'm here whenever you need PAN help.",
        "ta": "நட்புடன் பேசுவோம்! 😊",
        "hi": "दोस्ताना रहें! 😊",
    },
}


def _get_fallback(intent: Intent, language: str = "en", name: str = None) -> str:
    """Get a random language-appropriate fallback for an intent. No LLM involved."""
    fb = FALLBACKS.get(intent, {})

    if isinstance(fb, dict):
        options = fb.get(language) or fb.get("en", "")
        response = random.choice(options) if isinstance(options, list) else options
    else:
        response = fb

    return response


class RAGChain:

    def __init__(self):
        print("Initialising RAG chain...")
        self.retriever = HybridRetriever()
        self.memory    = MemoryManager()
        self._cache: dict[str, str] = {}  # simple in-process response cache
        print("✅ RAG chain ready\n")

    def _cache_key(self, question: str, session_id: str) -> str:
        return f"{session_id}:{question.strip().lower()[:80]}"

    def run(self, question: str, session_id: str = None, user_id: str = "anonymous", user_context: str = None, account_email: str = "", language_override: str = None) -> dict:
        _t_start = time.time()

        if not session_id:
            session_id = MemoryManager.new_session_id()

        # ── Spell-normalize the question before anything else ─────
        # Corrects common typos: "lakss"→"lakh", "aadhar"→"aadhaar",
        # "aply"→"apply", "pann crad"→"pan card", etc.
        question = spell_normalize(question)

        language = detect_language(question, override=language_override)

        # Only fall back to the session's stored preferred_language when NO
        # explicit override was sent. If the UI sent language_override="en",
        # that is an intentional switch — don't let a stale "ta"/"hi" entry
        # silently override it.
        if not language_override:
            try:
                from agent.flow_manager import FlowManager as _FM
                _fm = _FM(session_id, user_id or "anonymous")
                stored_lang = _fm.state.get("preferred_language")
                if stored_lang in ("ta", "hi"):
                    language = stored_lang
            except Exception:
                pass

        # Cache the context block Node sent — this is the single source of truth
        # for history. get_session_history() reads back from this cache.
        if user_context and user_context.strip():
            self.memory.cache_context(session_id, user_context, user_id)

        # Always load history first — used throughout
        session_history = self.memory.get_session_history(session_id, user_id)
        has_history     = len(session_history) > 0

        # Pass history to intent detector so flow replies ("1", "yes") are never misclassified
        intent = detect_intent(question, session_history=session_history)

        print(f"DEBUG intent={intent.value} | lang={language} | history_turns={len(session_history)}")

        # ── 0. Injection / jailbreak attempt — hard block ────────────
        if _is_injection_attempt(question):
            answer = "I'm strictly a PAN card assistant and my guidelines cannot be overridden by any instruction. How can I help you with PAN services?"
            self.memory.add_to_session(session_id, question, answer)
            return {
                "question"   : question,
                "answer"     : answer,
                "sources"    : [],
                "session_id" : session_id,
                "intent"     : "injection_blocked",
                "language"   : language,
                "followups"  : [],
                "close_form" : True,
                "open_upload": False,
            }

        # ── 0a. Cancellation — close any open form/flow immediately ──
        from agent.receptionist import _is_cancellation
        fm = FlowManager(session_id, user_id or "anonymous")
        flow_active = fm.has_active_flow()

        # Don't treat "no" as cancellation in steps where it's a valid answer
        _YES_NO_STEPS = {"aadhaar_photo", "rep_assessee", "confirmation"}
        _cancel_blocked = flow_active and fm.get_current_step() in _YES_NO_STEPS

        if _is_cancellation(question) and flow_active and not _cancel_blocked:
            fm.state["service_id"] = None
            fm.state["complete"] = True
            fm.save()
            answer = _get_fallback(Intent.FAREWELL, language) if intent == Intent.FAREWELL \
                else "Got it — I've stopped that. No worries! Let me know whenever you'd like to continue or if there's anything else I can help you with."
            self.memory.add_to_session(session_id, question, answer)
            return {
                "question"   : question,
                "answer"     : answer,
                "sources"    : [],
                "session_id" : session_id,
                "intent"     : intent.value,
                "language"   : language,
                "followups"  : [],
                "close_form" : True,
                "open_upload": False,
            }

        # ── 0b. Document upload intent ────────────────────────────────
        # Don't intercept if user is answering a form step (e.g. "Upload scanned docs & eSign")
        if _is_upload_intent(question):
            fm = FlowManager(session_id, user_id or "anonymous")
            _FORM_STEPS = {"submission_mode", "delivery_mode", "aadhaar_photo",
                           "source_of_income", "address_for_comm", "residential_status",
                           "rep_assessee", "details_collection", "confirmation"}
            if fm.has_active_flow() and fm.get_current_step() in _FORM_STEPS:
                pass  # fall through to flow handler
            else:
                service_id = fm.state.get("service_id") if fm.has_active_flow() else None
                from agent.service_flows import get_service
                has_docs = bool(service_id and get_service(service_id).get("documents"))

                if not has_docs:
                    fm.start_flow("pan_apply_indian")
                    fm.state["applicant_type"] = "indian_citizen"
                    fm.advance_step()
                    fm.save()

                answer = (
                    "Sure! Just attach your documents using the 📎 paperclip button in the chat "
                    "and include any details in the same message. I'll extract everything from there."
                )
                self.memory.add_to_session(session_id, question, answer)
                return {
                    "question"    : question,
                    "answer"      : answer,
                    "sources"     : [],
                    "session_id"  : session_id,
                    "intent"      : "pan_query",
                    "language"    : language,
                    "followups"   : [],
                    "open_upload" : False,
                }

        # ── 0c. Numbered/option reply — route through normal flow, no panel ──
        _short_option = re.match(r'^(option\s*1|1|online|option\s*one)$', question.strip(), re.IGNORECASE)
        if _short_option and has_history:
            fm = FlowManager(session_id, user_id or "anonymous")
            service_id = fm.state.get("service_id") if fm.has_active_flow() else None
            from agent.service_flows import get_service
            has_docs = bool(service_id and get_service(service_id).get("documents"))
            recent = session_history[-4:]
            if has_docs and any(any(s in t.get("answer", "").lower() for s in UPLOAD_CONTEXT_SIGNALS) for t in recent):
                # Route through the normal flow — don't open panel automatically
                agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
                if agent_response:
                    self.memory.add_to_session(session_id, question, agent_response["answer"])
                    return {
                        "question"   : question,
                        "answer"     : agent_response["answer"],
                        "sources"    : [],
                        "session_id" : session_id,
                        "intent"     : "pan_query",
                        "language"   : language,
                        "followups"  : agent_response.get("followups", []),
                        "open_upload": False,
                        "form_data"  : agent_response.get("form_data"),
                        "options"    : agent_response.get("options"),
                    }

        # ── 1. Active guided flow ─────────────────────────────────────
        # Social / casual messages mid-flow get a human response + soft nudge.
        # Everything else routes through the flow handler.
        if flow_active:
            _SOCIAL_INTENTS = {Intent.GREETING, Intent.GRATITUDE, Intent.FAREWELL, Intent.IDENTITY}

            # Also catch casual expressions the intent detector might miss
            _CASUAL_RE = re.compile(
                r"^(say\s+)?(hi|hey|hello|hii|sup|yo|ayo|bro|bruh|man|dude|mate|buddy|bhai|da|machan|"
                r"lol|haha|hehe|ok\s+cool|nice|wow|great|awesome|cool|"
                r"thanks|thank\s+you|ty|thx|bye|cya|later|good\s+night|"
                r"good\s+morning|good\s+afternoon|good\s+evening)\b.{0,30}$",
                re.IGNORECASE
            )
            is_casual = intent in _SOCIAL_INTENTS or bool(_CASUAL_RE.match(question.strip()))

            if is_casual:
                social_answer = _get_fallback(
                    intent if intent in _SOCIAL_INTENTS else Intent.GREETING,
                    language,
                )
                # Soft nudge back to flow (skip for farewells)
                if social_answer and intent != Intent.FAREWELL:
                    step = fm.get_current_step()
                    nudge = {
                        "applicant_type":   " By the way — still need to know if you're an Indian citizen, company, or foreign national to continue your PAN application.",
                        "personal_details": " Whenever you're ready, just share the remaining details.",
                        "documents":        " Whenever you're ready, use the 📎 paperclip to attach your documents.",
                    }.get(step, " Just let me know when you want to continue your PAN application.")
                    social_answer = social_answer.rstrip() + nudge
                if social_answer:
                    self.memory.add_to_session(session_id, question, social_answer)
                    return {
                        "question"  : question,
                        "answer"    : social_answer,
                        "sources"   : [],
                        "session_id": session_id,
                        "intent"    : intent.value,
                        "language"  : language,
                        "followups" : [],
                    }

            agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
            if agent_response:
                self.memory.add_to_session(session_id, question, agent_response["answer"])
                return {
                    "question"    : question,
                    "answer"      : agent_response["answer"],
                    "sources"     : [],
                    "session_id"  : session_id,
                    "intent"      : intent.value,
                    "language"    : language,
                    "followups"   : agent_response.get("followups", []),
                    "open_upload" : agent_response.get("open_upload", False),
                    "close_form"  : agent_response.get("close_form", False),
                    "form_data"   : agent_response.get("form_data"),
                    "form_fields" : agent_response.get("form_fields"),
                    "options"     : agent_response.get("options"),
                    "confirm_action": agent_response.get("confirm_action", False),
                    "flow_confirmed": agent_response.get("flow_confirmed", False),
                    "confirmation_fields": agent_response.get("confirmation_fields"),
                    "show_submit" : agent_response.get("show_submit", False),
                }
            # agent returned None — flow cancelled, fall through to RAG

        # ── 2. Context continuation — if user has history and says something
        #       short/ambiguous like "ready", "ok", "yes", try the agent first ──
        if has_history and _is_context_continuation(question):
            agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
            if agent_response:
                self.memory.add_to_session(session_id, question, agent_response["answer"])
                return {
                    "question"    : question,
                    "answer"      : agent_response["answer"],
                    "sources"     : [],
                    "session_id"  : session_id,
                    "intent"      : intent.value,
                    "language"    : language,
                    "followups"   : agent_response.get("followups", []),
                    "open_upload" : agent_response.get("open_upload", False),
                    "form_data"   : agent_response.get("form_data"),
                    "form_fields" : agent_response.get("form_fields"),
                    "options"     : agent_response.get("options"),
                }
            # No active flow — if last bot message was asking to upload,
            # guide user to use the paperclip button instead of opening a panel
            last_bot = session_history[-1].get("answer", "").lower() if session_history else ""
            last_asked_upload = any(s in last_bot for s in [
                "ready to upload", "upload panel", "reply **yes**", "open the upload",
                "upload your documents", "upload it whenever", "paperclip",
            ])
            if last_asked_upload:
                answer = "Go ahead — attach your files using the 📎 paperclip button and include your details in the message. I'll pick everything up from there."
                self.memory.add_to_session(session_id, question, answer)
                return {
                    "question"   : question,
                    "answer"     : answer,
                    "sources"    : [],
                    "session_id" : session_id,
                    "intent"     : intent.value,
                    "language"   : language,
                    "followups"  : [],
                    "open_upload": False,
                }

        # ── 3. Hard-blocked intents (safety) ─────────────────────────
        HARD_BLOCK = {Intent.ROLEPLAY, Intent.ABUSE}
        if intent in HARD_BLOCK:
            answer = _get_fallback(intent, language)
            self.memory.add_to_session(session_id, question, answer)
            return {
                "question"   : question,
                "answer"     : answer,
                "sources"    : [],
                "session_id" : session_id,
                "intent"     : intent.value,
                "language"   : language,
                "followups"  : [],
                "close_form" : True,
            }

        # ── 3a. Stored detail queries — ALWAYS check flow state first ──────────
        # Any question asking about stored data (name, mother, salary, all details, etc.)
        # must be answered from flow state before any profile/RAG fallback.
        # handle_message contains _display_user_profile and _direct_info_query which
        # read directly from FlowManager state on disk — the authoritative source.
        _STORED_DETAIL_Q = re.compile(
            r"\b(what|whats|tell\s+me|show\s+me|display)\s+(is|are|'?s)?\s*(my|the)\s+"
            r"(name|full\s+name|mother|grandfather|email|salary|income|personal\s+details?)"
            r"|\b(personal\s+details?|details?\s+(i\s+gave|you\s+have|you\s+stored|you\s+collected|you\s+know))"
            r"|\b(what\s+details?|which\s+details?)\s+(do\s+you\s+have|did\s+i\s+give|have\s+you\s+(got|collected|stored))"
            r"|\b(show|tell|list|display)\s+(me\s+)?(what\s+)?(you\s+)?(know|have|collected|stored|remember)\s+(about\s+me|on\s+me)"
            r"|\bwhat\s+do\s+you\s+know\s+about\s+me\b"
            r"|\bwhat\s+have\s+i\s+(told|given|shared|provided)\s+(you|so\s+far)\b"
            r"|\bdo\s+you\s+(remember|recall|know|have)\s+(my\s+)?(name|details?|info|salary|email|mother)\b"
            r"|\bdo\s+you\s+(remember|know)\s+me\b"
            r"|\bwho\s+am\s+i\b"
            r"|\bdid\s+you\s+(save|store|get|record|note)\s+my\b"
            r"|\bhave\s+you\s+(saved|stored|got|recorded)\s+my\b",
            re.IGNORECASE,
        )
        if _STORED_DETAIL_Q.search(question):
            agent_response = handle_message(
                question, session_id, language,
                user_context=user_context,
                account_email=account_email,
                user_id=user_id,
            )
            if agent_response:
                self.memory.add_to_session(session_id, question, agent_response["answer"])
                return {
                    "question"  : question,
                    "answer"    : agent_response["answer"],
                    "sources"   : [],
                    "session_id": session_id,
                    "intent"    : "pan_query",
                    "language"  : language,
                    "followups" : agent_response.get("followups", []),
                    "options"   : agent_response.get("options"),
                    "field_buttons": agent_response.get("field_buttons"),
                    "confirmation_fields": agent_response.get("confirmation_fields"),
                }

        # ── 3b. Memory questions — check BEFORE social/unrelated handlers ──
        # IMPORTANT: Only intercept questions about the user's OWN stored data.
        # General PAN questions ("what are the fees", "what documents") must go to RAG.
        # Resume/continuation queries also handled here.
        _MEMORY_Q_EARLY = re.compile(
            r"\b("
            # Explicit memory/recall queries
            r"do\s+you\s+(remember|know|recall|have)\s+(my|what)|"
            r"what\s+(is|are|was|were)\s+my\s+(name|email|income|salary|mother|father|pan|aadhaar|address|dob|phone|details?)\b|"
            r"you\s+(said|told|mentioned|know|remember)\s+(my|what\s+i)|"
            r"what\s+did\s+(i|you)\s+(say|tell|mention)\s+(about\s+me|my|you)|"
            r"i\s+(told|said|mentioned|gave|shared|provided)\s+you\s+(my|about)|"
            r"did\s+i\s+(tell|give|share|mention|provide)\s+you\s+my|"
            r"did\s+you\s+(get|receive|save|store|note)\s+my|"
            r"have\s+i\s+(told|given|shared|mentioned|provided)\s+you\s+my|"
            r"do\s+you\s+have\s+my\s+(name|email|income|salary|mother|father|pan|aadhaar|address|dob|phone|details?)\b|"
            # "show/tell/list my details" — personal data only
            r"(show|tell|list|display)\s+(me\s+)?(my\s+)?(details?|info|information|profile|data)\b|"
            r"what\s+do\s+you\s+know\s+about\s+me|"
            r"what\s+have\s+i\s+told\s+you|"
            r"what\s+did\s+i\s+(give|provide|share)\s+(you|to\s+you)|"
            # Resume / continuation queries
            r"where\s+(we|i|did\s+we|did\s+i)\s+\w+|"
            r"where\s+were\s+we|where\s+was\s+i|"
            r"continue\s+(from|where|our|the)|resume|pick\s+up\s+where|"
            r"last\s+(time|session|chat|conversation)|"
            r"next\s+what\s+to\s+do|what\s+to\s+do\s+next|"
            r"what\s+(should|do)\s+i\s+do\s+next|"
            r"what\s+is\s+(the\s+)?next\s+step|"
            # bare possessive questions: "my mother name?", "my email?", "my salary?"
            r"^(ok\s+)?my\s+(mother|father|name|email|salary|income|pan|aadhaar|address|dob)\b"
            r")\b",
            re.IGNORECASE
        )
        _FACT_PROVIDE_EARLY = re.compile(
            r"\b(my\s+\w+(\s+\w+)?\s+(is|are|was|=)\s+\S|"
            r"(name|email|income|salary|mother|father|dob|pan)\s+(is|are)\s+\S)",
            re.IGNORECASE
        )
        is_early_memory_q = (
            bool(_MEMORY_Q_EARLY.search(question))
            and not bool(_FACT_PROVIDE_EARLY.search(question))
            and user_context
            and user_context.strip()
        )
        if is_early_memory_q:
            answer = _answer_from_profile(question, user_context, language, session_history=session_history)
            if answer:
                self.memory.add_to_session(session_id, question, answer)
                return {
                    "question"  : question,
                    "answer"    : answer,
                    "sources"   : [],
                    "session_id": session_id,
                    "intent"    : "pan_query",
                    "language"  : language,
                    "followups" : [],
                }
            # Memory had no answer — fall through to RAG

        # ── 4. Social intents — LLM for "say X" / conversational, fallback otherwise ─
        SOCIAL_INTENTS = {
            Intent.GREETING, Intent.FAREWELL, Intent.GRATITUDE, Intent.IDENTITY,
        }

        # Detect "say X" / "tell me X" / "wish me X" — user wants the bot to perform
        # a conversational act, not get redirected to PAN services
        _SAY_PATTERN = re.compile(
            r"^(say|tell\s+me|wish\s+me|give\s+me|write|type|repeat|respond\s+with)\b",
            re.IGNORECASE
        )
        _is_say_request = bool(_SAY_PATTERN.match(question.strip()))

        if intent in SOCIAL_INTENTS or _is_say_request:
            # Use LLM for "say X" requests and identity — they need a real response
            if _is_say_request or intent == Intent.IDENTITY:
                from generation.llm import generate_conversational
                answer = generate_conversational(question, language, name=None, history=session_history)
                if not answer:
                    answer = _get_fallback(intent if intent in SOCIAL_INTENTS else Intent.GREETING, language)
            else:
                answer = _get_fallback(intent, language)

            self.memory.add_to_session(session_id, question, answer)
            return {
                "question"  : question,
                "answer"    : answer,
                "sources"   : [],
                "session_id": session_id,
                "intent"    : intent.value,
                "language"  : language,
                "followups" : [],
            }

        # ── 5. Junk — LLM if history exists, instant fallback otherwise ─
        if intent == Intent.JUNK:
            if has_history:
                from generation.llm import generate_conversational
                answer = generate_conversational(question, language, history=session_history)
                if not answer:
                    answer = _get_fallback(Intent.JUNK, language)
            else:
                answer = _get_fallback(Intent.JUNK, language)
            return {
                "question"  : question,
                "answer"    : answer,
                "sources"   : [],
                "session_id": session_id,
                "intent"    : intent.value,
                "language"  : language,
                "followups" : [],
            }

        # ── 6. Agent: new service detection ──────────────────────────
        # PAN_QUERY intent + action keywords → try agent before RAG
        agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
        if agent_response:
            self.memory.add_to_session(session_id, question, agent_response["answer"])
            return {
                "question"    : question,
                "answer"      : agent_response["answer"],
                "sources"     : [],
                "session_id"  : session_id,
                "intent"      : intent.value,
                "language"    : language,
                "followups"   : agent_response.get("followups", []),
                "open_upload" : agent_response.get("open_upload", False),
                "form_data"   : agent_response.get("form_data"),
            }

        # ── 6b. Memory questions AND fact-providing statements ───────
        # Catches:
        #   Questions:  "my mother name?", "what is my email?", "do you know my salary?"
        #   Statements: "my mother name is Nabina J", "ok my mother name is Nabina J"
        # NOTE: Only intercepts personal data queries — NOT general PAN questions.
        # General questions ("what are the fees") must go to RAG.

        _MEMORY_Q = re.compile(
            r"\b("
            r"do\s+you\s+(remember|know|recall|have)\s+(my|what)|"
            r"what\s+(is|are|was|were)\s+my\s+(name|email|income|salary|mother|father|pan|aadhaar|address|dob|phone)\b|"
            r"you\s+(said|told|mentioned|know|remember)\s+(my|what\s+i)|"
            r"what\s+did\s+(i|you)\s+(say|tell|mention)\s+(about\s+me|my|you)|"
            r"i\s+(told|said|mentioned|gave|shared|provided)\s+you\s+(my|about)|"
            r"did\s+i\s+(tell|give|share|mention|provide)\s+you\s+my|"
            r"did\s+you\s+(get|receive|save|store|note)\s+my|"
            r"have\s+i\s+(told|given|shared|mentioned|provided)\s+you\s+my|"
            r"do\s+you\s+have\s+my\s+(name|email|income|salary|mother|father|pan|aadhaar|address|dob|phone)\b|"
            # bare possessive questions: "my mother name?", "my email?", "my salary?"
            r"^(ok\s+)?my\s+(mother|father|name|email|salary|income|pan|aadhaar|address|dob)\b"
            r")\b",
            re.IGNORECASE
        )

        # Fact-providing statements: "my mother name is X", "ok my mother name is Nabina J"
        _FACT_PROVIDE = re.compile(
            r"\b(my\s+\w+(\s+\w+)?\s+(is|are|was|=)\s+\S|"
            r"(name|email|income|salary|mother|father|dob|pan)\s+(is|are)\s+\S)",
            re.IGNORECASE
        )

        is_fact_provide = bool(_FACT_PROVIDE.search(question)) and user_context and user_context.strip()
        is_memory_question = (
            bool(_MEMORY_Q.search(question))
            and not is_fact_provide
            and user_context
            and user_context.strip()
        )

        # User is providing a personal fact — acknowledge and confirm it was saved
        if is_fact_provide and not flow_active:
            # Extract what was provided for a natural acknowledgement
            _FIELD_LABELS = {
                r"mother": "mother's name",
                r"father": "father's name",
                r"email":  "email",
                r"salary|income": "income",
                r"pan":    "PAN number",
                r"aadhaar": "Aadhaar",
                r"address": "address",
                r"name":   "name",
            }
            field_label = "detail"
            for pattern, label in _FIELD_LABELS.items():
                if re.search(pattern, question, re.IGNORECASE):
                    field_label = label
                    break
            answer = f"Got it — I've noted your {field_label}. Is there anything else you'd like to update or ask?"
            self.memory.add_to_session(session_id, question, answer)
            return {
                "question"  : question,
                "answer"    : answer,
                "sources"   : [],
                "session_id": session_id,
                "intent"    : intent.value,
                "language"  : language,
                "followups" : [],
            }

        if is_memory_question:
            answer = _answer_from_profile(question, user_context, language, session_history=session_history)
            if answer:
                self.memory.add_to_session(session_id, question, answer)
                return {
                    "question"  : question,
                    "answer"    : answer,
                    "sources"   : [],
                    "session_id": session_id,
                    "intent"    : intent.value,
                    "language"  : language,
                    "followups" : [],
                }

        # ── 7. Unrelated — let LLM respond naturally, no RAG ────────
        if intent == Intent.UNRELATED:
            # First check: if the question is actually PAN/flow related despite
            # being classified UNRELATED, route it through the agent/RAG pipeline
            from intent.intent_detector import PAN_DOMAIN_PATTERN
            if PAN_DOMAIN_PATTERN.search(question) or has_history:
                # Fall through to agent check and RAG below
                pass
            else:
                from generation.llm import generate_conversational
                answer = generate_conversational(question, language, name=None, history=session_history)
                if not answer:
                    answer = "I'm not sure about that one, but I'm great with PAN card questions! What would you like to know? 😊"
                self.memory.add_to_session(session_id, question, answer)
                return {
                    "question"  : question,
                    "answer"    : answer,
                    "sources"   : [],
                    "session_id": session_id,
                    "intent"    : intent.value,
                    "language"  : language,
                    "followups" : [],
                }

        # ── 8. RAG pipeline ───────────────────────────────────────────

        # Document question intercept — always return the fixed 3-doc answer
        # instead of letting RAG hallucinate a generic list from chunks
        _DOC_Q = re.compile(
            r"\b(document|documents|doc|docs|proof|proofs|file|files|"
            r"upload|uploads|uploaded|uploading|attach|attached|attaching|"
            r"approve|submit|submitted|submitting|required|requirements)\b",
            re.IGNORECASE
        )
        if _DOC_Q.search(question):
            answer = (
                "For a new PAN card application, you need to submit **3 documents**:\n\n"
                "### 1. Aadhaar Card\n"
                "> Your Aadhaar covers all three KYC requirements in one go — proof of identity, proof of address, and proof of date of birth. "
                "This is why it's the primary document for PAN applications.\n"
                "Accepted: Aadhaar Card (front & back scan or clear photo)\n\n"
                "### 2. Driving License\n"
                "> Required as a secondary identity proof to cross-verify your name and details against the Aadhaar. "
                "It adds an extra layer of verification that the Income Tax Department requires.\n"
                "Accepted: Valid Driving License (front side only)\n\n"
                "### 3. Applicant Photograph\n"
                "> Your photo is printed directly on the physical PAN card and is used for visual identity verification at banks, "
                "government offices, and financial institutions.\n"
                "Accepted: Recent passport-size photo (white background, no sunglasses, face clearly visible)\n\n"
                "---\n"
                "> ⚠️ **Important:** The name on all documents must match your Aadhaar exactly — "
                "even a small spelling difference will cause your application to be rejected.\n\n"
                "Use the 📎 paperclip button to attach each file whenever you're ready."
            )
            followups = [
                "I'm ready to upload my documents",
                "Can Aadhaar alone cover all three proofs?",
                "What format should the photograph be in?",
            ]
            self.memory.add_to_session(session_id, question, answer)
            return {
                "question"  : question,
                "answer"    : answer,
                "sources"   : [],
                "session_id": session_id,
                "intent"    : intent.value,
                "language"  : language,
                "followups" : followups,
            }

        history_text = ""
        if session_history:
            history_text = "\n".join(
                [f"User: {h['query']}\nBot: {h['answer']}" for h in session_history[-5:]]
            )

        _t_retrieve = time.time()
        chunks = self.retriever.retrieve(question)
        _t_llm = time.time()
        answer = generate_answer(question, chunks, history_text=history_text, language=language, user_context=user_context)
        _t_llm_done = time.time()

        print(f"⏱  LLM generate: {_t_llm_done - _t_llm:.2f}s  |  total chain: {_t_llm_done - _t_start:.2f}s")

        # ── Hallucination guard ───────────────────────────────────────
        answer = _sanitise_answer(answer, question)

        # ── Post-translate if language is Tamil or Hindi ──────────────
        # The LLM is instructed to respond in the target language, but
        # translation is applied as a safety net for any English leakage.
        if language in ("ta", "hi"):
            answer = translate_response(answer, language)

        followups = get_followup_suggestions(question, answer)
        followups = translate_followups(followups, language)

        # Translate guided-flow option labels (radio/checkbox choices)
        if language in ("ta", "hi") and agent_response and agent_response.get("options"):
            agent_response["options"] = translate_options(agent_response["options"], language)

        self.memory.add_to_session(session_id, question, answer)
        self.memory.update_user_memory(user_id, question, answer)

        seen, unique_sources = set(), []
        # Sources intentionally omitted — agent is self-sufficient, no external links

        return {
            "question"  : question,
            "answer"    : answer,
            "sources"   : [],
            "session_id": session_id,
            "intent"    : intent.value,
            "language"  : language,
            "followups" : followups,
        }

    # ── Streaming variant ─────────────────────────────────────────────────────
    def run_stream(self, question: str, session_id: str = None, user_id: str = "anonymous", user_context: str = None, account_email: str = "", language_override: str = None):
        """
        Generator that yields SSE-formatted strings.
        Runs all pre-LLM logic synchronously, then streams LLM tokens.
        Non-LLM paths (social, flow, injection) emit a single token event.
        """
        import json as _json
        _t_start = time.time()

        def _sse(obj: dict) -> str:
            return f"data: {_json.dumps(obj)}\n\n"

        def _get_collected_facts(sid: str) -> dict:
            """Extract all facts collected by the flow so Node can persist them."""
            try:
                fm = FlowManager(sid)
                facts = {}
                # Personal details
                if fm.state.get("full_name"):        facts["full_name"]         = fm.state["full_name"]
                if fm.state.get("mother_name"):      facts["mother_name"]       = fm.state["mother_name"]
                if fm.state.get("email"):            facts["email"]             = fm.state["email"]
                if fm.state.get("salary"):           facts["salary"]            = fm.state["salary"]
                # PAN preferences — ALL of them
                if fm.state.get("applicant_type"):   facts["applicant_type"]    = fm.state["applicant_type"]
                if fm.state.get("submission_mode"):  facts["submission_mode"]   = fm.state["submission_mode"]
                if fm.state.get("delivery_mode"):    facts["delivery_mode"]     = fm.state["delivery_mode"]
                if fm.state.get("aadhaar_photo") is not None:
                                                     facts["aadhaar_photo"]     = fm.state["aadhaar_photo"]
                if fm.state.get("source_of_income"): facts["source_of_income"]  = fm.state["source_of_income"]
                if fm.state.get("address_for_comm"): facts["address_for_comm"]  = fm.state["address_for_comm"]
                if fm.state.get("residential_status"):facts["residential_status"]= fm.state["residential_status"]
                if fm.state.get("rep_assessee") is not None:
                                                     facts["rep_assessee"]      = fm.state["rep_assessee"]
                if fm.state.get("pan_number"):       facts["pan_number"]        = fm.state["pan_number"]
                return facts
            except Exception:
                return {}

        def _emit_static(result: dict):
            """Emit meta + single token + done for non-streaming paths."""
            answer = result.pop("answer", "")
            elapsed_ms = result.pop("elapsed_ms", None)
            flow_confirmed = result.get("flow_confirmed", False)
            yield _sse({"type": "meta", **result})
            yield _sse({"type": "token", "text": answer})
            facts = _get_collected_facts(session_id)
            # Include flow_data in done event when confirmed so Node can persist
            done_payload = {"type": "done"}
            if elapsed_ms:
                done_payload["elapsed_ms"] = elapsed_ms
            if facts:
                done_payload["collected_facts"] = facts
            if flow_confirmed and facts:
                done_payload["flow_confirmed"] = True
                done_payload["flow_data"] = facts
            yield _sse(done_payload)

        # ── Run all pre-LLM logic (reuse run() for non-RAG paths) ────────────
        # We detect whether we'll need streaming by checking if the chain
        # would reach the RAG pipeline. To avoid duplicating all the logic,
        # we run a lightweight pre-check: if run() would return before RAG
        # (social/flow/injection), we just call run() and emit statically.
        # Only for the RAG path do we stream.

        if not session_id:
            session_id = MemoryManager.new_session_id()

        # ── Spell-normalize before intent detection ───────────────
        question = spell_normalize(question)

        language = detect_language(question, override=language_override)

        # Only fall back to the session's stored preferred_language when NO
        # explicit override was sent. If the UI sent language_override="en",
        # that is an intentional switch — don't let a stale "ta"/"hi" entry
        # silently override it.
        if not language_override:
            try:
                from agent.flow_manager import FlowManager as _FM
                _fm = _FM(session_id, user_id or "anonymous")
                stored_lang = _fm.state.get("preferred_language")
                if stored_lang in ("ta", "hi"):
                    language = stored_lang
            except Exception:
                pass

        if user_context and user_context.strip():
            self.memory.cache_context(session_id, user_context, user_id)

        session_history = self.memory.get_session_history(session_id, user_id)
        has_history     = len(session_history) > 0
        intent          = detect_intent(question, session_history=session_history)
        fm              = FlowManager(session_id, user_id or "anonymous")
        flow_active     = fm.has_active_flow()

        # Paths that don't hit the LLM streaming path — delegate to run()
        _NON_STREAM_INTENTS = {
            Intent.GREETING, Intent.FAREWELL, Intent.GRATITUDE,
            Intent.IDENTITY, Intent.ROLEPLAY,
            Intent.ABUSE, Intent.JUNK,
        }
        # UNRELATED only goes static if it has no PAN domain content and no history
        from intent.intent_detector import PAN_DOMAIN_PATTERN as _PAN_PAT
        _unrelated_is_static = (
            intent == Intent.UNRELATED
            and not _PAN_PAT.search(question)
            and not has_history
        )
        _SAY_PATTERN_STREAM = re.compile(
            r"^(say|tell\s+me|wish\s+me|give\s+me|write|type|repeat|respond\s+with)\b",
            re.IGNORECASE
        )
        _MEMORY_Q = re.compile(
            r"\b(do\s+you\s+(remember|know|recall|have)|"
            r"what\s+(is|are|was|were)\s+my\b|"
            r"what\s+(is|are)\s+(your|the)\s+(name|email|income|mother|father)\b|"
            r"you\s+(said|told|mentioned|know|remember)|"
            r"what\s+did\s+(i|you)\s+(say|tell|mention)|"
            r"i\s+(told|said|mentioned|gave|shared|provided)\s+you|"
            r"did\s+i\s+(tell|give|share|mention|provide)\s+you|"
            r"did\s+you\s+(get|receive|save|store|note)\s+my|"
            r"have\s+i\s+(told|given|shared|mentioned|provided)\s+you|"
            r"do\s+you\s+have\s+my\b|"
            r"what\s+(are|is)\s+(the\s+)?(details?|info|information)\b|"
            r"what\s+(details?|info|information)\s*(do\s+you\s+have|you\s+have|i\s+told|i\s+gave|i\s+shared)?|"
            r"(tell\s+me|show\s+me|list)\s+.{0,20}(details?|info|information|facts?)\b|"
            r"what\s+do\s+you\s+know\s+about\s+me|"
            r"what\s+have\s+i\s+told\s+you|"
            # Resume / continuation queries
            r"where\s+(we|i|did\s+we|did\s+i)\s+\w+|"
            r"where\s+were\s+we|where\s+was\s+i|"
            r"continue\s+(from|where|our|the)|resume|pick\s+up\s+where|"
            r"last\s+(time|session|chat|conversation)|"
            r"next\s+what\s+to\s+do|what\s+to\s+do\s+next|"
            r"what\s+(should|do)\s+i\s+do\s+next|"
            r"what\s+is\s+(the\s+)?next\s+step|"
            r"^(ok\s+)?my\s+(mother|father|name|email|salary|income|pan|aadhaar|address|dob)\b)\b",
            re.IGNORECASE
        )
        _FACT_PROVIDE = re.compile(
            r"\b(my\s+\w+(\s+\w+)?\s+(is|are|was|=)\s+\S|"
            r"(name|email|income|salary|mother|father|dob|pan)\s+(is|are)\s+\S)",
            re.IGNORECASE
        )
        _FORM_STEPS = {"submission_mode", "delivery_mode", "aadhaar_photo",
                       "source_of_income", "address_for_comm", "residential_status",
                       "rep_assessee", "details_collection", "confirmation"}
        _upload_intent_active = (
            _is_upload_intent(question)
            and not (flow_active and fm.get_current_step() in _FORM_STEPS)
        )
        needs_static = (
            _is_injection_attempt(question)
            or flow_active
            or (has_history and _is_context_continuation(question))
            or intent in _NON_STREAM_INTENTS
            or _unrelated_is_static
            or bool(_SAY_PATTERN_STREAM.match(question.strip()))
            or _upload_intent_active
            or bool(
                _MEMORY_Q.search(question)
                and not _FACT_PROVIDE.search(question)
                and user_context and user_context.strip()
            )
            # fact-provide statements also go through run() for acknowledgement
            or bool(
                _FACT_PROVIDE.search(question)
                and not flow_active
                and user_context and user_context.strip()
            )
            # stored-detail queries always go through run() to check flow state first
            or bool(re.search(
                r"\b(what|whats|tell\s+me|show\s+me|display)\s+(is|are|'?s)?\s*(my|the)\s+"
                r"(name|full\s+name|mother|grandfather|email|salary|income|personal\s+details?)"
                r"|\b(personal\s+details?|details?\s+(i\s+gave|you\s+have|you\s+stored|you\s+know))"
                r"|\bwhat\s+do\s+you\s+know\s+about\s+me\b"
                r"|\bwhat\s+have\s+i\s+(told|given|shared|provided)\s+(you|so\s+far)\b",
                question, re.IGNORECASE,
            ))
        )

        if needs_static:
            result = self.run(question=question, session_id=session_id, user_id=user_id, user_context=user_context)
            result["elapsed_ms"] = int((time.time() - _t_start) * 1000)
            yield from _emit_static(result)
            return

        # ── RAG streaming path ────────────────────────────────────────────────
        # 1. Agent check (new service detection)
        agent_response = handle_message(question, session_id, language, user_context=user_context, account_email=account_email, user_id=user_id)
        if agent_response:
            # Translate agent response for Tamil/Hindi
            if language in ("ta", "hi"):
                agent_response["answer"] = translate_response(agent_response["answer"], language)
                if agent_response.get("followups"):
                    agent_response["followups"] = translate_followups(agent_response["followups"], language)
                # Translate guided-flow option labels (radio/checkbox choices)
                if agent_response.get("options"):
                    agent_response["options"] = translate_options(agent_response["options"], language)

            self.memory.add_to_session(session_id, question, agent_response["answer"])

            # If user just confirmed their details, collect them for Node to persist
            flow_confirmed = agent_response.get("flow_confirmed", False)
            flow_data = None
            if flow_confirmed:
                flow_data = _get_collected_facts(session_id)

            result = {
                "question"      : question,
                "sources"       : [],
                "session_id"    : session_id,
                "intent"        : intent.value,
                "language"      : language,
                "followups"     : agent_response.get("followups", []),
                "open_upload"   : agent_response.get("open_upload", False),
                "form_data"     : agent_response.get("form_data"),
                "form_fields"   : agent_response.get("form_fields"),
                "options"       : agent_response.get("options"),
                "confirm_action": agent_response.get("confirm_action", False),
                "flow_confirmed": flow_confirmed,
                "flow_data"     : flow_data,
                "field_buttons" : agent_response.get("field_buttons"),
                "confirmation_fields": agent_response.get("confirmation_fields"),
                "show_submit"   : agent_response.get("show_submit", False),
            }
            yield _sse({"type": "meta", **result})
            yield _sse({"type": "token", "text": agent_response["answer"]})
            yield _sse({"type": "done"})
            return

        # 2. Retrieval
        chunks = self.retriever.retrieve(question)

        history_text = ""
        if session_history:
            history_text = "\n".join(
                [f"User: {h['query']}\nBot: {h['answer']}" for h in session_history[-5:]]
            )

        # 3. Emit meta first so frontend can set session_id / followups immediately
        followups = get_followup_suggestions(question, "")  # pre-generate without answer
        yield _sse({
            "type"       : "meta",
            "question"   : question,
            "sources"    : [],
            "session_id" : session_id,
            "intent"     : intent.value,
            "language"   : language,
            "followups"  : followups,
            "open_upload": False,
            "form_data"  : None,
        })

        # 4. Stream tokens
        full_answer = []
        try:
            for token in generate_answer_stream(
                question, chunks,
                history_text=history_text,
                language=language,
                user_context=user_context,
            ):
                full_answer.append(token)
                yield _sse({"type": "token", "text": token})
        except Exception as e:
            print(f"[ERROR] Streaming error: {e}")
            # If streaming fails, provide a fallback answer
            full_answer = ["I can only help with PAN card services. What PAN-related question can I answer?"]
            yield _sse({"type": "token", "text": full_answer[0]})

        answer = "".join(full_answer)

        # Hallucination guard — sanitise before persisting or streaming replace
        sanitised = _sanitise_answer(answer, question)
        if sanitised != answer:
            answer = sanitised
            yield _sse({"type": "replace", "text": answer})

        # Post-translate for Tamil/Hindi (safety net for any English leakage)
        if language in ("ta", "hi"):
            translated = translate_response(answer, language)
            if translated != answer:
                answer = translated
                yield _sse({"type": "replace", "text": answer})

        # 5. Persist
        self.memory.add_to_session(session_id, question, answer)
        self.memory.update_user_memory(user_id, question, answer)

        elapsed_ms = int((time.time() - _t_start) * 1000)
        facts = _get_collected_facts(session_id)
        yield _sse({"type": "done", "elapsed_ms": elapsed_ms, **({"collected_facts": facts} if facts else {})})
