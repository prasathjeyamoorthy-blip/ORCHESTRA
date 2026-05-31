"""
server.py — FastAPI HTTP server for the voice agent

Endpoints:
  POST /api/voice/stt   — audio blob → { transcript }
  POST /api/voice/speak — audio blob → audio/wav (full pipeline: STT → RAG+LLM → TTS)

Run: uvicorn server:app --host 0.0.0.0 --port 8002
"""

import io
import os
import struct
import tempfile
import subprocess

import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from core.llm import OllamaLLM
from rag.retriever import RAGRetriever
import config

app = FastAPI(title="Voice Agent API")


# ── Singletons ────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    import asyncio
    from faster_whisper import WhisperModel
    from core.tts import TextToSpeech

    print("  Loading faster-whisper (base.en)...")
    # Load in thread pool so it doesn't block the event loop
    loop = asyncio.get_event_loop()
    app.state.whisper = await loop.run_in_executor(
        None, lambda: WhisperModel("base.en", device="cpu", compute_type="int8")
    )
    print("  ✅ STT ready (faster-whisper base.en, local)")
    app.state.tts = await loop.run_in_executor(None, TextToSpeech)
    app.state.llm = OllamaLLM()
    app.state.rag = RAGRetriever()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 22050) -> bytes:
    """Wrap raw 16-bit mono PCM in a WAV container."""
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(pcm_bytes)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate,
                          sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(pcm_bytes)))
    buf.write(pcm_bytes)
    return buf.getvalue()


def _transcribe_upload(audio: bytes, content_type: str) -> str:
    """
    Transcribe browser audio (webm/opus) using faster-whisper locally.
    Pipeline: webm → ffmpeg → 16kHz WAV → normalize → whisper
    """
    import wave

    is_ogg = b"OggS" in audio[:8] or "ogg" in (content_type or "")
    suffix = ".ogg" if is_ogg else ".webm"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        tmp_in.write(audio)
        tmp_in_path = tmp_in.name

    tmp_wav = tmp_in_path.replace(suffix, ".wav")

    try:
        # 1. Convert to 16kHz mono 16-bit WAV
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_in_path,
             "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
             "-acodec", "pcm_s16le", tmp_wav],
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"[STT] ffmpeg error: {result.stderr.decode()[-200:]}")
            return ""

        wav_size = os.path.getsize(tmp_wav) if os.path.exists(tmp_wav) else 0
        if wav_size < 500:
            print(f"[STT] WAV too small: {wav_size} bytes")
            return ""

        # 2. Read PCM and check quality
        with wave.open(tmp_wav, "rb") as wf:
            pcm = wf.readframes(wf.getnframes())
            sr = wf.getframerate()
            ch = wf.getnchannels()

        duration = len(pcm) / (sr * ch * 2)
        samples = struct.unpack(f"<{len(pcm)//2}h", pcm)
        rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
        peak = max(abs(s) for s in samples)
        print(f"[STT] {duration:.1f}s, RMS={rms:.0f}, Peak={peak}")

        if duration < 0.5:
            print("[STT] Too short")
            return ""
        if rms < 5:
            print("[STT] Silent")
            return ""

        # Normalize only if actually clipping (peak > 28000)
        if peak > 28000:
            scale = 16000.0 / peak
            norm = struct.pack(
                f"<{len(samples)}h",
                *[max(-32768, min(32767, int(s * scale))) for s in samples]
            )
            with wave.open(tmp_wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(norm)
            print(f"[STT] Normalized peak {peak}→{int(peak*scale)}")
        # Boost if too quiet (peak < 3000 — whisper struggles with very quiet audio)
        elif peak < 3000 and peak > 50:
            scale = 8000.0 / peak
            boosted = struct.pack(
                f"<{len(samples)}h",
                *[max(-32768, min(32767, int(s * scale))) for s in samples]
            )
            with wave.open(tmp_wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(boosted)
            print(f"[STT] Boosted peak {peak}→{int(peak*scale)}")

        # 4. Transcribe — try without VAD first, fall back to with VAD
        for use_vad in [False, True]:
            kwargs = dict(
                language="en",
                beam_size=5,
                temperature=[0.0, 0.2, 0.4],  # fallback temperatures
                condition_on_previous_text=False,
                no_speech_threshold=0.95,
                log_prob_threshold=-3.0,
                compression_ratio_threshold=3.0,
            )
            if use_vad:
                kwargs["vad_filter"] = True
                kwargs["vad_parameters"] = dict(threshold=0.05, min_speech_duration_ms=100, speech_pad_ms=500)

            segments, info = app.state.whisper.transcribe(tmp_wav, **kwargs)
            transcript = " ".join(s.text.strip() for s in segments).strip()
            print(f"[STT] vad={use_vad}: '{transcript}' (lang_prob={info.language_probability:.2f})")

            if transcript and not (transcript.startswith("*") and transcript.endswith("*")):
                return transcript.strip(" .,")

        print("[STT] No speech detected")
        return ""

    except Exception as e:
        print(f"[STT] Error: {e}")
        import traceback; traceback.print_exc()
        return ""
    finally:
        for p in [tmp_in_path, tmp_wav]:
            try:
                os.unlink(p)
            except OSError:
                pass


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/voice/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """audio blob → { transcript }"""
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")
    transcript = _transcribe_upload(data, audio.content_type or "")
    if not transcript:
        raise HTTPException(status_code=422, detail="Could not hear speech. Please try again.")
    return {"transcript": transcript}


@app.post("/api/voice/speak")
async def voice_speak(audio: UploadFile = File(...)):
    """
    Full pipeline: audio blob → STT → RAG+LLM → TTS → audio/wav response.
    """
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # 1. STT — opus direct path, no quality loss
    transcript = _transcribe_upload(data, audio.content_type or "")
    if not transcript:
        raise HTTPException(status_code=422, detail="Could not hear speech. Please try again.")
    if transcript == "HALLUCINATION":
        raise HTTPException(status_code=422, detail="Couldn't make out what you said. Please speak clearly into the mic.")

    # 2. RAG + LLM
    context = app.state.rag.get_context(transcript)
    reply = app.state.llm.chat(transcript, context=context)

    # 3. TTS
    all_pcm = app.state.tts.synthesise_full(reply)

    import urllib.parse
    if not all_pcm:
        # TTS failed — still return transcript+reply as JSON so chat works
        print("[TTS] synthesis returned empty — returning text-only response")
        from fastapi.responses import JSONResponse
        return JSONResponse({
            "transcript": transcript,
            "reply": reply,
            "tts_failed": True,
        })

    wav_bytes = _pcm_to_wav_bytes(all_pcm, sample_rate=config.TTS_SAMPLE_RATE)

    return StreamingResponse(
        io.BytesIO(wav_bytes),
        media_type="audio/wav",
        headers={
            "X-Transcript": urllib.parse.quote(transcript),
            "X-Reply":      urllib.parse.quote(reply),
            "Access-Control-Expose-Headers": "X-Transcript, X-Reply",
        },
    )
