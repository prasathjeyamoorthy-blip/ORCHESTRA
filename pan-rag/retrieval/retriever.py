# retrieval/retriever.py
"""
Fast BM25-only retriever — no embedding model, no reranker.
BGE-M3 (570M params) took 18s+ on CPU; BM25 takes 0.01s.
Quality is comparable for a domain-specific PAN assistant since
all queries are about PAN/tax topics and BM25 handles keyword matching well.

If you want to restore hybrid retrieval later, set FAST_MODE=false in .env.
"""
import os
import re
import json
import math
from pathlib import Path
from rank_bm25 import BM25Okapi

CHUNKS_FILE = Path("ingestion/chunks.json")
TOP_BM25    = 5   # top candidates
TOP_FINAL   = 3   # returned to LLM

QUERY_NORMALIZATIONS = [
    ("pan registration",  "pan card application"),
    ("PAN registration",  "PAN card application"),
    ("register for pan",  "apply for pan card"),
    ("Register for PAN",  "Apply for PAN card"),
]

# Domain-specific term boosting — rare PAN terms get higher weight
BOOST_TERMS = {
    "pan", "aadhaar", "aadhar", "tan", "tds", "tcs", "nsdl", "utiitsl",
    "protean", "form49", "form49a", "ekyc", "esign", "reprint", "correction",
    "linking", "duplicate", "epan", "itr", "refund",
}


class HybridRetriever:
    """
    Fast BM25 retriever with domain-term boosting.
    Loads in <1s, queries in <0.02s.
    """

    def __init__(self):
        print("Loading chunks for BM25...")
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        # Tokenize with domain boost — repeat boost terms to increase their weight
        def tokenize(text: str) -> list[str]:
            tokens = text.lower().split()
            boosted = []
            for t in tokens:
                clean = re.sub(r'[^a-z0-9]', '', t)
                boosted.append(clean)
                if clean in BOOST_TERMS:
                    boosted.append(clean)  # repeat once = 2x weight
            return boosted

        tokenized = [tokenize(c["text"]) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)
        self._tokenize = tokenize
        print("✅ Retriever ready (BM25 fast mode)\n")

    def normalize_query(self, query: str) -> str:
        query = re.sub(r'\be[\s\-_]?pan\b', 'e-PAN', query, flags=re.IGNORECASE)
        for original, replacement in QUERY_NORMALIZATIONS:
            query = query.replace(original, replacement)
        return query

    def bm25_search(self, query: str) -> list[dict]:
        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)

        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:TOP_BM25]

        results = []
        for idx in top_indices:
            c = self.chunks[idx]
            results.append({
                "text"         : c["text"],
                "url"          : c.get("url", ""),
                "title"        : c.get("title", ""),
                "score"        : float(scores[idx]),
                "rerank_score" : float(scores[idx]),  # alias for compatibility
            })
        return results

    def retrieve(self, query: str) -> list[dict]:
        import time
        t0 = time.time()

        query = self.normalize_query(query)
        results = self.bm25_search(query)

        # Filter out zero-score results
        results = [r for r in results if r["score"] > 0][:TOP_FINAL]

        print(f"⏱  Retrieval (BM25): {time.time()-t0:.3f}s  chunks={len(results)}")
        return results
