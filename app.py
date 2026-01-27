# %%
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from dotenv import load_dotenv
import os
from openai import OpenAI





# %%
# Load .env file into environment
load_dotenv()

# NVIDIA
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_LLM_API_KEY = os.getenv("NVIDIA_LLM_API_KEY")


# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Basic safety checks (optional but recommended)
if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY not found in environment")

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError("QDRANT credentials not found in environment")

# %%

PDF_PATHS = [
    "pdf_documents/Residence_certificate_info.pdf",
    "pdf_documents/Residence_Certificate_Service_Explanation.pdf"
]

documents = []
for path in PDF_PATHS:
    loader = PyMuPDFLoader(path)
    documents.extend(loader.load())


# %%
SECTION_HEADERS = [
    "Service Details",
    "Mandatory Documents",
    "Category-wise Document Classification",
    "General Citizens",
    "Government Employees",
    "Important Notes",
    "What is the Residence Certificate Service",
    "Why Documents are Collected",
    "Reasoning Behind Each Document"
]


# %%
def split_by_section(documents):
    sectioned_docs = []

    pattern = r"(?=(" + "|".join(SECTION_HEADERS) + r"))"

    for doc in documents:
        text = doc.page_content
        splits = re.split(pattern, text)

        for chunk in splits:
            cleaned = chunk.strip()
            if cleaned:
                sectioned_docs.append(
                    Document(
                        page_content=cleaned,
                        metadata=doc.metadata
                    )
                )

    return sectioned_docs


# %%
adaptive_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,          # high precision
    chunk_overlap=60,        # preserves meaning
    separators=[
        "\n\n",              # paragraphs
        "\n",                # lines
        "•", "-", "1.",      # lists
        " "
    ]
)


# %%
def efficient_chunking(documents):
    # Step 1: Split by logical sections
    section_docs = split_by_section(documents)

    # Step 2: Chunk within sections
    chunks = adaptive_splitter.split_documents(section_docs)

    return chunks


# %%
# documents = output from PyMuPDFLoader
chunks = efficient_chunking(documents)


# %%
for i, chunk in enumerate(chunks):
    chunk.metadata["chunk_id"] = i
    chunk.metadata.setdefault("source", "residence_certificate")


# %%

client_embed = OpenAI(
    api_key=NVIDIA_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)


# %%
def embed_chunks(chunks):
    texts = [chunk.page_content for chunk in chunks]

    response = client_embed.embeddings.create(
        model="nvidia/nv-embedqa-e5-v5",
        input=texts,
        extra_body={"input_type": "passage"}
    )

    return [item.embedding for item in response.data]


# %%
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)


# %%
COLLECTION_NAME = "residence_certificate"

qdrant_client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    )
)


# %%
from qdrant_client.models import PointStruct
import uuid

embeddings = embed_chunks(chunks)

points = []

for chunk, vector in zip(chunks, embeddings):
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "text": chunk.page_content,
                "metadata": chunk.metadata
            }
        )
    )

qdrant_client.upsert(
    collection_name=COLLECTION_NAME,
    points=points
)


# %%
def retrieve_chunks(query: str, top_k: int = 6):
    # 1. Embed the query (QUERY MODE is IMPORTANT)
    query_embedding = client_embed.embeddings.create(
        model="nvidia/nv-embedqa-e5-v5",
        input=query,
        extra_body={"input_type": "query"}
    ).data[0].embedding

    # 2. Query Qdrant (NEW API)
    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=top_k
    )

    # 3. Extract stored text
    return [point.payload["text"] for point in results.points]

# %%
chunks = retrieve_chunks(
    "What documents are mandatory for residence certificate?"
)

for c in chunks:
    print("-" * 40)
    print(c[:300])


# %%
client_llm = OpenAI(
    api_key=NVIDIA_LLM_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)
print(client_llm.models.list())


# %%
def rag_answer(question: str, context: str):
    response = client_llm.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a government service assistant. "
                    "You MUST answer strictly using the provided context. "
                    "DO NOT infer, estimate, or modify any numbers. "
                    "If a numeric value appears in the context, reproduce it exactly. "
                    "If the context contains a list of documents, summarise the list clearly. "
                    "If the answer cannot be answered using the context, say exactly: "
                    "'The information is not available in the provided documents.'"
                )
            },
            {
                "role": "user",
                "content": f"""
Use ONLY the information in the Context section.

Context:
{context}

Question:
{question}

Answer format:
- Give a single, direct answer.
- Do not add extra explanation.
"""
            }
        ],
        temperature=0.2,
        max_tokens=512
    )

    return response.choices[0].message.content


# %%
def answer_question(question: str):
    contexts = retrieve_chunks(question, top_k=6)
    context_text = "\n\n".join(contexts)
    return rag_answer(question, context_text)


# %%
print(answer_question("what are all the documents i have to submit if i am a government employee"))


# %%



# %%



