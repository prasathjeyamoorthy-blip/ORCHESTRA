from dotenv import load_dotenv
import os

load_dotenv()

NVIDIA_API_KEY     = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL    = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL       = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
CHROMA_PATH        = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION", "pan_portal")
EMBED_MODEL        = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANKER_MODEL     = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")

# Aliases so llm.py can import these names
LLM_MODEL    = NVIDIA_MODEL
MAX_TOKENS   = int(os.getenv("MAX_TOKENS", "1024"))
TEMPERATURE  = float(os.getenv("TEMPERATURE", "0.2"))