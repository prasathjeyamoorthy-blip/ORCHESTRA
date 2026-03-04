import os
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from pypdf import PdfReader
import uuid

load_dotenv()

COLLECTION = "residence_certificate"

embed_client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1"
)

qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Create collection if not exists
if not qdrant.collection_exists(COLLECTION):
    qdrant.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(
            size=1024,
            distance=Distance.COSINE
        )
    )
    print("Collection created.")

def chunk_text(text, chunk_size=500):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

pdf_folder = "pdf_documents"

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
                model="nvidia/nv-embedqa-e5-v5",
                input=chunk,
                extra_body={"input_type": "passage"}
            ).data[0].embedding

            qdrant.upsert(
                collection_name=COLLECTION,
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={"text": chunk}
                    )
                ]
            )

print("Ingestion complete.")