import os
import json
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)

# ===============================
# CONFIGURATION
# ===============================
COLLECTION_NAME = "residence_certificate_docs"
VECTOR_SIZE = 1024


def get_embed_client():
    return OpenAI(
        api_key=os.getenv("OPEN_ROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )


def get_qdrant_client():
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    if not qdrant_url or not qdrant_api_key:
        raise ValueError("[Qdrant] Critical: QDRANT_URL or QDRANT_API_KEY missing in .env. Qdrant Cloud is required.")

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, check_compatibility=False, timeout=10)
    client.get_collections()
    print(f"[Qdrant] Connected exclusively to cloud instance: {qdrant_url}")
    return client


def chunk_text(text, chunk_size=350, overlap=50):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - overlap)]


def run_ingestion():
    client = get_qdrant_client()
    embed_client = get_embed_client()

    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )
        print(f"[Qdrant] Created collection '{COLLECTION_NAME}' with vector size {VECTOR_SIZE}")

    pdf_folder = os.path.join(os.path.dirname(__file__), "pdf_documents")
    points = []
    point_id = 0

    if not os.path.exists(pdf_folder):
        print(f"[Qdrant] Warning: PDF folder '{pdf_folder}' not found.")
        return

    for file in os.listdir(pdf_folder):
        if file.endswith(".pdf"):
            path = os.path.join(pdf_folder, file)
            reader = PdfReader(path)
            full_text = ""

            for page in reader.pages:
                full_text += page.extract_text() or ""

            chunks = chunk_text(full_text)

            for chunk in chunks:
                embedding = embed_client.embeddings.create(
                    model="baai/bge-large-en-v1.5",
                    input=chunk
                ).data[0].embedding

                point_id += 1
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "source_file": file
                    }
                ))

            print(f"[Qdrant] Ingested {len(chunks)} chunks from {file}")

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"[Qdrant] Successfully upserted {len(points)} vector points into collection '{COLLECTION_NAME}'.")

    print("[Qdrant] Ingestion complete.")


if __name__ == "__main__":
    run_ingestion()