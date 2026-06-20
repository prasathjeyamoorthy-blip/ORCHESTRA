"""
core/tts.py — Text to Speech via NVIDIA NIM (nvidia/magpie-tts-multilingual)
"""

import re
import numpy as np
import sounddevice as sd

import config

try:
    import riva.client as riva
    _RIVA_OK = True
except ImportError:
    _RIVA_OK = False

_GRPC_SERVER = "grpc.nvcf.nvidia.com:443"
_FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"

# Sentence-ending punctuation for splitting
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')


class TextToSpeech:

    def __init__(self):
        if not _RIVA_OK:
            raise ImportError("nvidia-riva-client is not installed. Run: pip install nvidia-riva-client")

        auth = riva.Auth(
            uri=_GRPC_SERVER,
            use_ssl=True,
            metadata_args=[
                ["function-id",   _FUNCTION_ID],
                ["authorization", f"Bearer {config.TTS_API_KEY}"],
            ],
        )
        self._tts = riva.SpeechSynthesisService(auth)
        print("  TTS → NVIDIA NIM magpie-tts-multilingual  (cloud gRPC)")
        print(f"  Voice: {config.TTS_VOICE}")
        print("  ✅ TTS ready")

    # ── Text cleaning ──────────────────────────────────────────────

    def clean(self, text: str) -> str:
        """Strip markdown/symbols and convert to natural spoken text."""
        # Remove think tags
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Strip markdown formatting
        text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        text = re.sub(r'#{1,6}\s*', '', text)
        text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)
        text = re.sub(r'---+', '', text)
        # Links → just the label
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # List markers → natural flow (keep the text, remove the bullet)
        text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

        # Currency — spoken naturally
        text = re.sub(r'₹\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + ' rupees', text)
        text = re.sub(r'Rs\.?\s*([\d,]+)', lambda m: m.group(1).replace(',', '') + ' rupees', text)

        # Abbreviations → spoken form
        _ABBREVS = {
            r'\bPAN\b':     'PAN',          # keep as-is, TTS handles it
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
            r'\bw/o\b':     'without',
            r'\bw/\b':      'with',
            r'\b&\b':       'and',
        }
        for pattern, replacement in _ABBREVS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Numbers to words (skip years and very large numbers)
        text = _numbers_to_words(text)

        # Collapse whitespace
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def split_sentences(self, text: str) -> list[str]:
        """
        Split into chunks that fit within the TTS model's 400-char limit.
        Splits on sentence boundaries first, then hard-splits long chunks.
        """
        # Split on sentence-ending punctuation
        raw = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        for s in raw:
            s = s.strip()
            if not s:
                continue
            # Hard split if a single sentence exceeds 350 chars (safe margin under 400)
            if len(s) <= 350:
                chunks.append(s)
            else:
                # Split on clause boundaries: comma, semicolon
                parts = re.split(r'(?<=[,;])\s+', s)
                current = ""
                for part in parts:
                    if len(current) + len(part) + 1 <= 350:
                        current = (current + " " + part).strip() if current else part
                    else:
                        if current:
                            chunks.append(current)
                        # If single part still too long, split by words
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

    # ── Synthesis ──────────────────────────────────────────────────

    def _synthesise(self, text: str) -> bytes | None:
        """
        Synthesise text → raw LINEAR_PCM bytes (22050 Hz, mono, 16-bit).
        Returns None on failure instead of raising so the caller can skip.
        """
        text = text.strip()
        if not text:
            return None
        try:
            resp = self._tts.synthesize(
                text,
                voice_name=config.TTS_VOICE,
                language_code=config.TTS_LANGUAGE,
                encoding=riva.AudioEncoding.LINEAR_PCM,
                sample_rate_hz=config.TTS_SAMPLE_RATE,
            )
            return resp.audio if resp.audio else None
        except Exception as e:
            print(f"[TTS] Synthesis error for text '{text[:60]}...': {e}")
            return None

    def _play_pcm(self, pcm_bytes: bytes):
        """Play raw 16-bit mono PCM through sounddevice (CLI mode)."""
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(samples, samplerate=config.TTS_SAMPLE_RATE)
        sd.wait()

    def speak(self, text: str):
        """CLI mode: clean → split → synthesise → play each sentence."""
        clean_text = self.clean(text)
        if not clean_text:
            return
        for sentence in self.split_sentences(clean_text):
            if sentence.strip():
                pcm = self._synthesise(sentence)
                if pcm:
                    self._play_pcm(pcm)

    def synthesise_full(self, text: str) -> bytes:
        """
        Server mode: clean → split → synthesise all sentences → return
        concatenated raw PCM bytes ready to be wrapped in a WAV container.
        Returns empty bytes if synthesis fails entirely.
        """
        clean_text = self.clean(text)
        if not clean_text:
            return b""

        all_pcm = b""
        for sentence in self.split_sentences(clean_text):
            sentence = sentence.strip()
            if not sentence:
                continue
            pcm = self._synthesise(sentence)
            if pcm:
                all_pcm += pcm

        return all_pcm


# ── Number → words ─────────────────────────────────────────────────────────────

def _num_to_words(n: int) -> str:
    if n == 0:
        return "zero"
    ones = ["", "one", "two", "three", "four", "five", "six", "seven",
            "eight", "nine", "ten", "eleven", "twelve", "thirteen",
            "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty",
            "sixty", "seventy", "eighty", "ninety"]

    def _below_1000(num):
        if num == 0:   return ""
        elif num < 20: return ones[num]
        elif num < 100:
            r = ones[num % 10]
            return tens[num // 10] + (" " + r if r else "")
        else:
            r = _below_1000(num % 100)
            return ones[num // 100] + " hundred" + (" " + r if r else "")

    parts = []
    if n >= 10_000_000: parts.append(_below_1000(n // 10_000_000) + " crore");  n %= 10_000_000
    if n >= 100_000:    parts.append(_below_1000(n // 100_000) + " lakh");      n %= 100_000
    if n >= 1_000:      parts.append(_below_1000(n // 1_000) + " thousand");    n %= 1_000
    if n > 0:           parts.append(_below_1000(n))
    return " ".join(parts)


def _numbers_to_words(text: str) -> str:
    def _replace(m):
        raw = m.group(0).replace(",", "")
        try:
            n = int(raw)
        except ValueError:
            return m.group(0)
        if 1900 <= n <= 2099: return m.group(0)   # keep years as digits
        if len(raw) >= 12:    return m.group(0)   # skip huge numbers
        return _num_to_words(n)
    return re.sub(r'\b[\d,]+\b', _replace, text)
