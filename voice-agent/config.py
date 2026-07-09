import os
from dotenv import load_dotenv
load_dotenv()

# ── API Keys ──────────────────────────────────────────────────
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

if not SARVAM_API_KEY:
    raise EnvironmentError(
        "SARVAM_API_KEY is not set. Add it to voice-agent/.env:\n"
        "  SARVAM_API_KEY=sk_..."
    )

# ── Groq API — key pool for rotation ─────────────────────────
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
GROQ_LLM_URL  = f"{GROQ_BASE_URL}/chat/completions"

# ── Voice Service Configuration ───────────────────────────────
VOICE_AGENT_PORT = int(os.getenv("VOICE_AGENT_PORT", "8002"))
VOICE_AGENT_HOST = os.getenv("VOICE_AGENT_HOST", "0.0.0.0")

VOICE_SERVICE_TIMEOUT      = int(os.getenv("VOICE_SERVICE_TIMEOUT", "30"))
VOICE_HEALTH_CHECK_INTERVAL = int(os.getenv("VOICE_HEALTH_CHECK_INTERVAL", "60"))
VOICE_FALLBACK_ENABLED     = os.getenv("VOICE_FALLBACK_ENABLED", "true").lower() == "true"

# ── Sarvam AI STT / TTS ───────────────────────────────────────
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")

# TTS voice configs per language (bulbul:v3 speakers)
SARVAM_VOICE_CONFIGS = {
    "en": {"tts_language": "en-IN", "tts_speaker": "aditya", "stt_language": "en-IN"},
    "ta": {"tts_language": "ta-IN", "tts_speaker": "amit",   "stt_language": "ta-IN"},
    "hi": {"tts_language": "hi-IN", "tts_speaker": "shubh",  "stt_language": "hi-IN"},
}

TTS_SAMPLE_RATE = 22050
TTS_LANGUAGE    = "en-IN"   # default

# ── LLM (CLI agent mode) ──────────────────────────────────────
LLM_MODEL       = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = 0.75
LLM_MAX_TOKENS  = 150

# ── Legacy aliases (kept so any remaining references don't break) ─
OLLAMA_MODEL       = LLM_MODEL
OLLAMA_TEMPERATURE = LLM_TEMPERATURE
OLLAMA_MAX_TOKENS  = LLM_MAX_TOKENS
OLLAMA_CTX         = 4096

# ── Mic / Recording Settings ──────────────────────────────────
SAMPLE_RATE       = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION  = 1.2
MAX_RECORD_SECS   = 30

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
