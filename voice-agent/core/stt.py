"""
core/stt.py — Speech to Text via NVIDIA NIM (openai/whisper-large-v3)
"""

import os
import wave
import tempfile
import numpy as np
import sounddevice as sd

import config

try:
    import riva.client as riva
    _RIVA_OK = True
except ImportError:
    _RIVA_OK = False

_GRPC_SERVER = "grpc.nvcf.nvidia.com:443"
_FUNCTION_ID = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"


def _read_wav_info(path: str) -> tuple[bytes, int, int]:
    """Read WAV file, return (pcm_bytes, sample_rate, channels)."""
    with wave.open(path, "rb") as wf:
        return wf.readframes(wf.getnframes()), wf.getframerate(), wf.getnchannels()


class SpeechToText:

    def __init__(self):
        if not _RIVA_OK:
            raise ImportError("nvidia-riva-client is not installed. Run: pip install nvidia-riva-client")

        auth = riva.Auth(
            uri=_GRPC_SERVER,
            use_ssl=True,
            metadata_args=[
                ["function-id",   _FUNCTION_ID],
                ["authorization", f"Bearer {config.ASR_API_KEY}"],
            ],
        )
        self._asr = riva.ASRService(auth)
        print("  STT → NVIDIA NIM whisper-large-v3  (cloud gRPC)")
        print("  ✅ STT ready")

    # ── Recording (CLI mode only) ──────────────────────────────────

    def record(self) -> str:
        """Records from mic until silence. Returns path to temp WAV."""
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

    # ── Transcription ──────────────────────────────────────────────

    def transcribe(self, audio_path: str, delete_after: bool = False) -> str:
        """
        Transcribe a WAV file. Reads actual sample rate from the file header
        so it works with any valid WAV regardless of how it was created.

        Args:
            audio_path:   Path to a 16-bit mono WAV file.
            delete_after: If True, delete the file after transcription.
                          Server.py manages its own cleanup, so pass False
                          from there to avoid double-delete errors.
        """
        try:
            pcm_bytes, sample_rate, channels = _read_wav_info(audio_path)

            if not pcm_bytes:
                print("[STT] Empty audio — nothing to transcribe")
                return ""

            asr_config = riva.RecognitionConfig(
                language_code="en-IN",          # Indian English — better accent handling
                max_alternatives=1,
                enable_automatic_punctuation=True,
                audio_channel_count=channels,   # use actual channel count from file
                sample_rate_hertz=sample_rate,  # use actual rate from file
                encoding=riva.AudioEncoding.LINEAR_PCM,
            )

            resp = self._asr.offline_recognize(pcm_bytes, asr_config)

            if not resp.results:
                return ""

            transcript = " ".join(
                r.alternatives[0].transcript
                for r in resp.results
                if r.alternatives
            ).strip()

            # Basic cleanup — remove filler artifacts whisper sometimes adds
            transcript = transcript.strip(" .,")
            return transcript

        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            return ""
        finally:
            if delete_after:
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass

    def listen(self) -> str:
        """CLI pipeline: record mic → transcribe → return text."""
        audio_path = self.record()
        return self.transcribe(audio_path, delete_after=True)
