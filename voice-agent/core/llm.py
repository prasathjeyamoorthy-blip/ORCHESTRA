"""
core/llm.py — LLM via Groq API (llama-3.3-70b-versatile)

Streams tokens from Groq's OpenAI-compatible /chat/completions endpoint.
Automatically rotates through up to 5 API keys on 429 (rate limit) or 401.
TTS can start speaking the first sentence while the rest is still generating.
"""

import re
import json
import requests
import config

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
_CLAUSE_END   = re.compile(r'(?<=[.!?,;:])\s+')

# ── Key rotation state ────────────────────────────────────────
_GROQ_KEYS: list[str] = list(config.GROQ_API_KEYS) if config.GROQ_API_KEYS else []
_current_key_index: int = 0
_ROTATE_ON = {429, 401}


def _active_key() -> str:
    if not _GROQ_KEYS:
        raise EnvironmentError("No Groq API keys found. Add GROQ_API_KEY1..5 to voice-agent/.env")
    return _GROQ_KEYS[_current_key_index]


def _rotate_key() -> bool:
    """Move to the next key. Returns False if all keys are exhausted."""
    global _current_key_index
    next_index = (_current_key_index + 1) % len(_GROQ_KEYS)
    if next_index == 0 and _current_key_index != 0:
        return False   # wrapped around — all exhausted
    _current_key_index = next_index
    print(f"[LLM] Rotated to Groq key #{_current_key_index + 1}")
    return True


class GroqLLM:
    """LLM client using Groq API (llama-3.3-70b-versatile) with key rotation."""

    def __init__(self):
        key_count = len(_GROQ_KEYS)
        if key_count == 0:
            raise EnvironmentError("No Groq API keys configured in voice-agent/.env")
        print(f"  Connecting to Groq — model: {config.LLM_MODEL} ({key_count} key(s) available)")
        print("  ✅ LLM ready")

    def _build_messages(self, user_text: str, context: str, history: list) -> list:
        content = (
            f"Relevant information from documents:\n{context}\n\nUser said: {user_text}"
            if context else user_text
        )
        history = history + [{"role": "user", "content": content}]

        system = config.SYSTEM_PROMPT
        if len(history) > 2:
            last_assistant = next(
                (m["content"] for m in reversed(history) if m["role"] == "assistant"),
                ""
            )
            first_word = last_assistant.split()[0] if last_assistant else ""
            if first_word:
                system += f"\n\nIMPORTANT: Do NOT start your response with '{first_word}'. Vary your opening."

        return [
            {"role": "system", "content": system},
            *history[-10:],
        ]

    def _post(self, messages: list, stream: bool) -> requests.Response:
        """POST to Groq with the active key. Raises on non-rotatable errors."""
        payload = {
            "model":       config.LLM_MODEL,
            "messages":    messages,
            "max_tokens":  config.LLM_MAX_TOKENS,
            "temperature": config.LLM_TEMPERATURE,
            "stream":      stream,
        }
        headers = {
            "Authorization": f"Bearer {_active_key()}",
            "Content-Type":  "application/json",
        }
        return requests.post(
            config.GROQ_LLM_URL,
            headers=headers,
            json=payload,
            stream=stream,
            timeout=30,
        )

    def stream(self, user_text: str, context: str = "", history: list = None):
        """
        Generator — yields complete sentences/clauses as they arrive.
        TTS speaks each piece the moment it's yielded.
        Rotates keys automatically on 429/401.
        """
        if history is None:
            history = []
        messages = self._build_messages(user_text, context, history)

        response = None
        for attempt in range(len(_GROQ_KEYS)):
            try:
                resp = self._post(messages, stream=True)
                if resp.status_code in _ROTATE_ON:
                    print(f"[LLM] Key #{_current_key_index + 1} returned {resp.status_code} — rotating")
                    if not _rotate_key():
                        break
                    continue
                resp.raise_for_status()
                response = resp
                break
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code in _ROTATE_ON:
                    if not _rotate_key():
                        break
                    continue
                yield f"Sorry, something went wrong connecting to the AI service. {e}"
                return

        if response is None:
            yield "Sorry, all API keys are currently rate-limited. Please try again shortly."
            return

        buffer      = ""
        first_yield = True

        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data: "):
                continue
            payload_str = line[6:].strip()
            if payload_str == "[DONE]":
                break
            try:
                chunk = json.loads(payload_str)
            except json.JSONDecodeError:
                continue

            token = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if not token:
                continue

            buffer += token

            while True:
                match = _CLAUSE_END.search(buffer) if first_yield else _SENTENCE_END.search(buffer)
                if not match:
                    break
                piece  = buffer[: match.end()].strip()
                buffer = buffer[match.end():]
                if piece:
                    first_yield = False
                    yield piece

        leftover = buffer.strip()
        if leftover:
            yield leftover

    def chat(self, user_text: str, context: str = "", history: list = None) -> str:
        """Blocking call — collects the full streamed reply."""
        parts = list(self.stream(user_text, context, history=history))
        result = ""
        for part in parts:
            if result and result[-1] not in ".!?,;:":
                result += " "
            result += part
        return result.strip()

    def reset(self):
        pass  # no-op — history is per-request


# Alias — agent.py imports OllamaLLM (legacy name)
OllamaLLM = GroqLLM
NvidiaLLM  = GroqLLM   # in case anything references NvidiaLLM directly
