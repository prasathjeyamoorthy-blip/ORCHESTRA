# api/voice.py
"""
Voice endpoints:
  POST /api/voice/stt  — audio → transcript JSON
  POST /api/voice/tts  — text  → WAV audio

STT: openai/whisper-large-v3 via NVIDIA NIM cloud gRPC
     Server: grpc.nvcf.nvidia.com:443
     Key:    STT_API_KEY (from .env)

TTS: nvidia/magpie-tts-multilingual via NVIDIA NIM cloud gRPC
     Server: grpc.nvcf.nvidia.com:443
     Key:    TTS_API_KEY (from .env)
"""

import sys
import io
import re
import wave
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import av
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse

voice_router = APIRouter()

# ── NVIDIA NIM credentials ────────────────────────────────────────────────────
import os
from dotenv import load_dotenv
load_dotenv()

_GRPC_SERVER   = "grpc.nvcf.nvidia.com:443"
_ASR_FUNC_ID   = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"   # whisper-large-v3
_TTS_FUNC_ID   = "877104f7-e885-42b9-8de8-f6e4c6303969"   # magpie-tts-multilingual
_ASR_API_KEY   = os.getenv("STT_API_KEY") or os.getenv("NVIDIA_API_KEY")
_TTS_API_KEY   = os.getenv("TTS_API_KEY") or os.getenv("NVIDIA_API_KEY")
_TTS_VOICE     = os.getenv("TTS_VOICE",    "Magpie-Multilingual.EN-US.Aria")
_TTS_LANGUAGE  = "en-US"
_TTS_RATE      = 22050   # Hz — Magpie output sample rate

# Voice configurations for different languages
VOICE_CONFIGS = {
    "en": {
        "tts_voice": "Magpie-Multilingual.EN-US.Aria",
        "tts_language": "en-US",
        "stt_language": "en-US",
        "display_name": "English"
    },
    "ta": {
        "tts_voice": "Magpie-Multilingual.TA-IN.Anjali",  # Native Tamil voice
        "tts_language": "ta-IN",
        "stt_language": "ta-IN",
        "display_name": "Tamil (தமிழ்)"
    },
    "hi": {
        "tts_voice": "Magpie-Multilingual.HI-IN.Aditi",  # Native Hindi voice
        "tts_language": "hi-IN",
        "stt_language": "hi-IN",
        "display_name": "Hindi (हिंदी)"
    }
}

if not _ASR_API_KEY or not _TTS_API_KEY:
    raise EnvironmentError(
        "NVIDIA_API_KEY (or STT_API_KEY/TTS_API_KEY) is not set in pan-rag/.env"
    )

# ── Lazy-loaded Riva clients ──────────────────────────────────────────────────
_asr_service = None
_tts_service = None

def _get_asr():
    global _asr_service
    if _asr_service is None:
        try:
            import riva.client as riva
            auth = riva.Auth(
                uri=_GRPC_SERVER,
                use_ssl=True,
                metadata_args=[
                    ["function-id",   _ASR_FUNC_ID],
                    ["authorization", f"Bearer {_ASR_API_KEY}"],
                ],
            )
            _asr_service = riva.ASRService(auth)
            print("✅ NVIDIA NIM STT (whisper-large-v3) connected")
        except ImportError:
            print("⚠️  nvidia-riva-client not installed. Run: pip install nvidia-riva-client")
            _asr_service = "unavailable"
        except Exception as e:
            print(f"⚠️  NVIDIA NIM STT unavailable: {e}")
            _asr_service = "unavailable"
    return None if _asr_service == "unavailable" else _asr_service

def _get_tts():
    global _tts_service
    if _tts_service is None:
        try:
            import riva.client as riva
            auth = riva.Auth(
                uri=_GRPC_SERVER,
                use_ssl=True,
                metadata_args=[
                    ["function-id",   _TTS_FUNC_ID],
                    ["authorization", f"Bearer {_TTS_API_KEY}"],
                ],
            )
            _tts_service = riva.SpeechSynthesisService(auth)
            print("✅ NVIDIA NIM TTS (magpie-tts-multilingual) connected")
        except ImportError:
            print("⚠️  nvidia-riva-client not installed. Run: pip install nvidia-riva-client")
            _tts_service = "unavailable"
        except Exception as e:
            print(f"⚠️  NVIDIA NIM TTS unavailable: {e}")
            _tts_service = "unavailable"
    return None if _tts_service == "unavailable" else _tts_service


# ── Text cleaning for TTS ─────────────────────────────────────────────────────
def _clean_for_tts(text: str, language: str = "en") -> str:
    """
    Strip markdown and format text for natural speech synthesis.
    Makes the voice output sound more conversational and understandable.
    Handles English, Tamil, and Hindi text appropriately.
    """
    # Remove thinking tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Remove markdown formatting
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)  # Bold/italic
    text = re.sub(r'#{1,6}\s?', '', text)  # Headers
    text = re.sub(r'`+[^`]*`+', '', text)  # Code blocks
    text = re.sub(r'---+', '', text)  # Horizontal rules
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
    
    # Remove list markers but keep the content
    text = re.sub(r'[-–—•]\s+', '', text)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # Numbered lists
    
    # Remove table formatting
    text = re.sub(r'\|[-| :]+\|', '', text)  # Table separators
    text = re.sub(r'\|', ' ', text)  # Remaining pipes
    
    # Language-specific cleaning
    if language == "en":
        # Convert abbreviations to full words for better pronunciation
        text = text.replace('e.g.', 'for example')
        text = text.replace('i.e.', 'that is')
        text = text.replace('etc.', 'and so on')
        text = text.replace('&', 'and')
        text = text.replace('vs.', 'versus')
        text = text.replace('approx.', 'approximately')
        
        # Handle common acronyms - spell them out or make them pronounceable
        text = text.replace('PAN', 'P A N')
        text = text.replace('TAN', 'T A N')
        text = text.replace('TDS', 'T D S')
        text = text.replace('KYC', 'K Y C')
        text = text.replace('OTP', 'O T P')
        text = text.replace('DOB', 'date of birth')
        text = text.replace('eKYC', 'e K Y C')
        text = text.replace('Aadhaar', 'Aadhar')  # Simplified pronunciation
        
    elif language == "ta":
        # Tamil-specific cleaning
        # Keep Tamil script as-is, but clean English acronyms if mixed
        text = text.replace('PAN', 'பான்')
        text = text.replace('KYC', 'கே வை சி')
        text = text.replace('OTP', 'ஓ டி பி')
        text = text.replace('&', 'மற்றும்')
        text = text.replace('Aadhaar', 'ஆதார்')
        
    elif language == "hi":
        # Hindi-specific cleaning
        # Keep Devanagari script as-is, but clean English acronyms if mixed
        text = text.replace('PAN', 'पैन')
        text = text.replace('KYC', 'के वाई सी')
        text = text.replace('OTP', 'ओ टी पी')
        text = text.replace('&', 'और')
        text = text.replace('Aadhaar', 'आधार')
    
    # Handle currency - make it sound natural (works for all languages)
    text = re.sub(r'₹\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + (' rupees' if language == 'en' else ' रुपये' if language == 'hi' else ' ரூபாய்'), text)
    text = re.sub(r'\$\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + (' dollars' if language == 'en' else ' डॉलर' if language == 'hi' else ' டாலர்'), text)
    
    # Handle numbers and dates more naturally
    text = re.sub(r'\b(\d{2})/(\d{2})/(\d{4})\b', r'\1 \2 \3', text)  # Dates
    
    # Clean up whitespace
    text = re.sub(r'\n+', ' ', text)  # Replace newlines with spaces
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
    
    # Add natural pauses for better speech flow
    text = text.replace('. ', '. ')  # Ensure space after periods
    text = text.replace('? ', '? ')  # Ensure space after questions
    text = text.replace('! ', '! ')  # Ensure space after exclamations
    
    return text.strip()


# ── Audio decode helper ───────────────────────────────────────────────────────
def _decode_to_wav_16k(input_path: str) -> str:
    """Decode any audio format to 16kHz mono WAV using PyAV."""
    out_path = tempfile.mktemp(suffix=".wav")
    try:
        container = av.open(input_path)
        audio_stream = next((s for s in container.streams if s.type == "audio"), None)
        if audio_stream is None:
            raise ValueError("No audio stream found")

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


def _read_wav_pcm(path: str) -> bytes:
    """Read WAV and return raw PCM bytes (strips header)."""
    with wave.open(path, "rb") as wf:
        return wf.readframes(wf.getnframes())


# ── PAN domain vocabulary — injected as Whisper initial_prompt ───────────────
# Whisper uses this as a "soft" prior to bias transcription toward these terms.
# This dramatically improves accuracy for PAN/Aadhaar/tax domain speech.
_STT_INITIAL_PROMPTS = {
    "en": (
        "PAN card application, Aadhaar, TAN, TDS, income tax, Form 49A, eKYC, "
        "NSDL, UTIITSL, Protean, annual income, submission mode, delivery mode, "
        "residential status, source of income, mother name, date of birth, "
        "representative assessee, address for communication, e-PAN, digital signature."
    ),
    "ta": (
        "PAN அட்டை விண்ணப்பம், ஆதார், TAN, TDS, வருமான வரி, eKYC, "
        "வருமான மூலம், சமர்ப்பிக்கும் முறை, விநியோக முறை, குடியிருப்பு நிலை, "
        "தாயின் பெயர், முழு பெயர், மின்னஞ்சல், ஆண்டு வருமானம்."
    ),
    "hi": (
        "पैन कार्ड आवेदन, आधार, टैन, टीडीएस, आयकर, eKYC, "
        "वार्षिक आय, जमा करने का तरीका, डिलीवरी मोड, आवासीय स्थिति, "
        "आय का स्रोत, माता का नाम, पूरा नाम, ईमेल."
    ),
}

# ── Off-topic guard — reject transcripts clearly unrelated to PAN ─────────────
# Only blocks obviously unrelated content; PAN queries always pass.
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

def _is_off_topic_voice(transcript: str) -> bool:
    """Return True if transcript is clearly unrelated to PAN/tax services."""
    return bool(_OFF_TOPIC_RE.match(transcript.strip()))

# ── STT via NVIDIA NIM ────────────────────────────────────────────────────────
def _transcribe_nvidia(audio_path: str, language: str = "en") -> str:
    """
    Send 16kHz mono WAV to NVIDIA NIM whisper-large-v3 via gRPC.
    Injects a PAN-domain initial_prompt to bias Whisper toward PAN vocabulary.
    Supports multiple languages: en-US, ta-IN, hi-IN
    """
    import riva.client as riva

    asr = _get_asr()
    if asr is None:
        raise RuntimeError("NVIDIA NIM STT service not available")

    pcm_bytes = _read_wav_pcm(audio_path)
    
    voice_config = VOICE_CONFIGS.get(language, VOICE_CONFIGS["en"])
    language_code = voice_config["stt_language"]

    asr_config = riva.RecognitionConfig(
        language_code=language_code,
        max_alternatives=1,
        enable_automatic_punctuation=True,
        audio_channel_count=1,
        sample_rate_hertz=16000,
        encoding=riva.AudioEncoding.LINEAR_PCM,
        # Bias Whisper toward PAN/tax vocabulary for higher domain accuracy
        # initial_prompt is supported by NVIDIA NIM Whisper
    )

    # Inject domain prompt if the API supports it
    try:
        initial_prompt = _STT_INITIAL_PROMPTS.get(language, _STT_INITIAL_PROMPTS["en"])
        asr_config_with_prompt = riva.RecognitionConfig(
            language_code=language_code,
            max_alternatives=1,
            enable_automatic_punctuation=True,
            audio_channel_count=1,
            sample_rate_hertz=16000,
            encoding=riva.AudioEncoding.LINEAR_PCM,
            initial_prompt=initial_prompt,
        )
        resp = asr.offline_recognize(pcm_bytes, asr_config_with_prompt)
    except (TypeError, AttributeError):
        # initial_prompt not supported by this Riva version — fall back silently
        resp = asr.offline_recognize(pcm_bytes, asr_config)

    if not resp.results:
        return ""
    return " ".join(
        r.alternatives[0].transcript
        for r in resp.results
        if r.alternatives
    ).strip()


# ── TTS via NVIDIA NIM ────────────────────────────────────────────────────────
def _synthesise_nvidia(text: str, language: str = "en") -> bytes:
    """
    Send text to NVIDIA NIM magpie-tts-multilingual, return LINEAR_PCM bytes.
    Supports multiple languages with appropriate voice selection.
    """
    import riva.client as riva

    tts = _get_tts()
    if tts is None:
        raise RuntimeError("NVIDIA NIM TTS service not available")

    # Get voice configuration for the language
    voice_config = VOICE_CONFIGS.get(language, VOICE_CONFIGS["en"])
    
    resp = tts.synthesize(
        text,
        voice_name=voice_config["tts_voice"],
        language_code=voice_config["tts_language"],
        encoding=riva.AudioEncoding.LINEAR_PCM,
        sample_rate_hz=_TTS_RATE,
    )
    return resp.audio   # raw 16-bit mono PCM at _TTS_RATE Hz


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    """Wrap raw PCM bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@voice_router.post("/voice/stt")
async def voice_stt(audio: UploadFile = File(...), language: str = Form(default="en")):
    """
    STT: browser audio (webm/ogg/wav) → { transcript }
    Uses NVIDIA NIM openai/whisper-large-v3 via cloud gRPC.
    Supports multiple languages: en, ta, hi
    """
    raw = await audio.read()
    if len(raw) < 1000:
        raise HTTPException(status_code=422, detail="Audio too short — please speak for at least 1 second.")

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    wav_path = None
    try:
        # Decode to 16kHz mono WAV
        wav_path = _decode_to_wav_16k(tmp_path)
        # Transcribe via NVIDIA NIM with specified language
        transcript = _transcribe_nvidia(wav_path, language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        if wav_path:
            Path(wav_path).unlink(missing_ok=True)

    if not transcript or not transcript.strip():
        raise HTTPException(status_code=422, detail="Could not hear speech — please speak clearly and try again.")

    return {"transcript": transcript.strip(), "language": language}


@voice_router.post("/voice/tts")
async def voice_tts(text: str = Form(...), language: str = Form(default="en")):
    """
    TTS: text → WAV audio
    Uses NVIDIA NIM nvidia/magpie-tts-multilingual via cloud gRPC.
    Speaks only the first 2 sentences for conversational speed.
    Supports multiple languages (en, ta, hi).
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    # Clean markdown and limit to first 2 sentences (with language-specific cleaning)
    clean = _clean_for_tts(text.strip(), language)
    # Handle Tamil/Hindi sentence endings
    sentences = [s.strip() for s in re.split(r'(?<=[.!?।॥])\s+', clean) if s.strip()]
    speak_text = ' '.join(sentences[:2])
    if not speak_text:
        raise HTTPException(status_code=400, detail="No speakable text.")

    import asyncio
    loop = asyncio.get_event_loop()

    try:
        pcm_bytes = await loop.run_in_executor(
            None, 
            lambda: _synthesise_nvidia(speak_text, language)
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"TTS failed: {e}")

    if not pcm_bytes:
        raise HTTPException(status_code=503, detail="TTS generated no audio.")

    wav_bytes = _pcm_to_wav(pcm_bytes, _TTS_RATE)

    return StreamingResponse(
        io.BytesIO(wav_bytes),
        media_type="audio/wav",
        headers={"Cache-Control": "no-cache"},
    )


@voice_router.post("/voice/speak")
async def voice_speak(audio: UploadFile = File(...), language: str = Form(default="en")):
    """
    Full voice pipeline: STT → PAN domain validation → RAG+LLM → TTS

    - Biases Whisper STT with PAN vocabulary initial_prompt for accuracy
    - Rejects clearly off-topic speech with a polite redirect
    - Passes transcript through full RAG chain with language context
    - Synthesizes response to speech (TTS)

    Returns:
        audio/wav with X-Transcript and X-Reply headers,
        or JSON fallback if TTS fails.
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

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    wav_path = None
    transcript = ""
    # Use the language the user has selected in the UI (passed as form field)
    # This skips the double-transcription and is more reliable for Tamil/Hindi
    detected_language = language if language in ("en", "ta", "hi") else "en"

    try:
        wav_path = _decode_to_wav_16k(tmp_path)
        # Transcribe in the user's selected language with PAN domain prompt
        transcript = _transcribe_nvidia(wav_path, detected_language)

        # If Tamil/Hindi produced empty result, try English as fallback
        if not transcript and detected_language != "en":
            print(f"[VOICE] {detected_language} transcription empty — retrying in English")
            transcript = _transcribe_nvidia(wav_path, "en")
            detected_language = "en"

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        if wav_path:
            Path(wav_path).unlink(missing_ok=True)

    if not transcript or not transcript.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not hear speech — please speak clearly and try again.",
        )

    print(f"[VOICE] Transcript ({detected_language}): {transcript}")

    # ── Step 2: PAN domain guard ──────────────────────────────────────────────
    # Politely redirect clearly off-topic speech instead of processing it.
    if _is_off_topic_voice(transcript):
        _redirect = {
            "en": "I'm your PAN card assistant. I can only help with PAN registration, Aadhaar linking, TAN, TDS, and related income tax topics. What PAN-related question can I help you with?",
            "ta": "நான் உங்கள் PAN கார்டு உதவியாளர். PAN பதிவு, ஆதார் இணைப்பு, TAN, TDS மற்றும் வருமான வரி தொடர்பான கேள்விகளுக்கு மட்டுமே உதவ முடியும். என்ன PAN கேள்வி உள்ளது?",
            "hi": "मैं आपका PAN कार्ड सहायक हूँ। केवल PAN पंजीकरण, आधार लिंकिंग, TAN, TDS और आयकर संबंधी प्रश्नों में मदद कर सकता हूँ।",
        }
        reply = _redirect.get(detected_language, _redirect["en"])
        print(f"[VOICE] Off-topic rejected: {transcript!r}")

        clean = _clean_for_tts(reply, detected_language)
        loop = asyncio.get_event_loop()
        try:
            pcm_bytes = await loop.run_in_executor(None, lambda: _synthesise_nvidia(clean, detected_language))
            if pcm_bytes:
                wav_bytes = _pcm_to_wav(pcm_bytes, _TTS_RATE)
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

    # ── Step 3: RAG+LLM ───────────────────────────────────────────────────────
    print(f"[VOICE] Processing with language: {detected_language}")

    try:
        from api.chain_instance import get_chain

        result = get_chain().run(
            question=transcript,
            session_id=None,
            user_id="voice_user",
            user_context="",
            account_email="",
            language_override=detected_language,
        )
        reply = result.get("answer", "")
        print(f"[VOICE] Reply: {reply[:100]}...")

    except Exception as e:
        print(f"[VOICE] RAG failed: {e}")
        _err = {
            "ta": "மன்னிக்கவும், செயல்படுத்துவதில் சிக்கல். மீண்டும் முயற்சிக்கவும்.",
            "hi": "माफ़ कीजिए, प्रक्रिया में समस्या है। कृपया पुनः प्रयास करें।",
            "en": "I'm having trouble processing that. Please try again.",
        }
        reply = _err.get(detected_language, _err["en"])

    if not reply:
        reply = {
            "en": "I can help you with PAN card services. What would you like to know?",
            "ta": "PAN கார்டு சேவைகளில் உதவ முடியும். என்ன தெரிய வேண்டும்?",
            "hi": "PAN कार्ड सेवाओं में मदद कर सकता हूँ। क्या जानना चाहते हैं?",
        }.get(detected_language, "I can help you with PAN card services.")

    # ── Step 4: TTS ───────────────────────────────────────────────────────────
    clean = _clean_for_tts(reply, detected_language)
    # Split on sentence boundaries — Tamil uses '. ' and '! ', Hindi uses '।'
    sentences = [s.strip() for s in re.split(r'(?<=[.!?।॥])\s+', clean) if s.strip()]
    speak_text = ' '.join(sentences[:3])

    if not speak_text:
        return {"transcript": transcript, "reply": reply, "audio_available": False}

    loop = asyncio.get_event_loop()
    try:
        pcm_bytes = await loop.run_in_executor(
            None, lambda: _synthesise_nvidia(speak_text, detected_language)
        )
        if not pcm_bytes:
            return {"transcript": transcript, "reply": reply, "audio_available": False}

        wav_bytes = _pcm_to_wav(pcm_bytes, _TTS_RATE)
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
