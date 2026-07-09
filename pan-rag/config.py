from dotenv import load_dotenv
import os

load_dotenv()

# ── LLM Provider selection ────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()  # "groq" | "nvidia"

# ── Groq API — all 5 keys loaded for rotation ─────────────────────
GROQ_API_KEYS = [
    k for k in [
        os.getenv("GROQ_API_KEY1", ""),
        os.getenv("GROQ_API_KEY2", ""),
        os.getenv("GROQ_API_KEY3", ""),
        os.getenv("GROQ_API_KEY4", ""),
        os.getenv("GROQ_API_KEY5", ""),
    ] if k
]
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── NVIDIA NIM API (fallback) ─────────────────────────────────────
NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL    = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")

# ── Active LLM config ─────────────────────────────────────────────
if LLM_PROVIDER == "groq":
    if not GROQ_API_KEYS:
        raise EnvironmentError("LLM_PROVIDER=groq but no GROQ_API_KEY1..5 found in .env")
    LLM_API_KEY  = GROQ_API_KEYS[0]   # seed; rotation overrides at runtime
    LLM_BASE_URL = GROQ_BASE_URL
    LLM_MODEL    = GROQ_MODEL
else:
    LLM_API_KEY  = NVIDIA_API_KEY
    LLM_BASE_URL = NVIDIA_BASE_URL
    LLM_MODEL    = NVIDIA_MODEL

# ── Vector store / embeddings ─────────────────────────────────────
CHROMA_PATH        = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION", "pan_portal")
EMBED_MODEL        = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANKER_MODEL     = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")

# ── Generation settings ───────────────────────────────────────────
MAX_TOKENS  = int(os.getenv("MAX_TOKENS", "1024"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
