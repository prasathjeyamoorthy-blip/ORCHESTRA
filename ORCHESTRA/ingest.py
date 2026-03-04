import os
import json
import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

# ===============================
# FILE PATHS
# ===============================

FAISS_INDEX_FILE = "faiss_index.bin"
FAISS_TEXT_FILE = "faiss_texts.json"

# ===============================
# EMBEDDING CLIENT
# ===============================

embed_client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1"
)

# ===============================
# LOAD OR CREATE FAISS INDEX
# ===============================

dimension = 1024

if os.path.exists(FAISS_INDEX_FILE):
    index = faiss.read_index(FAISS_INDEX_FILE)
else:
    index = faiss.IndexFlatL2(dimension)

if os.path.exists(FAISS_TEXT_FILE):
    with open(FAISS_TEXT_FILE, "r") as f:
        stored_texts = json.load(f)
else:
    stored_texts = []

# ===============================
# TEXT CHUNKING
# ===============================

def chunk_text(text, chunk_size=1200, overlap=200):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# ===============================
# PDF INGESTION
# ===============================

pdf_folder = "pdf_documents"

for file in os.listdir(pdf_folder):

    if file.endswith(".pdf"):

        path = os.path.join(pdf_folder, file)
        reader = PdfReader(path)

        full_text = ""

        for page in reader.pages:
            full_text += page.extract_text() or ""

        chunks = chunk_text(full_text)

        vectors = []

        for chunk in chunks:

            embedding = embed_client.embeddings.create(
                model="nvidia/nv-embedqa-e5-v5",
                input=chunk,
                extra_body={"input_type": "passage"}
            ).data[0].embedding

            vectors.append(embedding)
            stored_texts.append(chunk)

        vectors = np.array(vectors).astype("float32")

        index.add(vectors)

        print(f"Ingested {len(chunks)} chunks from {file}")

# ===============================
# SAVE FAISS INDEX
# ===============================

faiss.write_index(index, FAISS_INDEX_FILE)

with open(FAISS_TEXT_FILE, "w") as f:
    json.dump(stored_texts, f)

print("Ingestion complete.")