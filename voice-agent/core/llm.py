"""
core/llm.py — LLM via NVIDIA NIM API (meta/llama-3.1-70b-instruct)

Streams tokens from the NVIDIA OpenAI-compatible /chat/completions endpoint
so TTS can start speaking the first sentence while the rest is still generating.
"""

import re
import json
import requests
import config

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
_CLAUSE_END   = re.compile(r'(?<=[.!?,;:])\s+')


class NvidiaLLM:
    """LLM client using NVIDIA NIM cloud API (meta/llama-3.1-70b-instruct)."""

    def __init__(self):
        print(f"  Connecting to NVIDIA NIM — model: {config.LLM_MODEL}")
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

    def stream(self, user_text: str, context: str = "", history: list = None):
        """
        Generator — yields complete sentences as they arrive.
        TTS speaks each sentence the moment it's yielded.
        history: per-request conversation history (not shared across users).
        """
        if history is None:
            history = []
        messages = self._build_messages(user_text, context, history)

        payload = {
            "model":       config.LLM_MODEL,
            "messages":    messages,
            "max_tokens":  config.LLM_MAX_TOKENS,
            "temperature": config.LLM_TEMPERATURE,
            "top_p":       0.85,
            "stream":      True,
        }
        headers = {
            "Authorization": f"Bearer {config.NVIDIA_API_KEY}",
            "Content-Type":  "application/json",
        }

        try:
            response = requests.post(
                config.NVIDIA_LLM_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=60,
            )
            response.raise_for_status()
        except Exception as e:
            yield f"Sorry, something went wrong connecting to the AI service. {e}"
            return

        buffer      = ""
        full_reply  = ""
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

            buffer     += token
            full_reply += token

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
        """Blocking call — collects the full streamed reply preserving punctuation.
        history: per-request conversation history (not shared across users)."""
        parts = list(self.stream(user_text, context, history=history))
        # Join with a space but avoid double-spacing around existing punctuation
        result = ""
        for part in parts:
            if result and not result[-1] in ".!?,;:":
                result += " "
            result += part
        return result.strip()

    def reset(self):
        pass  # no-op — history is now per-request, not shared


# Alias for backward compatibility with agent.py which imports OllamaLLM
OllamaLLM = NvidiaLLM
