"""
memory/memory_manager.py

Single-source-of-truth memory for the RAG pipeline.

The Node backend owns the persistent history (Supabase + Redis).
This module's job is:
  1. Cache the structured context block Node sends per request (short TTL)
  2. Store flow state snapshots (FlowManager already calls this)
  3. Provide a clean get_recent_context() for chain.py that reads from
     the context block Node sent — NOT a separate parallel history store.

This eliminates the double-history problem where Node and RAG each kept
their own history that could diverge and cause hallucinations.
"""

import json
import uuid
import os
from datetime import datetime

# TTLs
CONTEXT_TTL = 60 * 60 * 2    # 2h — matches Node's CACHE_TTL
FLOW_TTL    = 60 * 60 * 24 * 7  # 7 days — flow state survives restarts

MAX_HISTORY = 20  # kept for compatibility with FlowManager


class MemoryManager:
    """
    Upstash Redis-backed memory. REQUIRES Upstash credentials.
    No local fallback — fails fast if not configured.
    """

    def __init__(self):
        self._url   = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self._token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

        if not self._url or not self._url.startswith("https://"):
            raise EnvironmentError(
                "UPSTASH_REDIS_REST_URL is not set or invalid.\n"
                "Add it to pan-rag/.env:\n"
                "  UPSTASH_REDIS_REST_URL=https://your-redis-url.upstash.io"
            )
        
        if not self._token or self._token == "your-token-here":
            raise EnvironmentError(
                "UPSTASH_REDIS_REST_TOKEN is not set or invalid.\n"
                "Add it to pan-rag/.env:\n"
                "  UPSTASH_REDIS_REST_TOKEN=your_token_here"
            )
        
        print("[Memory] ✅ Connected to Upstash Redis")

    # ── Low-level REST helpers ────────────────────────────────────
    def _get(self, key: str):
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self._url}/get/{key}",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read()).get("result")
        except Exception as e:
            print(f"[Memory] GET {key} failed: {e}")
            return None

    def _setex(self, key: str, ttl: int, value: str):
        try:
            import urllib.request
            payload = json.dumps(["SET", key, value, "EX", ttl]).encode()
            req = urllib.request.Request(
                self._url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[Memory] SETEX {key} failed: {e}")
            raise  # Re-raise to make failures visible

    def _del(self, key: str):
        try:
            import urllib.request
            payload = json.dumps(["DEL", key]).encode()
            req = urllib.request.Request(
                self._url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[Memory] DEL {key} failed: {e}")
            raise  # Re-raise to make failures visible

    # ── Context block cache ───────────────────────────────────────
    # Node sends a fully-built user_context string with each request.
    # We cache it so chain.py can access it without it being passed
    # through every function call.

    def cache_context(self, session_id: str, user_context: str, user_id: str = ""):
        """Cache the context block Node sent for this session."""
        if not user_context or not user_context.strip():
            return
        # Key includes user_id so two users can never share a context entry
        prefix = f"{user_id}:" if user_id and user_id != "anonymous" else ""
        self._setex(f"ctx:{prefix}{session_id}", CONTEXT_TTL, user_context)

    def get_cached_context(self, session_id: str, user_id: str = "") -> str:
        """Retrieve the cached context block for this session."""
        prefix = f"{user_id}:" if user_id and user_id != "anonymous" else ""
        return self._get(f"ctx:{prefix}{session_id}") or ""

    # ── Session history (DEPRECATED — kept for FlowManager compat) ──
    # chain.py no longer writes its own history here.
    # These methods are kept so FlowManager.load_from_memory() still works.

    def get_session_history(self, session_id: str, user_id: str = "") -> list:
        """
        Returns the conversation history for this session.
        Parses the cached context block Node sent — no separate store.
        """
        ctx = self.get_cached_context(session_id, user_id)
        if not ctx:
            return []
        # Parse the '=== RECENT CONVERSATION ===' block back into turn dicts
        turns = []
        in_block = False
        for line in ctx.splitlines():
            if "=== RECENT CONVERSATION" in line:
                in_block = True
                continue
            if in_block:
                if line.startswith("RULE:") or line.startswith("==="):
                    break
                if line.startswith("User: "):
                    turns.append({"query": line[6:], "answer": ""})
                elif line.startswith("Assistant: ") and turns:
                    turns[-1]["answer"] = line[11:]
        return turns

    def get_long_term_context(self, session_id: str, user_id: str = "") -> str:
        """
        Returns the long-term memory block from the context Node sent.
        This is the '=== RELEVANT PAST CONVERSATIONS ===' section.
        """
        ctx = self.get_cached_context(session_id, user_id)
        if not ctx or "=== RELEVANT PAST CONVERSATIONS ===" not in ctx:
            return ""
        lines = []
        in_block = False
        for line in ctx.splitlines():
            if "=== RELEVANT PAST CONVERSATIONS ===" in line:
                in_block = True
                lines.append(line)
                continue
            if in_block:
                if line.startswith("===") and "RELEVANT PAST" not in line:
                    break
                lines.append(line)
        return "\n".join(lines)

    def get_recent_context(self, session_id: str, n: int = 6, user_id: str = "") -> str:
        """
        Returns the last n turns as a plain string.
        Reads from the context block Node sent — not a separate store.
        """
        history = self.get_session_history(session_id, user_id)
        if not history:
            return ""
        lines = []
        for t in history[-n:]:
            if t.get("query"):
                lines.append(f"User: {t['query']}")
            if t.get("answer"):
                lines.append(f"Assistant: {t['answer']}")
        return "\n".join(lines)

    def add_to_session(self, session_id: str, query: str, answer: str):
        """
        No-op — Node owns history persistence.
        Kept so chain.py call sites don't need to change.
        """
        pass

    # ── User memory (cross-session) — no-op ──────────────────────
    # Node's user_profiles table + extractFacts() handles this.

    def get_user_memory(self, user_id: str) -> dict:
        return {}

    def update_user_memory(self, user_id: str, query: str, answer: str):
        pass

    # ── Helpers ───────────────────────────────────────────────────
    @staticmethod
    def new_session_id() -> str:
        return str(uuid.uuid4())
