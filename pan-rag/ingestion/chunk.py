# ingestion/chunk.py
import json
from pathlib import Path

INPUT_FILE = Path("scraper/scraped_data.json")
OUTPUT_FILE = Path("ingestion/chunks.json")

# Chunking settings
CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 100     # characters shared between consecutive chunks

# Junk phrases that indicate a chunk has no real content
JUNK_PHRASES = [
    "clicking here",
    "click here",
    "view the list",
    "please visit",
    "refer to the link",
    "click on the link",
    "refer here",
    "visit here",
]


def clean_text(text: str) -> str:
    """Remove excessive whitespace and blank lines."""
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned)


def is_quality_chunk(text: str) -> bool:
    """
    Returns False if the chunk is too short or contains
    redirect-only language that won't help the RAG answer questions.
    """
    if len(text.strip()) < 200:
        return False
    text_lower = text.lower()
    if any(phrase in text_lower for phrase in JUNK_PHRASES):
        return False
    return True


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Don't add tiny leftover chunks (less than 100 chars)
        if len(chunk) >= 100:
            chunks.append(chunk)

        # Move forward by (chunk_size - overlap)
        # This creates the overlap with the previous chunk
        start += chunk_size - overlap

    return chunks


def main():
    # Load scraped data
    print("Loading scraped data...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        pages = json.load(f)

    print(f"Loaded {len(pages)} pages")

    all_chunks = []
    skipped_pages = 0
    filtered_chunks = 0

    for page in pages:
        url = page.get("url", "")
        title = page.get("title", "")
        text = page.get("text", "")

        # Skip empty or failed pages
        if len(text) < 100:
            skipped_pages += 1
            continue

        # Clean the text first
        text = clean_text(text)

        # Split into chunks
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)

        # Store each chunk with its metadata
        for i, chunk in enumerate(chunks):

            # Skip low-quality chunks
            if not is_quality_chunk(chunk):
                filtered_chunks += 1
                continue

            all_chunks.append({
                "chunk_id": f"{url}__chunk_{i}",    # unique ID for each chunk
                "url": url,
                "title": title,
                "chunk_index": i,                    # position of chunk in page
                "total_chunks": len(chunks),          # how many chunks this page has
                "text": chunk,
            })

    # Save chunks
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"\n{'='*50}")
    print(f"✅ Total chunks created  : {len(all_chunks)}")
    print(f"🚫 Chunks filtered out  : {filtered_chunks}")
    print(f"📄 Pages processed      : {len(pages) - skipped_pages}")
    print(f"⏭️  Pages skipped        : {skipped_pages}")
    print(f"📏 Chunk size           : {CHUNK_SIZE} chars")
    print(f"🔁 Overlap              : {CHUNK_OVERLAP} chars")
    print(f"💾 Saved to             : {OUTPUT_FILE}")


main()