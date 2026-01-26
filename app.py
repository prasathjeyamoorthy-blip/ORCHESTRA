# %%
from langchain_community.document_loaders import PyPDFLoader, PyMuPDFLoader, DirectoryLoader



# %%


# %%

dir_loader = DirectoryLoader(
    path="./pdf_documents",  # current directory (AGENTICRAG)
    glob="Residence_Certificate*.pdf",  # only your two PDFs
    loader_cls=PyMuPDFLoader,
    show_progress=True
)

pdf_documents = dir_loader.load()

pdf_documents


# %%
import sys
print(sys.executable)


# %%
# for doc in chunks:
#     source = doc.metadata.get("source", "").lower()

#     if "reason" in source or "explanation" in source:
#         doc.metadata["intent"] = "reasoning"
#     else:
#         doc.metadata["intent"] = "rules"

#     doc.metadata["service"] = "residence_certificate"


# %%
from langchain_community.document_loaders import PyMuPDFLoader

pdf_files = {
    "rules": "pdf_documents/Residence_Certificate_Full_Structured_Info.pdf",
    "reasoning": "pdf_documents/Residence_Certificate_Service_Explanation_and_Document_Reasons.pdf"
}


documents = {}

for key, path in pdf_files.items():
    loader = PyMuPDFLoader(path)
    documents[key] = loader.load()


# %%
from langchain_core.documents import Document

def make_chunk(text, intent, source, entity=None):
    metadata = {
        "service": "residence_certificate",
        "intent": intent,
        "source": source
    }
    if entity:
        metadata["entity"] = entity

    return Document(page_content=text.strip(), metadata=metadata)



# %%
import re

def extract_service_details_from_text(rules_text, source):
    chunks = []

    lines = [l.strip() for l in rules_text.splitlines() if l.strip()]

    for i, line in enumerate(lines):
        if "service charge" in line.lower():
            value = None

            # Try same line first
            match = re.search(r"\b(\d+)\b", line)
            if match:
                value = match.group(1)

            # Otherwise check next line
            elif i + 1 < len(lines):
                next_line = lines[i + 1]
                match = re.search(r"\b(\d+)\b", next_line)
                if match:
                    value = match.group(1)

            if value:
                chunks.append(
                    make_chunk(
                        f"Service Charge (INR): {value}",
                        intent="service_fee",
                        source=source
                    )
                )

    return chunks


# %%
#Semantic chunking for PDF 1

rule_chunks = []

rules_text = "\n".join([d.page_content for d in documents["rules"]])

# --- Service Info ---
service_info = rules_text.split("Mandatory Documents")[0]
rule_chunks.append(
    make_chunk(service_info, "service_info", pdf_files["rules"])
)

# --- Service Details (from text, not table) ---
service_detail_chunks = extract_service_details_from_text(
    rules_text,
    pdf_files["rules"]
)
rule_chunks.extend(service_detail_chunks)

# --- Mandatory Documents ---
mandatory_section = rules_text.split("Mandatory Documents")[1].split("Category-wise")[0]
rule_chunks.append(
    make_chunk(mandatory_section, "rules_mandatory", pdf_files["rules"])
)


# %%
# --- Government Employees Documents (ROBUST FIX) ---
import re

def extract_government_documents(rules_text, source):
    pattern = re.compile(
        r"government\s+employees(.*?)(?:\n\n|\Z)",
        re.IGNORECASE | re.DOTALL
    )

    match = pattern.search(rules_text)
    if not match:
        return []

    text = match.group(1).strip()

    return [
        make_chunk(
            text,
            intent="rules_category_govt",
            source=source
        )
    ]

rule_chunks.extend(
    extract_government_documents(rules_text, pdf_files["rules"])
)


# %%
def extract_service_details_from_text(rules_text, source):
    """
    Extracts service metadata like Service Charge, Service Name, etc.
    from flattened PDF text.
    """
    service_keys = [
        "Service ID",
        "Department",
        "Service Name",
        "Access Type",
        "Online Availability",
        "Service Charge"
    ]

    chunks = []

    for key in service_keys:
        for line in rules_text.splitlines():
            if key.lower() in line.lower():
                cleaned = " ".join(line.split())
                chunks.append(
                    make_chunk(
                        cleaned,
                        intent="service_fee" if "charge" in key.lower() else "service_metadata",
                        source=source
                    )
                )
                break  # stop after first match

    return chunks


# %%
#Semantic chunking for PDF 2

reasoning_chunks = []

reasoning_text = "\n".join([d.page_content for d in documents["reasoning"]])

# --- Service explanation ---
service_explanation = reasoning_text.split("Why Documents are Collected")[0]
reasoning_chunks.append(
    make_chunk(service_explanation, "service_explanation", pdf_files["reasoning"])
)

# --- Global reasoning ---
global_reason = reasoning_text.split("Why Documents are Collected")[1].split("Reasoning Behind")[0]
reasoning_chunks.append(
    make_chunk(global_reason, "reasoning_global", pdf_files["reasoning"])
)

# --- Per-document reasoning ---
document_reasons = {
    "Applicant Photograph": "Applicant Photograph",
    "Current Address Proof": "Current Address Proof",
    "Self-Declaration": "Self-Declaration",
    "Passport": "Passport",
    "Driving Licence": "Driving Licence",
    "PAN Card": "PAN Card",
    "Bank / Post Office Passbook": "Bank / Post Office Passbook",
    "Smart Card": "Smart Card",
    "Health Insurance Smart Card": "Health Insurance Smart Card",
    "Pension Document": "Pension Document",
    "Service Identity Card": "Service Identity Card",
    "MP/MLA/MLC Identity Card": "MP/MLA/MLC Identity Card",
    "Photo Voter Slip": "Photo Voter Slip"
}

for doc_name, key in document_reasons.items():
    if doc_name in reasoning_text:
        section = reasoning_text.split(doc_name)[1].split("\n", 1)[1]
        reasoning_chunks.append(
            make_chunk(section, "reasoning_document", pdf_files["reasoning"], entity=doc_name)
        )


# %%
all_chunks = rule_chunks + reasoning_chunks

print(f"Total semantic chunks created: {len(all_chunks)}")

# Inspect one
print(all_chunks[0].metadata)
print(all_chunks[0].page_content[:300])


# %%
from dotenv import load_dotenv
import os

load_dotenv()  # 👈 this reads .env into environment variables

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
NVIDIA_LLM_API_KEY = os.getenv("NVIDIA_LLM_API_KEY")   

if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY not found")



# %%
from openai import OpenAI

client_embed = OpenAI(
    api_key=NVIDIA_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)


# %%
def embed_chunks(chunks):
    """
    chunks: List[langchain_core.documents.Document]
    returns: List[List[float]] -> embeddings aligned with chunks
    """

    texts = [chunk.page_content for chunk in chunks]

    response = client_embed.embeddings.create(
        model="nvidia/nv-embedqa-e5-v5",
        input=texts,
        extra_body={
            "input_type": "passage"  # REQUIRED for document chunks
        }
    )

    return [item.embedding for item in response.data]


# %%
# %% 
chunk_embeddings = embed_chunks(all_chunks)

# sanity check
print(len(chunk_embeddings))       # should be 19
print(len(chunk_embeddings[0]))    # embedding dimension (~1024)


# %%
from qdrant_client import QdrantClient

qdrant_client = QdrantClient(
    url="https://103795bc-13b7-45b8-aea6-9b2ab07095a1.eu-west-2-0.aws.cloud.qdrant.io", 
    api_key=QDRANT_API_KEY,
)



# %%
from qdrant_client.models import VectorParams, Distance

VECTOR_SIZE = len(chunk_embeddings[0])

COLLECTION_NAME = "residence_certificate_agent"

qdrant_client.recreate_collection(
    collection_name="residence_certificate_agent",
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE   # ✅ BEST for E5 models
    )
)


# %%
# %%
from qdrant_client.models import PayloadSchemaType

qdrant_client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="intent",
    field_schema=PayloadSchemaType.KEYWORD
)

print("Index created for 'intent'")


# %%
# %%
qdrant_client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="entity",
    field_schema=PayloadSchemaType.KEYWORD
)

print("Index created for 'entity'")


# %%
# %%
qdrant_client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="service",
    field_schema=PayloadSchemaType.KEYWORD
)

print("Index created for 'service'")


# %%
# %%
from qdrant_client.models import PointStruct
import uuid

points = []

for chunk, embedding in zip(all_chunks, chunk_embeddings):
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "text": chunk.page_content,
                **chunk.metadata
            }
        )
    )

qdrant_client.upsert(
    collection_name=COLLECTION_NAME,
    points=points
)

print(f"Inserted {len(points)} chunks into Qdrant")


# %%
# %%
info = qdrant_client.get_collection(COLLECTION_NAME)
print(info)


# %%
# %%
def embed_query(text: str):
    response = client_embed.embeddings.create(
        model="nvidia/nv-embedqa-e5-v5",
        input=text,
        extra_body={
            "input_type": "query"   # 🔑 REQUIRED for queries
        }
    )
    return response.data[0].embedding


# %%
from qdrant_client.models import Filter, FieldCondition, MatchValue

def search_documents(question: str, intent: str, limit=5):
    query_vector = embed_query(question)

    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="intent",
                    match=MatchValue(value=intent)
                )
            ]
        )
    )

    return results.points


# %%
# %%
results = search_documents(
    "What are the documents to be certified by Government employees ?",
    intent="rules_category_govt"
)


for hit in results:
    print("Score:", hit.score)
    print(hit.payload["text"][:300])
    print("-" * 50)


# %%
def build_context(results):
    """
    results: list of Qdrant points
    returns: single context string for LLM
    """
    context_blocks = []
    for hit in results:
        context_blocks.append(hit.payload["text"])

    return "\n\n".join(context_blocks)


# %%
from openai import OpenAI


client_embed_reasoning = OpenAI(
    api_key=NVIDIA_LLM_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)


# %%
def generate_answer(question: str, context: str):
    response = client_embed_reasoning.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[
    {
    "role": "system",
    "content": (
        "You are a government service assistant. "
        "You MUST answer strictly using the provided context. "
        "DO NOT infer, estimate, or modify any numbers. "
        "If a numeric value appears in the context, reproduce it exactly without modification. "
        "If the value refers to a service charge, fee, or amount, present it explicitly in Indian Rupees (₹). "
        "If the context contains a list of documents, summarise the list clearly in the answer. "
        "If the answer cannot be answered using the context, say "
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
def detect_intents(question: str):
    q = question.lower()

    if any(k in q for k in ["fee", "charge", "amount", "cost"]):
        return ["service_fee"]

    if "why" in q or "purpose" in q:
        return ["service_explanation", "reasoning_global", "reasoning_document"]

    if "government" in q or "employee" in q:
        return ["rules_category_govt"]

    return ["rules_mandatory"]


# %%
def retrieve_context(question: str, limit=5):
    intents = detect_intents(question)
    all_results = []

    for intent in intents:
        # 🔑 Rule-based intents → direct filter (no embeddings)
        if intent in ["rules_category_govt", "rules_mandatory"]:
            results = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                limit=limit,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="intent",
                            match=MatchValue(value=intent)
                        )
                    ]
                )
            ).points
        else:
            # Semantic intents → vector search
            results = search_documents(question, intent, limit)

        all_results.extend(results)

    # Deduplicate by point ID
    seen = set()
    unique = []
    for r in all_results:
        if r.id not in seen:
            unique.append(r)
            seen.add(r.id)

    return unique


# %%
def detect_entity(question: str):
    docs = [
        "pension",
        "passport",
        "pan",
        "driving licence",
        "bank",
        "smart card"
    ]
    for d in docs:
        if d in question.lower():
            return d.title()
    return None


# %%
def answer_question(user_query: str):
    intents = detect_intents(user_query)
    results = retrieve_context(user_query)

    # 🔑 RULE-BASED ANSWERS → NO LLM
    if "rules_category_govt" in intents or "rules_mandatory" in intents:
        if not results:
            return "The information is not available in the provided documents."

        # Combine rule chunks directly
        lines = []
        for r in results:
            lines.append(r.payload["text"])

        return "\n".join(lines)

    # 🔑 EVERYTHING ELSE → LLM
    context = build_context(results)
    return generate_answer(user_query, context)


# %%
response = answer_question(
    "what documents i have to submit if i am a government employee?"
)

print(response)


# %%
results = qdrant_client.query_points(
    collection_name=COLLECTION_NAME,
    limit=5,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="intent",
                match=MatchValue(value="rules_category_govt")
            )
        ]
    )
)

for p in results.points:
    print(p.payload["text"][:300])


# %%



