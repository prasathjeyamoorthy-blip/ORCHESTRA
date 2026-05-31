"""
intent/spell_normalizer.py

Lightweight, zero-dependency spell normalizer for the PAN Assistant.

Strategy:
  1. Exact-match substitution table for the most common typos/variants
     (fast, deterministic, no model needed).
  2. Fuzzy word-level correction using difflib.SequenceMatcher as a
     fallback for words not in the table (only for domain keywords).

This runs on EVERY incoming message before intent detection, service
detection, and the RAG pipeline — so misspellings are corrected once
and all downstream logic sees clean text.

Design principles:
  - Never change proper nouns (names, PAN numbers, Aadhaar numbers).
  - Never change numbers or currency amounts.
  - Only correct words that are clearly domain keywords.
  - Fast: O(n) table lookup + O(k) fuzzy check on unknown words.
"""

import re
from difflib import SequenceMatcher

# ─────────────────────────────────────────────────────────────────────────────
# Exact substitution table
# Format: (regex_pattern, replacement)
# Sorted so longer/more-specific patterns come first.
# ─────────────────────────────────────────────────────────────────────────────
_EXACT_SUBS = [
    # ── PAN / document keywords ──────────────────────────────────
    (r'\bpann\b',           'pan'),
    (r'\bpan\s+crad\b',     'pan card'),
    (r'\bpan\s+cadr\b',     'pan card'),
    (r'\bpan\s+crd\b',      'pan card'),
    (r'\bpan\s+caard\b',    'pan card'),
    (r'\bpancard\b',        'pan card'),
    (r'\bpanno\b',          'pan number'),
    (r'\bpan\s+no\b',       'pan number'),
    (r'\baadhar\b',         'aadhaar'),
    (r'\badhaar\b',         'aadhaar'),
    (r'\baadhaaar\b',       'aadhaar'),
    (r'\badhaar\b',         'aadhaar'),
    (r'\baadhar\b',         'aadhaar'),
    (r'\badhaar\b',         'aadhaar'),
    (r'\baadharc\b',        'aadhaar card'),
    (r'\baadhaarcard\b',    'aadhaar card'),
    (r'\baadhaar\s+crad\b', 'aadhaar card'),

    # ── Apply / application ───────────────────────────────────────
    (r'\baply\b',           'apply'),
    (r'\bappply\b',         'apply'),
    (r'\bappley\b',         'apply'),
    (r'\bapplay\b',         'apply'),
    (r'\baplly\b',          'apply'),
    (r'\bapplyy\b',         'apply'),
    (r'\bapplu\b',          'apply'),
    (r'\bapli\b',           'apply'),
    (r'\baplying\b',        'applying'),
    (r'\bapplying\b',       'applying'),
    (r'\bapplication\b',    'application'),  # already correct, keep
    (r'\bapplicaton\b',     'application'),
    (r'\bapplicaiton\b',    'application'),
    (r'\bapplcation\b',     'application'),

    # ── Want / wanna ──────────────────────────────────────────────
    (r'\bwnat\b',           'want'),
    (r'\bwatn\b',           'want'),
    (r'\bwnna\b',           'wanna'),
    (r'\bwannt\b',          'want'),
    (r'\bwwant\b',          'want'),
    (r'\bwana\b',           'wanna'),

    # ── Link / linking ────────────────────────────────────────────
    (r'\blinkg\b',          'linking'),
    (r'\blinkin\b',         'linking'),
    (r'\blinkng\b',         'linking'),
    (r'\blinked\b',         'linked'),   # already correct
    (r'\blinkin\b',         'linking'),

    # ── Status / track ────────────────────────────────────────────
    (r'\bstatus\b',         'status'),   # already correct
    (r'\bstatuss\b',        'status'),
    (r'\bstauts\b',         'status'),
    (r'\bstaus\b',          'status'),
    (r'\btraking\b',        'tracking'),
    (r'\btracking\b',       'tracking'), # already correct
    (r'\btrck\b',           'track'),

    # ── Correction / update ───────────────────────────────────────
    (r'\bcorrction\b',      'correction'),
    (r'\bcorection\b',      'correction'),
    (r'\bcorrect\b',        'correct'),  # already correct
    (r'\bupdat\b',          'update'),
    (r'\bupadte\b',         'update'),
    (r'\bupdaet\b',         'update'),

    # ── Document ──────────────────────────────────────────────────
    (r'\bdocumnet\b',       'document'),
    (r'\bdocuemnt\b',       'document'),
    (r'\bdocumnt\b',        'document'),
    (r'\bdocumet\b',        'document'),
    (r'\bdocuments\b',      'documents'), # already correct
    (r'\bdocumnets\b',      'documents'),
    (r'\bdocuemnts\b',      'documents'),

    # ── Income / salary units ─────────────────────────────────────
    (r'\blakss\b',          'lakh'),
    (r'\blakhs\b',          'lakh'),
    (r'\blaksh\b',          'lakh'),
    (r'\blaks\b',           'lakh'),
    (r'\blaakh\b',          'lakh'),
    (r'\blac\b',            'lakh'),
    (r'\blacs\b',           'lakh'),
    (r'\bcrore\b',          'crore'),    # already correct
    (r'\bcrores\b',         'crore'),
    (r'\bcrroe\b',          'crore'),

    # ── Name / personal details ───────────────────────────────────
    (r'\bnaem\b',           'name'),
    (r'\bnme\b',            'name'),
    (r'\bnam\b',            'name'),
    (r'\bfull\s+naem\b',    'full name'),
    (r'\bmothre\b',         'mother'),
    (r'\bmoter\b',          'mother'),
    (r'\bmothr\b',          'mother'),
    (r'\bmuther\b',         'mother'),
    (r'\bfathre\b',         'father'),
    (r'\bfater\b',          'father'),
    (r'\bfathr\b',          'father'),

    # ── Email ─────────────────────────────────────────────────────
    (r'\bemali\b',          'email'),
    (r'\beamil\b',          'email'),
    (r'\bemial\b',          'email'),
    (r'\bemail\b',          'email'),    # already correct

    # ── Salary / income ───────────────────────────────────────────
    (r'\bslary\b',          'salary'),
    (r'\bsalry\b',          'salary'),
    (r'\bsalary\b',         'salary'),   # already correct
    (r'\bincme\b',          'income'),
    (r'\bincoe\b',          'income'),
    (r'\bincmoe\b',         'income'),

    # ── Reprint / duplicate ───────────────────────────────────────
    (r'\breprint\b',        'reprint'),  # already correct
    (r'\brepirnt\b',        'reprint'),
    (r'\brepint\b',         'reprint'),
    (r'\bduplcate\b',       'duplicate'),
    (r'\bduplicte\b',       'duplicate'),

    # ── Lost / misplaced ─────────────────────────────────────────
    (r'\blsot\b',           'lost'),
    (r'\blost\b',           'lost'),     # already correct
    (r'\bmisplaced\b',      'misplaced'), # already correct
    (r'\bmisplced\b',       'misplaced'),

    # ── Verify / verification ─────────────────────────────────────
    (r'\bverfy\b',          'verify'),
    (r'\bverifiy\b',        'verify'),
    (r'\bverificaton\b',    'verification'),
    (r'\bverificaiton\b',   'verification'),

    # ── Download / e-PAN ─────────────────────────────────────────
    (r'\bdownlod\b',        'download'),
    (r'\bdownlaod\b',       'download'),
    (r'\bepan\b',           'e-pan'),
    (r'\be\s+pan\b',        'e-pan'),

    # ── TDS / TAN ─────────────────────────────────────────────────
    (r'\btds\b',            'tds'),      # already correct
    (r'\btan\b',            'tan'),      # already correct
    (r'\btdss\b',           'tds'),
    (r'\btann\b',           'tan'),

    # ── Common chat typos ─────────────────────────────────────────
    (r'\bwht\b',            'what'),
    (r'\bwat\b',            'what'),
    (r'\bwhats\b',          "what's"),
    (r'\bhwo\b',            'how'),
    (r'\bhow\b',            'how'),      # already correct
    (r'\bplz\b',            'please'),
    (r'\bpls\b',            'please'),
    (r'\bplease\b',         'please'),   # already correct
    (r'\bhelp\s+me\b',      'help me'),  # already correct
    (r'\bhlep\b',           'help'),
    (r'\bhelp\b',           'help'),     # already correct
    (r'\bi\s+wanna\b',      'i want to'),
    (r'\bi\s+wana\b',       'i want to'),
    (r'\bi\s+wan\b',        'i want'),
    (r'\bgimme\b',          'give me'),
    (r'\bgiv\s+me\b',       'give me'),
]

# Compile all patterns once at module load
_COMPILED_SUBS = [
    (re.compile(pat, re.IGNORECASE), repl)
    for pat, repl in _EXACT_SUBS
]

# ─────────────────────────────────────────────────────────────────────────────
# Domain keyword list for fuzzy correction
# Only words in this list are candidates for fuzzy correction.
# This prevents the fuzzy corrector from mangling proper nouns or names.
# ─────────────────────────────────────────────────────────────────────────────
_DOMAIN_KEYWORDS = {
    'pan', 'aadhaar', 'aadhar', 'apply', 'application', 'link', 'linking',
    'status', 'track', 'correction', 'update', 'reprint', 'duplicate',
    'document', 'documents', 'verify', 'verification', 'download',
    'income', 'salary', 'lakh', 'crore', 'thousand',
    'name', 'email', 'mother', 'father', 'address', 'phone',
    'resident', 'residential', 'submission', 'delivery',
    'aadhaar', 'photograph', 'identity', 'proof',
    'register', 'registration', 'obtain', 'create',
    'lost', 'misplaced', 'damaged', 'stolen',
    'tds', 'tan', 'itr', 'gst', 'huf', 'nri',
}

# Words that should NEVER be fuzzy-corrected — common English words that
# happen to be similar to domain keywords
_COMMON_WORDS = {
    'linked', 'links', 'linking', 'linked', 'link',
    'is', 'it', 'in', 'if', 'as', 'at', 'an', 'am', 'be', 'by', 'do',
    'for', 'from', 'get', 'got', 'has', 'had', 'him', 'his', 'how',
    'its', 'let', 'may', 'me', 'my', 'no', 'not', 'now', 'of', 'on',
    'or', 'our', 'out', 'per', 'put', 'set', 'she', 'so', 'the', 'to',
    'too', 'up', 'us', 'was', 'we', 'who', 'why', 'will', 'with', 'yes',
    'you', 'your', 'are', 'and', 'but', 'can', 'did', 'has', 'have',
    'here', 'just', 'know', 'like', 'make', 'more', 'need', 'only',
    'over', 'same', 'some', 'than', 'that', 'them', 'then', 'they',
    'this', 'time', 'very', 'want', 'what', 'when', 'where', 'which',
    'while', 'would', 'about', 'after', 'again', 'also', 'back', 'been',
    'before', 'being', 'both', 'came', 'come', 'could', 'each', 'even',
    'find', 'first', 'give', 'good', 'great', 'help', 'high', 'into',
    'keep', 'last', 'left', 'long', 'look', 'made', 'many', 'most',
    'much', 'must', 'next', 'once', 'open', 'part', 'place', 'right',
    'said', 'send', 'show', 'side', 'since', 'still', 'such', 'sure',
    'take', 'tell', 'their', 'there', 'these', 'think', 'those', 'three',
    'through', 'under', 'until', 'upon', 'used', 'using', 'well', 'went',
    'were', 'whether', 'without', 'work', 'year', 'years',
}

# Words that should NEVER be fuzzy-corrected (proper nouns, numbers, etc.)
_PROTECTED_PATTERN = re.compile(
    r'^[A-Z]{5}[0-9]{4}[A-Z]$'   # PAN number
    r'|\d'                          # any number
    r'|@'                           # email address
    r'|^[A-Z][a-z]'                # Capitalized word (likely a name)
)


def _fuzzy_correct_word(word: str) -> str:
    """
    If `word` is close to a domain keyword (similarity ≥ 0.82),
    return the keyword. Otherwise return the word unchanged.
    Only fires for words 4+ characters long.
    """
    if len(word) < 4:
        return word
    if _PROTECTED_PATTERN.match(word):
        return word

    w = word.lower()

    # Skip common English words — they're not typos
    if w in _COMMON_WORDS:
        return word

    if w in _DOMAIN_KEYWORDS:
        return word  # already correct

    best_match = None
    best_score = 0.0
    for kw in _DOMAIN_KEYWORDS:
        # Only compare words of similar length (±2 chars) for speed
        if abs(len(w) - len(kw)) > 3:
            continue
        score = SequenceMatcher(None, w, kw).ratio()
        if score > best_score:
            best_score = score
            best_match = kw

    # Threshold: 0.82 — high enough to avoid false positives like linked→link
    # Also require the corrected word is not shorter than the input by more than 1 char
    # (real typos are usually same length or longer, not shorter)
    if best_score >= 0.82 and best_match:
        if len(best_match) >= len(w) - 1:
            return best_match
    return word


def normalize(text: str) -> str:
    """
    Normalize a user message:
    1. Apply exact substitution table (fast path).
    2. Apply fuzzy word correction for remaining unknown words.

    Returns the normalized text. The original text is unchanged if
    no corrections are needed.

    Examples:
        "i wanna aply for pann crad" → "i want to apply for pan card"
        "salary is 3 lakss"          → "salary is 3 lakh"
        "my aadhar is linked"        → "my aadhaar is linked"
        "pan stauts check"           → "pan status check"
        "documnet required"          → "document required"
    """
    if not text or not text.strip():
        return text

    result = text

    # Step 1: exact substitutions (regex-based, handles multi-word patterns)
    for pattern, replacement in _COMPILED_SUBS:
        result = pattern.sub(replacement, result)

    # Step 2: fuzzy word-level correction
    # Split on whitespace, correct each word independently
    words = result.split()
    corrected = []
    for word in words:
        # Strip punctuation for matching, reattach after
        stripped = word.strip('.,!?;:')
        suffix = word[len(stripped):]
        corrected_word = _fuzzy_correct_word(stripped)
        corrected.append(corrected_word + suffix)

    result = ' '.join(corrected)
    return result
