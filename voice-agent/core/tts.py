"""
core/tts.py — Text to Speech via Sarvam AI (bulbul:v3)
"""

import io
import re
import base64
import wave
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
        print("  TTS → Sarvam AI bulbul:v3")
    return _sarvam_client


class TextToSpeech:

    def __init__(self):
        _get_client()
        print("  ✅ TTS ready (Sarvam bulbul:v3)")

    # ── Text cleaning ──────────────────────────────────────────

    def clean(self, text: str) -> str:
        """Strip markdown/symbols and convert to natural spoken text."""
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        text = re.sub(r'#{1,6}\s*', '', text)
        text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)
        text = re.sub(r'---+', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

        # Currency
        text = re.sub(r'₹\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + ' rupees', text)
        text = re.sub(r'Rs\.?\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + ' rupees', text)

        # Abbreviations
        _ABBREVS = {
            r'\bTDS\b':     'T D S',
            r'\bTCS\b':     'T C S',
            r'\bNSDL\b':    'N S D L',
            r'\bUTIITSL\b': 'U T I I T S L',
            r'\bITR\b':     'I T R',
            r'\bKYC\b':     'K Y C',
            r'\bNRI\b':     'N R I',
            r'\bOCI\b':     'O C I',
            r'\bHUF\b':     'H U F',
            r'\bDOB\b':     'date of birth',
            r'\bDL\b':      'driving license',
            r'\be\.g\.\b':  'for example',
            r'\bi\.e\.\b':  'that is',
            r'\betc\.\b':   'and so on',
            r'\bvs\.\b':    'versus',
            r'\b&\b':       'and',
        }
        for pattern, replacement in _ABBREVS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def split_sentences(self, text: str) -> list[str]:
        """Split into chunks ≤ 350 chars (safe under Sarvam's 500-char limit)."""
        raw = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        for s in raw:
            s = s.strip()
            if not s:
                continue
            if len(s) <= 350:
                chunks.append(s)
            else:
                parts = re.split(r'(?<=[,;])\s+', s)
                current = ""
                for part in parts:
                    if len(current) + len(part) + 1 <= 350:
                        current = (current + " " + part).strip() if current else part
                    else:
                        if current:
                            chunks.append(current)
                        if len(part) > 350:
                            words = part.split()
                            current = ""
                            for word in words:
                                if len(current) + len(word) + 1 <= 350:
                                    current = (current + " " + word).strip() if current else word
                                else:
                                    if current:
                                        chunks.append(current)
                                    current = word
                        else:
                            current = part
                if current:
                    chunks.append(current)

        return [c for c in chunks if c.strip()]

    # ── Synthesis ──────────────────────────────────────────────

    def _synthesise(self, text: str, language: str = "en") -> bytes | None:
        """
        Synthesise one chunk → raw WAV bytes via Sarvam bulbul:v3.
        Returns None on failure so the caller can skip the chunk.
        """
        text = text.strip()
        if not text:
            return None

        try:
            client = _get_client()
            cfg = config.SARVAM_VOICE_CONFIGS.get(language, config.SARVAM_VOICE_CONFIGS["en"])

            response = client.text_to_speech.convert(
                model=config.SARVAM_TTS_MODEL,
                text=text,
                target_language_code=cfg["tts_language"],
                speaker=cfg["tts_speaker"],
                speech_sample_rate=config.TTS_SAMPLE_RATE,
                pace=1.0,
            )

            if not (hasattr(response, "audios") and response.audios):
                print(f"[TTS] No audio returned for: {text[:60]!r}")
                return None

            wav_chunks = [base64.b64decode(chunk) for chunk in response.audios]

            if len(wav_chunks) == 1:
                return wav_chunks[0]

            # Multiple chunks — merge PCM into one WAV
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

        except Exception as e:
            print(f"[TTS] Synthesis error for text '{text[:60]}...': {e}")
            return None

    def _play_wav(self, wav_bytes: bytes):
        """Play WAV bytes through sounddevice (CLI mode)."""
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            sample_rate = wf.getframerate()
            pcm = wf.readframes(wf.getnframes())
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(samples, samplerate=sample_rate)
        sd.wait()

    def speak(self, text: str, language: str = "en"):
        """CLI mode: clean → split → synthesise → play each sentence."""
        clean_text = self.clean(text)
        if not clean_text:
            return
        for sentence in self.split_sentences(clean_text):
            if sentence.strip():
                wav = self._synthesise(sentence, language)
                if wav:
                    self._play_wav(wav)

    def synthesise_full(self, text: str, language: str = "en") -> bytes:
        """
        Server mode: clean → split → synthesise all sentences → return
        concatenated WAV bytes. Returns empty bytes if synthesis fails.
        """
        clean_text = self.clean(text)
        if not clean_text:
            return b""

        pcm_parts = []
        params = None

        for sentence in self.split_sentences(clean_text):
            sentence = sentence.strip()
            if not sentence:
                continue
            wav = self._synthesise(sentence, language)
            if not wav:
                continue
            buf = io.BytesIO(wav)
            with wave.open(buf, "rb") as wf:
                if params is None:
                    params = wf.getparams()
                pcm_parts.append(wf.readframes(wf.getnframes()))

        if not pcm_parts or params is None:
            return b""

        merged = io.BytesIO()
        with wave.open(merged, "wb") as wf:
            wf.setparams(params)
            for pcm in pcm_parts:
                wf.writeframes(pcm)
        return merged.getvalue()
