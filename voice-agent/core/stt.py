"""
core/stt.py — Speech to Text via Sarvam AI (saaras:v3)
"""

import os
import wave
import tempfile
import numpy as np
import sounddevice as sd

import config


# ── Lazy Sarvam client ────────────────────────────────────────
_sarvam_client = None

def _get_client():
    global _sarvam_client
    if _sarvam_client is None:
        from sarvamai import SarvamAI
        _sarvam_client = SarvamAI(api_subscription_key=config.SARVAM_API_KEY)
        print("  STT → Sarvam AI saaras:v3")
    return _sarvam_client


def _read_wav_info(path: str) -> tuple[bytes, int, int]:
    """Read WAV file, return (pcm_bytes, sample_rate, channels)."""
    with wave.open(path, "rb") as wf:
        return wf.readframes(wf.getnframes()), wf.getframerate(), wf.getnchannels()


class SpeechToText:

    def __init__(self):
        # Eagerly validate key and init client on startup
        _get_client()
        print("  ✅ STT ready (Sarvam saaras:v3)")

    # ── Recording (CLI mode only) ──────────────────────────────

    def record(self) -> str:
        """Record from mic until silence. Returns path to temp WAV."""
        print("\n🎤 Listening... (speak now)")

        recorded_chunks = []
        speaking_started = False
        silent_chunk_count = 0

        CHUNK_MS       = 100
        CHUNK_SIZE     = int(config.SAMPLE_RATE * CHUNK_MS / 1000)
        silence_needed = int(config.SILENCE_DURATION * 1000 / CHUNK_MS)
        max_chunks     = int(config.MAX_RECORD_SECS * 1000 / CHUNK_MS)

        def callback(indata, frames, time, status):
            recorded_chunks.append(indata.copy())

        with sd.InputStream(samplerate=config.SAMPLE_RATE, channels=1,
                            dtype="float32", blocksize=CHUNK_SIZE, callback=callback):
            for _ in range(max_chunks):
                sd.sleep(CHUNK_MS)
                if not recorded_chunks:
                    continue
                volume = float(np.abs(recorded_chunks[-1]).mean())
                if volume > config.SILENCE_THRESHOLD:
                    speaking_started = True
                    silent_chunk_count = 0
                elif speaking_started:
                    silent_chunk_count += 1
                    if silent_chunk_count >= silence_needed:
                        print("🔇 Got it, processing...")
                        break

        audio     = np.concatenate(recorded_chunks, axis=0)
        audio_i16 = (audio * 32767).astype(np.int16)

        tmp = tempfile.mktemp(suffix=".wav")
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(config.SAMPLE_RATE)
            wf.writeframes(audio_i16.tobytes())
        return tmp

    # ── Transcription ──────────────────────────────────────────

    def transcribe(self, audio_path: str, language: str = "en",
                   delete_after: bool = False) -> str:
        """
        Transcribe a WAV file using Sarvam AI saaras:v3.

        Args:
            audio_path:   Path to a 16-bit mono WAV file.
            language:     Language code — "en", "ta", or "hi".
            delete_after: If True, delete the file after transcription.
        """
        try:
            client = _get_client()
            cfg = config.SARVAM_VOICE_CONFIGS.get(language, config.SARVAM_VOICE_CONFIGS["en"])
            lang_code = cfg["stt_language"]

            with open(audio_path, "rb") as f:
                response = client.speech_to_text.transcribe(
                    file=f,
                    model=config.SARVAM_STT_MODEL,
                    mode="transcribe",
                    language_code=lang_code,
                )

            if hasattr(response, "transcript"):
                return (response.transcript or "").strip()
            if isinstance(response, dict):
                return (response.get("transcript") or "").strip()
            return str(response).strip()

        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            return ""
        finally:
            if delete_after:
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass

    def listen(self, language: str = "en") -> str:
        """CLI pipeline: record mic → transcribe → return text."""
        audio_path = self.record()
        return self.transcribe(audio_path, language=language, delete_after=True)
