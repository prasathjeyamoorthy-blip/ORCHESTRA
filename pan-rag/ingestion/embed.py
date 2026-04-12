# ingestion/embed.py
import os
os.environ["HF_HOME"] = "D:\\hf_cache"   # ← add this before all other imports

# ingestion/embed.py
import json
from pathlib import Path
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
import sys

INPUT_FILE  = Path("ingestion/chunks.json")
CHROMA_PATH = Path("./chroma_db")
COLLECTION  = "pan_chunks"
MODEL_NAME  = "BAAI/bge-m3"
BATCH_SIZE  = 32   # embed this many chunks at a time


def main():
    # ── 1. Load chunks ──────────────────────────────────────────
    print("Loading chunks...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks")

    # ── 2. Load embedding model ─────────────────────────────────
    print(f"\nLoading embedding model: {MODEL_NAME}")
    print("(First run will download ~2GB — this is normal, wait for it)")
    model = SentenceTransformer(MODEL_NAME)
    print("✅ Model loaded")

    # ── 3. Connect to ChromaDB ───────────────────────────────────
    print(f"\nConnecting to ChromaDB at: {CHROMA_PATH}")
    client = PersistentClient(path=str(CHROMA_PATH))

    # Delete existing collection if re-running
    # so we don't get duplicate chunks
    existing = [c.name for c in client.list_collections()]
    if COLLECTION in existing:
        print(f"⚠️  Existing collection '{COLLECTION}' found — deleting and rebuilding")
        client.delete_collection(COLLECTION)

    collection = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"}   # use cosine similarity for search
    )
    print(f"✅ Collection '{COLLECTION}' ready")

    # ── 4. Embed and store in batches ────────────────────────────
    print(f"\nEmbedding {len(chunks)} chunks in batches of {BATCH_SIZE}...")
    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(total_batches):
        start = batch_num * BATCH_SIZE
        end   = min(start + BATCH_SIZE, len(chunks))
        batch = chunks[start:end]

        texts     = [c["text"]     for c in batch]
        ids       = [c["chunk_id"] for c in batch]
        metadatas = [{"url": c["url"], "title": c["title"], "chunk_index": c["chunk_index"]} for c in batch]

        # Convert text → vectors
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,   # needed for cosine similarity
            show_progress_bar=False,
        ).tolist()

        # Store in ChromaDB
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        print(f"  Batch {batch_num + 1}/{total_batches} done — chunks {start+1} to {end}")

    # ── 5. Verify ────────────────────────────────────────────────
    count = collection.count()
    print(f"\n{'='*50}")
    print(f"✅ Embedded and stored : {count} chunks")
    print(f"🗄️  ChromaDB location   : {CHROMA_PATH}")
    print(f"📦 Collection name     : {COLLECTION}")
    print(f"🧠 Embedding model     : {MODEL_NAME}")

    # Quick sanity test
    print(f"\nRunning sanity test query...")
    results = collection.query(
        query_embeddings=model.encode(["How to apply for PAN?"], normalize_embeddings=True).tolist(),
        n_results=3,
    )
    print("Top 3 results for 'How to apply for PAN?':")
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        print(f"\n  [{i+1}] {meta['title']} ({meta['url']})")
        print(f"       {doc[:120]}...")


main()