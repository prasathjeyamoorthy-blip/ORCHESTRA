# api/voice.py
"""
Voice endpoints:
  POST /api/voice/stt   — audio → transcript JSON
  POST /api/voice/tts   — text  → WAV audio
  POST /api/voice/speak — full pipeline: STT → RAG+LLM → TTS

STT: Sarvam AI  saaras:v3   (speech_to_text.transcribe)
TTS: Sarvam AI  bulbul:v3   (text_to_speech.convert)
     Key: SARVAM_API_KEY  (pan-rag/.env)
"""

import sys
import io
import re
import wave
import base64
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

# Load .env FIRST — before any client is created
from dotenv import load_dotenv
load_dotenv()

import os
import numpy as np
import av
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse

voice_router = APIRouter()

# ── API key ───────────────────────────────────────────────────────────────────
_SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
if not _SARVAM_API_KEY:
    raise EnvironmentError(
        "SARVAM_API_KEY is not set in pan-rag/.env"
    )

# ── Voice configurations per language ────────────────────────────────────────
# bulbul:v3 speakers: shubh, ananya, ritu, priya, neha, rahul, pooja …
VOICE_CONFIGS = {
    "en": {
        "tts_language": "en-IN",
        "tts_speaker":  "aditya",  # clear, assertive male — formal English
        "stt_language": "en-IN",
    },
    "ta": {
        "tts_language": "ta-IN",
        "tts_speaker":  "amit",    # clear male Tamil voice
        "stt_language": "ta-IN",
    },
    "hi": {
        "tts_language": "hi-IN",
        "tts_speaker":  "shubh",   # bulbul:v3 Hindi male speaker
        "stt_language": "hi-IN",
    },
}


# ── Lazy Sarvam client (created once, on first use) ───────────────────────────
_sarvam_client = None

def _get_client():
    global _sarvam_client
    if _sarvam_client is None:
        from sarvamai import SarvamAI
        _sarvam_client = SarvamAI(api_subscription_key=_SARVAM_API_KEY)
        print("✅ Sarvam AI client ready (saaras:v3 STT + bulbul:v3 TTS)")
    return _sarvam_client


# ── Text cleaning for TTS ─────────────────────────────────────────────────────
# Abbreviation → spoken form maps.
# Key rule: keep as a single pronounceable word, NOT spaced letters.
_ABBR_EN = {
    'PAN':      'Pan',          # reads as one word, like "pan"
    'TAN':      'Tan',
    'TDS':      'TDS',          # common enough to read as-is
    'KYC':      'KYC',
    'OTP':      'OTP',
    'NRI':      'NRI',
    'GST':      'GST',
    'ITR':      'ITR',
    'HUF':      'HUF',
    'DOB':      'date of birth',
    'eKYC':     'e-KYC',
    'e-KYC':    'e-KYC',
    'NSDL':     'NSDL',
    'UTIITSL':  'UTI-ITSL',
    'Aadhaar':  'Aadhaar',      # leave as-is — TTS handles it fine
    'e.g.':     'for example',
    'i.e.':     'that is',
    'etc.':     'and so on',
    '&':        'and',
}

_ABBR_TA = {
    'PAN':      'பான்',
    'TAN':      'டான்',
    'TDS':      'டிடிஎஸ்',
    'KYC':      'கேஒய்சி',
    'eKYC':     'இ-கேஒய்சி',
    'e-KYC':    'இ-கேஒய்சி',
    'OTP':      'ஒடிபி',
    'NRI':      'என்ஆர்ஐ',
    'GST':      'ஜிஎஸ்டி',
    'ITR':      'ஐடிஆர்',
    'HUF':      'எச்யூஎஃப்',
    'NSDL':     'என்எஸ்டிஎல்',
    'UTIITSL':  'யுடிஐஐடிஎஸ்எல்',
    'Aadhaar':  'ஆதார்',
    'Aadhar':   'ஆதார்',
    'DOB':      'பிறந்த தேதி',
    '&':        'மற்றும்',
    'e.g.':     'எடுத்துக்காட்டாக',
    'i.e.':     'அதாவது',
    'etc.':     'மற்றும் பல',
}

_ABBR_HI = {
    'PAN':      'पैन',
    'TAN':      'टैन',
    'TDS':      'टीडीएस',
    'KYC':      'केवाईसी',
    'eKYC':     'ई-केवाईसी',
    'OTP':      'ओटीपी',
    'NRI':      'एनआरआई',
    'GST':      'जीएसटी',
    'ITR':      'आईटीआर',
    'DOB':      'जन्म तिथि',
    'Aadhaar':  'आधार',
    'Aadhar':   'आधार',
    '&':        'और',
    'e.g.':     'उदाहरण के लिए',
    'i.e.':     'यानी',
    'etc.':     'इत्यादि',
}


def _apply_abbr(text: str, abbr_map: dict) -> str:
    """Replace abbreviations using word-boundary matching (case-sensitive for non-ASCII maps)."""
    for abbr, spoken in abbr_map.items():
        # Use word boundaries for pure-ASCII tokens; plain replace for mixed/special
        if re.match(r'^[A-Za-z0-9.&-]+$', abbr):
            text = re.sub(r'\b' + re.escape(abbr) + r'\b', spoken, text)
        else:
            text = text.replace(abbr, spoken)
    return text


def _table_to_prose(text: str, language: str = "en") -> str:
    """Remove markdown tables entirely — tables are visual; don't read them aloud."""
    lines = text.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('|') and line.endswith('|'):
            # Skip the entire table block
            while i < len(lines) and lines[i].strip().startswith('|'):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return '\n'.join(out)


def _list_to_prose(text: str) -> str:
    """
    Convert markdown bullet/numbered lists into comma-joined prose.
    Groups consecutive list items into one sentence.
    e.g. "- Option A\n- Option B\n- Option C" → "Option A, Option B, and Option C."
    """
    lines = text.split('\n')
    out = []
    group = []

    def flush_group():
        if not group:
            return
        if len(group) == 1:
            out.append(group[0] + '.')
        elif len(group) == 2:
            out.append(f"{group[0]} and {group[1]}.")
        else:
            out.append(', '.join(group[:-1]) + f", and {group[-1]}.")
        group.clear()

    for line in lines:
        stripped = line.strip()
        # Numbered list: "1. Item"
        m_num = re.match(r'^\d+\.\s+(.+)', stripped)
        # Bullet list: "- Item" or "• Item"
        m_bul = re.match(r'^[-•*]\s+(.+)', stripped)

        if m_num:
            group.append(m_num.group(1).strip())
        elif m_bul:
            group.append(m_bul.group(1).strip())
        else:
            flush_group()
            out.append(line)

    flush_group()
    return '\n'.join(out)


def _clean_for_tts(text: str, language: str = "en") -> str:
    """
    Convert any bot response — markdown, tables, lists, abbreviations —
    into natural spoken prose ready for Sarvam bulbul:v3.

    Goals:
    - Abbreviations spoken as words, not letters
    - Tables read as "X is Y" sentences
    - Lists read as "A, B, and C"
    - Questions + their options all preserved (no sentence count limit here)
    - All markdown formatting stripped cleanly
    """
    # 1. Remove LLM thinking blocks
    text = re.sub(r'<think>[\s\S]*?</think>', '', text)

    # 2. Tables → prose BEFORE stripping pipes
    text = _table_to_prose(text, language)

    # 3. Lists → prose BEFORE stripping bullets
    text = _list_to_prose(text)

    # 4. Strip remaining markdown formatting
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)   # bold / italic
    text = re.sub(r'#{1,6}\s?', '', text)                  # headers
    text = re.sub(r'`+[^`]*`+', '', text)                  # inline code
    text = re.sub(r'---+', '', text)                        # hr
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # [label](url)
    text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)  # blockquotes / notes — skip
    text = re.sub(r'\|[-| :]+\|', '', text)                # remaining table separators
    text = re.sub(r'\|', ' ', text)                        # remaining pipes

    # 5. Apply abbreviation map for the language
    abbr_map = {'en': _ABBR_EN, 'ta': _ABBR_TA, 'hi': _ABBR_HI}.get(language, _ABBR_EN)
    text = _apply_abbr(text, abbr_map)

    # 6. Currency → spoken form
    currency_suffix = {'en': ' rupees', 'hi': ' रुपये', 'ta': ' ரூபாய்'}.get(language, ' rupees')
    text = re.sub(r'₹\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + currency_suffix, text)
    text = re.sub(r'\$\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + ' dollars', text)

    # 7. Collapse whitespace (keep single newlines as sentence breaks)
    text = re.sub(r'\n{2,}', '. ', text)   # paragraph break → pause
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()



# ── Audio decode helper ───────────────────────────────────────────────────────
def _decode_to_wav_16k(input_path: str) -> str:
    """Decode any audio format to 16 kHz mono WAV using PyAV."""
    out_path = tempfile.mktemp(suffix=".wav")
    try:
        container = av.open(input_path)
        audio_stream = next((s for s in container.streams if s.type == "audio"), None)
        if audio_stream is None:
            raise ValueError("No audio stream found in uploaded file")

        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        frames = []
        for packet in container.demux(audio_stream):
            for frame in packet.decode():
                for rf in resampler.resample(frame):
                    frames.append(rf.to_ndarray().flatten())
        container.close()

        if not frames:
            raise ValueError("Audio decoded to empty frames")

        audio = np.concatenate(frames).astype(np.int16)
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio.tobytes())
    except Exception as e:
        Path(out_path).unlink(missing_ok=True)
        raise RuntimeError(f"Audio decode failed: {e}")
    return out_path


# ── Off-topic guard ───────────────────────────────────────────────────────────
_OFF_TOPIC_RE = re.compile(
    r"^\s*("
    r"what('?s| is)( the)? weather(\s+\w+)*"
    r"|tell me a joke|give me a joke|say something funny"
    r"|play (some |a |my )?(music|song|playlist|video|youtube)"
    r"|what time is it(\s+now)?"
    r"|who (is|are) (you|your|the)\b"
    r"|set (a |an )?(timer|alarm|reminder)"
    r"|(search|google|look up|find)\s.{2,40}$"
    r"|open (the )?\w+(\s+\w+)? (app|browser|website)"
    r"|(call|text|message|whatsapp) (my )?\w+"
    r"|(hey|ok|okay) (siri|google|alexa|cortana)"
    r")\s*$",
    re.IGNORECASE,
)

def _is_off_topic(t: str) -> bool:
    return bool(_OFF_TOPIC_RE.match(t.strip()))


# ── STT via Sarvam AI saaras:v3 ──────────────────────────────────────────────
def _transcribe_sarvam(wav_path: str, language: str = "en") -> str:
    """
    Send 16 kHz mono WAV file to Sarvam saaras:v3 and return the transcript.
    The file handle is opened fresh each call (Sarvam SDK expects a file-like).
    """
    client = _get_client()
    lang_code = VOICE_CONFIGS.get(language, VOICE_CONFIGS["en"])["stt_language"]

    with open(wav_path, "rb") as f:
        response = client.speech_to_text.transcribe(
            file=f,
            model="saaras:v3",
            mode="transcribe",
            language_code=lang_code,
        )

    # SpeechToTextResponse.transcript
    if hasattr(response, "transcript"):
        return (response.transcript or "").strip()
    if isinstance(response, dict):
        return (response.get("transcript") or "").strip()
    return str(response).strip()


# ── TTS via Sarvam AI bulbul:v3 ──────────────────────────────────────────────
def _synthesise_sarvam(text: str, language: str = "en") -> bytes:
    """
    Send text to Sarvam bulbul:v3 and return a complete WAV bytes object.
    TextToSpeechResponse.audios is a list of base64-encoded WAV strings.
    Each chunk is already a self-contained WAV file — we concatenate the PCM.
    """
    client = _get_client()
    cfg = VOICE_CONFIGS.get(language, VOICE_CONFIGS["en"])

    response = client.text_to_speech.convert(
        model="bulbul:v3",
        text=text,
        target_language_code=cfg["tts_language"],
        speaker=cfg["tts_speaker"],
        speech_sample_rate=22050,
        pace=1.0,   # normal speed — fastest synthesis, clear delivery
    )

    if not (hasattr(response, "audios") and response.audios):
        raise RuntimeError("Sarvam TTS returned no audio data")

    wav_chunks = [base64.b64decode(chunk) for chunk in response.audios]

    if len(wav_chunks) == 1:
        return wav_chunks[0]   # Already a complete WAV

    # Multiple chunks — merge PCM frames into one WAV
    pcm_parts = []
    params = None
    for wav_bytes in wav_chunks:
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            if params is None:
                params = wf.getparams()
            pcm_parts.append(wf.readframes(wf.getnframes()))

    merged = io.BytesIO()
    with wave.open(merged, "wb") as wf:
        wf.setparams(params)
        for pcm in pcm_parts:
            wf.writeframes(pcm)
    return merged.getvalue()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@voice_router.post("/voice/stt")
async def voice_stt(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """
    STT: browser audio (webm/ogg/wav) → { transcript }
    Uses Sarvam AI saaras:v3.
    """
    raw = await audio.read()
    if len(raw) < 1000:
        raise HTTPException(
            status_code=422,
            detail="Audio too short — please speak for at least 1 second.",
        )

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    wav_path = None
    try:
        wav_path = _decode_to_wav_16k(tmp_path)
        transcript = _transcribe_sarvam(wav_path, language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        if wav_path:
            Path(wav_path).unlink(missing_ok=True)

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="Could not hear speech — please speak clearly and try again.",
        )

    return {"transcript": transcript, "language": language}


@voice_router.post("/voice/tts")
async def voice_tts(
    text: str = Form(...),
    language: str = Form(default="en"),
):
    """
    TTS: text → WAV audio.
    Uses Sarvam AI bulbul:v3.
    Aggressively caps text length to minimise Sarvam API latency.
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    clean = _clean_for_tts(text.strip(), language)

    # Cap at 300 chars — enough for 1-2 sentences, keeps Sarvam API fast.
    # The frontend only sends short early-TTS snippets anyway.
    speak_text = clean[:300] if len(clean) > 300 else clean
    if not speak_text:
        raise HTTPException(status_code=400, detail="No speakable text.")

    import asyncio
    loop = asyncio.get_event_loop()

    try:
        wav_bytes = await loop.run_in_executor(
            None,
            lambda: _synthesise_sarvam(speak_text, language),
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"TTS failed: {e}")

    return StreamingResponse(
        io.BytesIO(wav_bytes),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


@voice_router.post("/voice/speak")
async def voice_speak(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
    session_id: str = Form(default=None),
):
    """
    Full pipeline: STT → off-topic guard → RAG+LLM → TTS.
    Returns audio/wav with X-Transcript and X-Reply headers.
    Falls back to JSON if TTS fails.
    """
    import asyncio
    from urllib.parse import quote

    # ── Step 1: STT ───────────────────────────────────────────────────────────
    raw = await audio.read()
    if len(raw) < 1000:
        raise HTTPException(
            status_code=422,
            detail="Audio too short — please speak for at least 1 second.",
        )

    lang = language if language in ("en", "ta", "hi") else "en"
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    wav_path = None
    transcript = ""

    try:
        wav_path = _decode_to_wav_16k(tmp_path)
        transcript = _transcribe_sarvam(wav_path, lang)

        # Fallback to English if the selected language yields nothing
        if not transcript and lang != "en":
            print(f"[VOICE] {lang} transcription empty — retrying in English")
            transcript = _transcribe_sarvam(wav_path, "en")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        if wav_path:
            Path(wav_path).unlink(missing_ok=True)

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="Could not hear speech — please speak clearly and try again.",
        )

    print(f"[VOICE] Transcript ({lang}): {transcript}")

    # ── Step 2: Off-topic guard ───────────────────────────────────────────────
    if _is_off_topic(transcript):
        _redirect = {
            "en": "I'm your PAN card assistant. I can only help with PAN registration, Aadhaar linking, TAN, TDS, and related income tax topics. What PAN-related question can I help you with?",
            "ta": "நான் உங்கள் PAN கார்டு உதவியாளர். PAN பதிவு, ஆதார் இணைப்பு, TAN, TDS மற்றும் வருமான வரி தொடர்பான கேள்விகளுக்கு மட்டுமே உதவ முடியும்.",
            "hi": "मैं आपका PAN कार्ड सहायक हूँ। केवल PAN पंजीकरण, आधार लिंकिंग, TAN, TDS और आयकर संबंधी प्रश्नों में मदद कर सकता हूँ।",
        }
        reply = _redirect.get(lang, _redirect["en"])
        print(f"[VOICE] Off-topic rejected: {transcript!r}")
        loop = asyncio.get_event_loop()
        try:
            clean = _clean_for_tts(reply, lang)
            wav_bytes = await loop.run_in_executor(None, lambda: _synthesise_sarvam(clean, lang))
            return StreamingResponse(
                io.BytesIO(wav_bytes),
                media_type="audio/wav",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Transcript": quote(transcript),
                    "X-Reply": quote(reply),
                },
            )
        except Exception:
            pass
        return {"transcript": transcript, "reply": reply, "audio_available": False}

    # ── Step 3: RAG + LLM ────────────────────────────────────────────────────
    print(f"[VOICE] Processing — lang: {lang}, session: {session_id or 'anonymous'}")
    try:
        from api.chain_instance import get_chain
        result = get_chain().run(
            question=transcript,
            session_id=session_id or f"voice_{lang}",
            user_id="voice_user",
            user_context="",
            account_email="",
            language_override=lang,
        )
        reply = result.get("answer", "")
        print(f"[VOICE] Reply: {reply[:100]}...")
    except Exception as e:
        print(f"[VOICE] RAG failed: {e}")
        reply = {
            "ta": "மன்னிக்கவும், செயல்படுத்துவதில் சிக்கல். மீண்டும் முயற்சிக்கவும்.",
            "hi": "माफ़ कीजिए, प्रक्रिया में समस्या है। कृपया पुनः प्रयास करें।",
            "en": "I'm having trouble processing that. Please try again.",
        }.get(lang, "I'm having trouble processing that. Please try again.")

    if not reply:
        reply = {
            "en": "I can help you with PAN card services. What would you like to know?",
            "ta": "PAN கார்டு சேவைகளில் உதவ முடியும். என்ன தெரிய வேண்டும்?",
            "hi": "PAN कार्ड सेवाओं में मदद कर सकता हूँ। क्या जानना चाहते हैं?",
        }.get(lang, "I can help you with PAN card services.")

    # ── Step 4: Translate if needed, then TTS ────────────────────────────────
    if lang in ("ta", "hi"):
        try:
            from agent.translator import translate_response as _translate
            reply = _translate(reply, lang)
        except Exception:
            pass

    clean = _clean_for_tts(reply, lang)
    # Read the full reply — questions, options, tables all included
    speak_text = clean[:2400] if len(clean) > 2400 else clean

    if not speak_text:
        return {"transcript": transcript, "reply": reply, "audio_available": False}

    loop = asyncio.get_event_loop()
    try:
        wav_bytes = await loop.run_in_executor(
            None, lambda: _synthesise_sarvam(speak_text, lang)
        )
        return StreamingResponse(
            io.BytesIO(wav_bytes),
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-cache",
                "X-Transcript": quote(transcript),
                "X-Reply": quote(reply),
            },
        )
    except Exception as e:
        print(f"[VOICE] TTS failed: {e}")
        return {"transcript": transcript, "reply": reply, "audio_available": False}
