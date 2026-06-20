from dotenv import load_dotenv
import os

load_dotenv()

# ── NVIDIA NIM API ────────────────────────────────────────────────
NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
LLM_MODEL       = os.getenv("LLM_MODEL", "meta/llama-3.1-70b-instruct")

# ── Vector store / embeddings ─────────────────────────────────────
CHROMA_PATH        = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION", "pan_portal")
EMBED_MODEL        = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANKER_MODEL     = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")

# ── Generation settings ───────────────────────────────────────────
MAX_TOKENS   = int(os.getenv("MAX_TOKENS", "1024"))
TEMPERATURE  = float(os.getenv("TEMPERATURE", "0.2"))
