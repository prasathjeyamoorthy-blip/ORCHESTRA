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
def _clean_for_tts(text: str) -> str:
    """Strip markdown so TTS doesn't read symbols aloud."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'#{1,6}\s?', '', text)
    text = re.sub(r'`+[^`]*`+', '', text)
    text = re.sub(r'---+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[-–—•]\s+', '', text)
    text = re.sub(r'\|[-| :]+\|', '', text)   # table separators
    text = re.sub(r'\|', ' ', text)            # remaining pipes
    text = text.replace('e.g.', 'for example').replace('i.e.', 'that is')
    text = text.replace('etc.', 'and so on').replace('&', 'and')
    text = re.sub(r'₹\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + ' rupees', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
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


# ── STT via NVIDIA NIM ────────────────────────────────────────────────────────
def _transcribe_nvidia(audio_path: str) -> str:
    """Send 16kHz mono WAV to NVIDIA NIM whisper-large-v3 via gRPC."""
    import riva.client as riva

    asr = _get_asr()
    if asr is None:
        raise RuntimeError("NVIDIA NIM STT service not available")

    pcm_bytes = _read_wav_pcm(audio_path)

    asr_config = riva.RecognitionConfig(
        language_code="en-US",
        max_alternatives=1,
        enable_automatic_punctuation=True,
        audio_channel_count=1,
        sample_rate_hertz=16000,
        encoding=riva.AudioEncoding.LINEAR_PCM,
    )

    resp = asr.offline_recognize(pcm_bytes, asr_config)
    if not resp.results:
        return ""
    return " ".join(
        r.alternatives[0].transcript
        for r in resp.results
        if r.alternatives
    ).strip()


# ── TTS via NVIDIA NIM ────────────────────────────────────────────────────────
def _synthesise_nvidia(text: str) -> bytes:
    """Send text to NVIDIA NIM magpie-tts-multilingual, return LINEAR_PCM bytes."""
    import riva.client as riva

    tts = _get_tts()
    if tts is None:
        raise RuntimeError("NVIDIA NIM TTS service not available")

    resp = tts.synthesize(
        text,
        voice_name=_TTS_VOICE,
        language_code=_TTS_LANGUAGE,
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
async def voice_stt(audio: UploadFile = File(...)):
    """
    STT: browser audio (webm/ogg/wav) → { transcript }
    Uses NVIDIA NIM openai/whisper-large-v3 via cloud gRPC.
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
        # Transcribe via NVIDIA NIM
        transcript = _transcribe_nvidia(wav_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        if wav_path:
            Path(wav_path).unlink(missing_ok=True)

    if not transcript or not transcript.strip():
        raise HTTPException(status_code=422, detail="Could not hear speech — please speak clearly and try again.")

    return {"transcript": transcript.strip()}


@voice_router.post("/voice/tts")
async def voice_tts(text: str = Form(...)):
    """
    TTS: text → WAV audio
    Uses NVIDIA NIM nvidia/magpie-tts-multilingual via cloud gRPC.
    Speaks only the first 2 sentences for conversational speed.
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    # Clean markdown and limit to first 2 sentences
    clean = _clean_for_tts(text.strip())
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if s.strip()]
    speak_text = ' '.join(sentences[:2])
    if not speak_text:
        raise HTTPException(status_code=400, detail="No speakable text.")

    import asyncio
    loop = asyncio.get_event_loop()

    try:
        pcm_bytes = await loop.run_in_executor(None, lambda: _synthesise_nvidia(speak_text))
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
