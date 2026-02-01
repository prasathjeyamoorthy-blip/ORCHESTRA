# %%
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from dotenv import load_dotenv
import os
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from uuid import uuid4
from langgraph.graph import StateGraph, END
from qdrant_client.models import VectorParams, Distance
import uuid









# %%
from typing import TypedDict, Optional, List

class RAGState(TypedDict):
    question: str
    context: Optional[str]
    answer: Optional[str]
    route: Optional[str]  # "rag" or "direct"


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
if not NVIDIA_API_KEY or not NVIDIA_LLM_API_KEY:
    raise ValueError("NVIDIA keys not found in environment")

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


qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)


# %%
COLLECTION_NAME = "residence_certificate"

qdrant_client.recreate_collection( #replace the recreate_collection while in production
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    )
)


# %%


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



# %%
client_llm = OpenAI(
    api_key=NVIDIA_LLM_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)


# %%
def route_question(state: RAGState) -> RAGState:
    question = state["question"]

    router_prompt = [
        {
            "role": "system",
            "content": (
                "You are a classifier.\n"
                "Decide whether the user's question requires looking up "
                "government residence certificate documents.\n\n"
                "If the question is about documents, eligibility, fees, "
                "process, categories, or rules → respond with RAG.\n"
                "If the question is general, conversational, or unrelated "
                "→ respond with DIRECT.\n\n"
                "Respond with ONLY one word: RAG or DIRECT."
            )
        },
        {
            "role": "user",
            "content": question
        }
    ]

    response = client_llm.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=router_prompt,
        temperature=0.3
    )

    decision = response.choices[0].message.content.strip().upper()

    state["route"] = "rag" if decision == "RAG" else "direct"
    return state


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
                    "If the answer cannot be answered using the context, try to answer based on the data from the documents provided by rag. "
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
def rag_node(state: RAGState) -> RAGState:
    question = state["question"]
    contexts = retrieve_chunks(question, top_k=6)
    context_text = "\n\n".join(contexts)

    answer = rag_answer(question, context_text)

    state["context"] = context_text
    state["answer"] = answer
    return state


# %%
def direct_llm_node(state: RAGState) -> RAGState:
    question = state["question"]

    response = client_llm.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a government service assistant. "
                    "You provide general guidance related to public services "
                    "and official processes. Answer clearly and concisely."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        temperature=0.4
    )

    state["answer"] = response.choices[0].message.content
    return state


# %%

graph = StateGraph(RAGState)

# Nodes
graph.add_node("router", route_question)
graph.add_node("rag", rag_node)
graph.add_node("direct", direct_llm_node)

# Entry point
graph.set_entry_point("router")

# Conditional routing
graph.add_conditional_edges(
    "router",
    lambda state: state["route"],
    {
        "rag": "rag",
        "direct": "direct"
    }
)

# End nodes
graph.add_edge("rag", END)
graph.add_edge("direct", END)

agentic_rag = graph.compile()

agentic_rag

# %%
def answer_question(question: str):
    result = agentic_rag.invoke(
        {
            "question": question,
            "context": None,
            "answer": None,
            "route": None
        }
    )
    return result["answer"]


# %%


# %%
###TO BE RUN ONCE


# %%
# from qdrant_client.models import VectorParams, Distance

# qdrant_client.create_collection(
#     collection_name="validation_rules",
#     vectors_config=VectorParams(
#         size=1024,              # REQUIRED for nv-embedqa-e5-v5
#         distance=Distance.COSINE
#     )
# )


# %%

# # ---------------------------------
# # NVIDIA Embedding Client
# # ---------------------------------
# nvidia_embed_client = OpenAI(
#     api_key=NVIDIA_API_KEY,
#     base_url="https://integrate.api.nvidia.com/v1"
# )

# # ---------------------------------
# # Qdrant Client
# # ---------------------------------
# qdrant_client = QdrantClient(
#     url=QDRANT_URL,
#     api_key=QDRANT_API_KEY
# )

# # ---------------------------------
# # Embedding Function (NVIDIA)
# # ---------------------------------
# def embed(text: str) -> list:
#     response = nvidia_embed_client.embeddings.create(
#         model="nvidia/nv-embedqa-e5-v5",
#         input=text,
#         extra_body = {
#             "input_type": "passage"
#         }

#     )
#     return response.data[0].embedding


# # ---------------------------------
# # Tamil Nadu Residence Certificate Rules
# # ---------------------------------
# rules = [

#     {
#         "text": "Every Residence Certificate application in Tamil Nadu must include a recent photograph of the applicant.",
#         "payload": {
#             "state": "Tamil Nadu",
#             "service": "Residence Certificate",
#             "rule_type": "mandatory_document",
#             "document": "Photograph",
#             "applies_to": "all",
#             "severity": "error"
#         }
#     },
#     {
#         "text": "A valid current address proof is mandatory to establish residence within Tamil Nadu.",
#         "payload": {
#             "state": "Tamil Nadu",
#             "service": "Residence Certificate",
#             "rule_type": "mandatory_document",
#             "document": "Current Address Proof",
#             "applies_to": "all",
#             "severity": "error"
#         }
#     },
#     {
#         "text": "The address mentioned in the address proof must match the address declared in the application.",
#         "payload": {
#             "state": "Tamil Nadu",
#             "service": "Residence Certificate",
#             "rule_type": "address_consistency",
#             "applies_to": "all",
#             "severity": "error"
#         }
#     },
#     {
#         "text": "A self-declaration affirming the correctness of information is mandatory for all applicants.",
#         "payload": {
#             "state": "Tamil Nadu",
#             "service": "Residence Certificate",
#             "rule_type": "mandatory_document",
#             "document": "Self Declaration",
#             "applies_to": "all",
#             "severity": "error"
#         }
#     },

#     {
#         "text": "General citizens in Tamil Nadu must submit at least one supporting identity or residence document.",
#         "payload": {
#             "state": "Tamil Nadu",
#             "service": "Residence Certificate",
#             "rule_type": "minimum_supporting_documents",
#             "applicant_type": "general_citizen",
#             "min_required": 1,
#             "severity": "error"
#         }
#     },

#     {
#         "text": "Applicants who are government employees must submit a valid Service Identity Card.",
#         "payload": {
#             "state": "Tamil Nadu",
#             "service": "Residence Certificate",
#             "rule_type": "mandatory_supporting_document",
#             "applicant_type": "government_employee",
#             "document": "Service Identity Card",
#             "severity": "error"
#         }
#     },

#     {
#         "text": "Applicants who are MPs, MLAs, or MLCs must submit an official identity card issued by the competent authority.",
#         "payload": {
#             "state": "Tamil Nadu",
#             "service": "Residence Certificate",
#             "rule_type": "mandatory_supporting_document",
#             "applicant_type": "public_representative",
#             "document": "Official Identity Card",
#             "severity": "error"
#         }
#     },

#     {
#         "text": "Applicants are not required to submit all listed supporting documents, only those applicable to their category.",
#         "payload": {
#             "state": "Tamil Nadu",
#             "service": "Residence Certificate",
#             "rule_type": "interpretation_rule",
#             "severity": "info"
#         }
#     }
# ]

# # ---------------------------------
# # Insert Rules into Qdrant
# # ---------------------------------
# points = [
#     PointStruct(
#         id=str(uuid4()),
#         vector=embed(rule["text"]),
#         payload=rule["payload"]
#     )
#     for rule in rules
# ]

# qdrant_client.upsert(
#     collection_name="validation_rules",
#     points=points
# )

# print("Rules stored successfully using NVIDIA embeddings.")


# %%

agentic_rag = graph.compile()




