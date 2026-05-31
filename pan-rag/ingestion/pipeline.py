# ingestion/pipeline.py
import os
os.environ["HF_HOME"] = "D:\\hf_cache"

import subprocess
import sys
from pathlib import Path

CHUNK_SCRIPT = Path("ingestion/chunk.py")
EMBED_SCRIPT  = Path("ingestion/embed.py")


def run_script(script_path: Path, label: str):
    print(f"\n{'='*50}")
    print(f"▶️  Running: {label}")
    print(f"{'='*50}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=False
    )

    if result.returncode != 0:
        print(f"\n❌ {label} failed with exit code {result.returncode}")
        print("Fix the error above and re-run pipeline.py")
        sys.exit(1)

    print(f"\n✅ {label} completed successfully")


def main():
    print("🚀 Starting RAG ingestion pipeline...")
    print(f"   Step 1: Chunk scraped data")
    print(f"   Step 2: Embed chunks → ChromaDB")

    # Step 1: Chunk
    run_script(CHUNK_SCRIPT, "Chunking (chunk.py)")

    # Step 2: Embed into ChromaDB
    run_script(EMBED_SCRIPT, "Embedding (embed.py)")

    print(f"\n{'='*50}")
    print(f"🎉 Pipeline complete!")
    print(f"   ChromaDB is rebuilt and ready.")
    print(f"   Run: python test_chat.py to test your chatbot")
    print(f"{'='*50}")


main()