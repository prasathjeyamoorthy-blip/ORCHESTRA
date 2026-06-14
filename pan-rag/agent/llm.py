# agent/llm.py
# Provides get_llm() for modules that import from agent.llm
# Uses the NVIDIA NIM API via the OpenAI-compatible endpoint — no local models.

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, LLM_MODEL


class _NvidiaLLM:
    """
    Thin wrapper around the NVIDIA NIM chat completions endpoint.
    Exposes an .invoke(prompt) method that returns an object with .content
    so it's drop-in compatible with LangChain-style callers.
    """

    def __init__(self):
        import requests
        self._requests = requests
        self._url = f"{NVIDIA_BASE_URL}/chat/completions"
        self._headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        }
        self._model = LLM_MODEL

    def invoke(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2):
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = self._requests.post(
            self._url,
            headers=self._headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return _Response(content)


class _Response:
    """Mimics LangChain AIMessage so callers can do response.content"""
    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return self.content


# Singleton — created once, reused across all calls
_llm_instance: _NvidiaLLM | None = None


def get_llm() -> _NvidiaLLM:
    """Return the shared NVIDIA NIM LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = _NvidiaLLM()
    return _llm_instance
