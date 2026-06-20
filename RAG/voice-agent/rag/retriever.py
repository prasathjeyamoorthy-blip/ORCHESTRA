"""
rag/retriever.py — RAG Context Retrieval
Bridges the voice agent to the pan-rag BM25 retriever.

Loads chunks from pan-rag/ingestion/chunks.json and runs
BM25 search with domain-term boosting — same logic as pan-rag.
Falls back to empty string if chunks file is not found.
"""

import re
import json
from pathlib import Path

# ── Try to import rank_bm25, guide user if missing ───────────
try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False

# ── Path to pan-rag chunks (relative to project root) ────────
CHUNKS_FILE = Path(__file__).parent.parent.parent / "pan-rag" / "ingestion" / "chunks.json"

TOP_BM25  = 5   # candidates to score
TOP_FINAL = 3   # chunks returned to LLM
MAX_CHARS = 800 # max total context chars sent to LLM

# Domain terms that get 2× weight in BM25 tokenisation
BOOST_TERMS = {
    "pan", "aadhaar", "aadhar", "tan", "tds", "tcs", "nsdl", "utiitsl",
    "protean", "form49", "form49a", "ekyc", "esign", "reprint", "correction",
    "linking", "duplicate", "epan", "itr", "refund",
}

QUERY_NORMALIZATIONS = [
    ("pan registration", "pan card application"),
    ("PAN registration", "PAN card application"),
    ("register for pan", "apply for pan card"),
    ("Register for PAN", "Apply for PAN card"),
]


def _tokenize(text: str) -> list[str]:
    tokens = text.lower().split()
    boosted = []
    for t in tokens:
        clean = re.sub(r'[^a-z0-9]', '', t)
        boosted.append(clean)
        if clean in BOOST_TERMS:
            boosted.append(clean)   # repeat = 2× weight
    return boosted


def _normalize_query(query: str) -> str:
    query = re.sub(r'\be[\s\-_]?pan\b', 'e-PAN', query, flags=re.IGNORECASE)
    for original, replacement in QUERY_NORMALIZATIONS:
        query = query.replace(original, replacement)
    return query


class RAGRetriever:

    def __init__(self):
        if not _BM25_AVAILABLE:
            print("  ⚠️  rank_bm25 not installed — RAG disabled")
            print("     Run: pip install rank-bm25")
            self._ready = False
            return

        if not CHUNKS_FILE.exists():
            print(f"  ⚠️  Chunks file not found: {CHUNKS_FILE}")
            print("     RAG will be skipped — agent answers from model knowledge")
            self._ready = False
            return

        print("  Loading BM25 index from pan-rag chunks...")
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            self._chunks = json.load(f)

        tokenized    = [_tokenize(c["text"]) for c in self._chunks]
        self._bm25   = BM25Okapi(tokenized)
        self._ready  = True
        print(f"  ✅ RAG retriever ready — {len(self._chunks)} chunks indexed")

    def get_context(self, query: str) -> str:
        """
        Returns relevant context as a plain string for the LLM prompt.
        Returns empty string if nothing relevant is found.
        """
        if not self._ready:
            return ""

        query   = _normalize_query(query)
        tokens  = _tokenize(query)
        scores  = self._bm25.get_scores(tokens)

        top_idx = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:TOP_BM25]

        results = [
            self._chunks[i]["text"]
            for i in top_idx
            if scores[i] > 0
        ][:TOP_FINAL]

        if not results:
            return ""

        context = "\n\n".join(results)

        # Trim to MAX_CHARS so we don't blow the LLM context window
        if len(context) > MAX_CHARS:
            context = context[:MAX_CHARS] + "..."

        return context
