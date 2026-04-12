# retrieval/retriever.py
import os
import re
os.environ["HF_HOME"] = "D:\\hf_cache"

import json
from pathlib import Path
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi

CHROMA_PATH  = Path("./chroma_db")
COLLECTION   = "pan_chunks"
EMBED_MODEL  = "BAAI/bge-m3"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CHUNKS_FILE  = Path("ingestion/chunks.json")

TOP_DENSE  = 10
TOP_BM25   = 10
TOP_FINAL  = 3

QUERY_NORMALIZATIONS = [
    ("pan registration", "pan card application"),
    ("PAN registration", "PAN card application"),
    ("register for pan", "apply for pan card"),
    ("Register for PAN", "Apply for PAN card"),
]


class HybridRetriever:

    def __init__(self):
        print("Loading embedding model...")
        self.embed_model = SentenceTransformer(EMBED_MODEL)

        print("Loading reranker model...")
        self.reranker = CrossEncoder(RERANK_MODEL)

        print("Connecting to ChromaDB...")
        client = PersistentClient(path=str(CHROMA_PATH))
        self.collection = client.get_collection(COLLECTION)

        print("Loading chunks for BM25...")
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        tokenized = [c["text"].lower().split() for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)

        self.chunk_map = {c["chunk_id"]: c for c in self.chunks}

        print("✅ Retriever ready\n")

    def normalize_query(self, query: str) -> str:
        """Normalize common query variations."""
        # Handle e-PAN variants with regex (case-insensitive)
        query = re.sub(r'\be[\s\-_]?pan\b', 'e-PAN', query, flags=re.IGNORECASE)
        
        # Keep your existing loop for other normalizations
        for original, replacement in QUERY_NORMALIZATIONS:
            query = query.replace(original, replacement)
        
        return query

    def dense_search(self, query: str) -> list[dict]:
        """Search ChromaDB using embeddings (meaning-based)."""
        query_vector = self.embed_model.encode(
            [query],
            normalize_embeddings=True
        ).tolist()

        results = self.collection.query(
            query_embeddings=query_vector,
            n_results=TOP_DENSE,
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text"  : doc,
                "url"   : meta["url"],
                "title" : meta["title"],
                "score" : 1 - dist,
            })

        return chunks

    def bm25_search(self, query: str) -> list[dict]:
        """Search using BM25 (keyword-based)."""
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)

        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:TOP_BM25]

        chunks = []
        for idx in top_indices:
            c = self.chunks[idx]
            chunks.append({
                "text"  : c["text"],
                "url"   : c["url"],
                "title" : c["title"],
                "score" : float(scores[idx]),
            })

        return chunks

    def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """Use CrossEncoder to rerank combined results."""
        if not chunks:
            return []

        pairs  = [[query, c["text"]] for c in chunks]
        scores = self.reranker.predict(pairs)

        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

        filtered = [c for c in reranked if c["rerank_score"] > 1.0]

        final = filtered[:TOP_FINAL] if filtered else reranked[:2]

        return final

    def retrieve(self, query: str) -> list[dict]:
        """Full hybrid retrieval pipeline."""

        # Normalize query before retrieval
        query = self.normalize_query(query)

        # Step 1: Get candidates from both methods
        dense_results = self.dense_search(query)
        bm25_results  = self.bm25_search(query)

        # Step 2: Merge and deduplicate by text
        seen   = set()
        merged = []
        for chunk in dense_results + bm25_results:
            if chunk["text"] not in seen:
                seen.add(chunk["text"])
                merged.append(chunk)

        # Step 3: Rerank merged results
        final = self.rerank(query, merged)

        return final


if __name__ == "__main__":
    retriever = HybridRetriever()

    test_queries = [
        "How do I apply for a new PAN card?",
        "What documents are required for PAN?",
        "How to link Aadhaar with PAN?",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        results = retriever.retrieve(query)
        for i, r in enumerate(results):
            print(f"\n  [{i+1}] {r['title']}")
            print(f"       URL   : {r['url']}")
            print(f"       Score : {r['rerank_score']:.4f}")
            print(f"       Text  : {r['text'][:150]}...")