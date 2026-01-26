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
#Semantic chunking for PDF 1

rule_chunks = []

rules_text = "\n".join([d.page_content for d in documents["rules"]])

# --- Service Info ---
service_info = rules_text.split("Mandatory Documents")[0]
rule_chunks.append(
    make_chunk(service_info, "service_info", pdf_files["rules"])
)

# --- Mandatory Documents ---
mandatory_section = rules_text.split("Mandatory Documents")[1].split("Category-wise")[0]
rule_chunks.append(
    make_chunk(mandatory_section, "rules_mandatory", pdf_files["rules"])
)

# --- Category-wise Sections ---
citizen_section = rules_text.split("General Citizens")[1].split("Government employees")[0]
rule_chunks.append(
    make_chunk(citizen_section, "rules_category_citizen", pdf_files["rules"])
)

govt_section = rules_text.split("Government employees")[1]
rule_chunks.append(
    make_chunk(govt_section, "rules_category_govt", pdf_files["rules"])
)


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
# %%
from qdrant_client.models import Filter, FieldCondition, MatchValue

def search_mandatory_documents(question: str, limit=5):
    query_vector = embed_query(question)

    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[],
        query=query_vector,
        limit=limit,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="intent",
                    match=MatchValue(value="rules_mandatory")
                )
            ]
        )
    )

    return results.points


# %%
# %%
results = search_mandatory_documents(
    "What are the documents to be certified by Government employees ?"
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
                    "Answer ONLY using the provided context. "
                    "If the answer is not present in the context, say "
                    "'The information is not available in the provided documents.'"
                )
            },
            {
                "role": "user",
                "content": f"""
Context:
{context}

Question:
{question}
"""
            }
        ],
        temperature=0.2,
        max_tokens=512
    )

    return response.choices[0].message.content


# %%
def answer_question(user_query: str):
    results = search_mandatory_documents(user_query)
    context = build_context(results)
    answer = generate_answer(user_query, context)
    return answer


# %%
response = answer_question(
    "What are the certificates i have to submit to apply for residence certificate if i am a government employee?"
)

print(response)


# %%


# %%



