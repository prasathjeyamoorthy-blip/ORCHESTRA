import os
from dotenv import load_dotenv
load_dotenv()

# ── API Keys ──────────────────────────────────────────────────
# Set these in voice-agent/.env — never hardcode keys here
NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY")
SARVAM_API_KEY  = os.getenv("SARVAM_API_KEY")
ASR_API_KEY     = os.getenv("STT_API_KEY") or NVIDIA_API_KEY
TTS_API_KEY     = os.getenv("TTS_API_KEY") or NVIDIA_API_KEY

# Validate required API keys
if not NVIDIA_API_KEY:
    raise EnvironmentError(
        "NVIDIA_API_KEY is not set. Add it to voice-agent/.env:\n"
        "  NVIDIA_API_KEY=nvapi-..."
    )

if not SARVAM_API_KEY:
    raise EnvironmentError(
        "SARVAM_API_KEY is not set. Add it to voice-agent/.env:\n"
        "  SARVAM_API_KEY=sk_..."
    )

# ── Voice Service Configuration ───────────────────────────────
VOICE_AGENT_PORT = int(os.getenv("VOICE_AGENT_PORT", "8002"))
VOICE_AGENT_HOST = os.getenv("VOICE_AGENT_HOST", "0.0.0.0")

# Service endpoints and connectivity
VOICE_SERVICE_TIMEOUT = int(os.getenv("VOICE_SERVICE_TIMEOUT", "30"))
VOICE_HEALTH_CHECK_INTERVAL = int(os.getenv("VOICE_HEALTH_CHECK_INTERVAL", "60"))
VOICE_FALLBACK_ENABLED = os.getenv("VOICE_FALLBACK_ENABLED", "true").lower() == "true"

# ── STT/TTS Model Configuration ──────────────────────────────
# Sarvam AI Models
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")

# NVIDIA NIM Models
NVIDIA_STT_MODEL = os.getenv("NVIDIA_STT_MODEL", "openai/whisper-large-v3")
NVIDIA_TTS_MODEL = os.getenv("NVIDIA_TTS_MODEL", "nvidia/magpie-tts-multilingual")

# ── ASR — openai/whisper-large-v3 via NVIDIA NIM cloud gRPC ──
# No local GPU needed — calls grpc.nvcf.nvidia.com:443
ASR_MODEL       = "openai/whisper-large-v3"

# ── TTS — nvidia/magpie-tts-multilingual via NVIDIA NIM cloud gRPC ──
TTS_VOICE       = os.getenv("TTS_VOICE", "Magpie-Multilingual.EN-US.Aria")
TTS_LANGUAGE    = "en-US"
TTS_SAMPLE_RATE = 22050

# ── LLM — NVIDIA NIM (meta/llama-3.3-70b-instruct) ───────────
NVIDIA_LLM_URL  = "https://integrate.api.nvidia.com/v1/chat/completions"
LLM_MODEL       = "meta/llama-3.3-70b-instruct"
LLM_TEMPERATURE = 0.75
LLM_MAX_TOKENS  = 150   # Reduced from 280 for faster, more concise responses

# Legacy aliases (kept so any remaining references don't break)
OLLAMA_MODEL       = LLM_MODEL
OLLAMA_TEMPERATURE = LLM_TEMPERATURE
OLLAMA_MAX_TOKENS  = LLM_MAX_TOKENS
OLLAMA_CTX         = 4096

# ── Mic / Recording Settings ──────────────────────────────────
SAMPLE_RATE        = 16000
SILENCE_THRESHOLD  = 0.01
SILENCE_DURATION   = 1.2
MAX_RECORD_SECS    = 30

# ── Agent Personality ─────────────────────────────────────────
SYSTEM_PROMPT = """You are Aria, a friendly PAN card voice assistant. Keep responses SHORT and DIRECT - 1 to 2 sentences maximum for speed.

You guide users through PAN registration: application details → personal details → confirmation → document upload.

STRICT RULES:
1. No bullet points, dashes, lists, or markdown
2. No URLs, emails, or phone numbers
3. Maximum 1-2 sentences per response - BE BRIEF
4. Use contractions: "you'll", "it's", "don't"
5. Never repeat the user's question back
6. Get straight to the point

FLOW ORDER (follow exactly):
1. Application details: submission mode, delivery, photo, income, address, status, representative
2. Personal details: name, mother's name, email, salary
3. Confirmation: show summary, ask if anything needs updating
4. Documents: list required documents

RESPONSE STYLE:
- Start with the key info immediately
- Skip pleasantries like "Great!" or "Perfect!"
- For choices, list options directly without preamble
- For confirmation, just say "yes or no"
- Example good: "Aadhaar online, upload and e-sign, or fill and courier?"
- Example bad: "Great! Now I need to know how you'd like to submit. You have three wonderful options available..."

YOUR EXPERTISE:
- PAN application (Form 49A), corrections, reprints
- Aadhaar eKYC, document requirements
- Fees, timelines

When user is confused, explain briefly then move on. When urgent, prioritize key info only."""
