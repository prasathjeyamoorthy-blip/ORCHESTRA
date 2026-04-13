import redis
import json
import uuid
from datetime import datetime

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB   = 0

SESSION_TTL  = 60 * 60 * 24        # 24 hours
USER_TTL     = 60 * 60 * 24 * 30   # 30 days
MAX_HISTORY  = 20                   # last 20 turns (enough for full context)


class MemoryManager:
    def __init__(self):
        self.r = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=2,
        )

    # ── Session memory ────────────────────────────────────────────
    def get_session_history(self, session_id: str) -> list:
        try:
            key  = f"session:{session_id}:history"
            data = self.r.get(key)
            return json.loads(data) if data else []
        except Exception:
            return []

    def add_to_session(self, session_id: str, query: str, answer: str):
        try:
            key     = f"session:{session_id}:history"
            history = self.get_session_history(session_id)
            history.append({
                "query"    : query,
                "answer"   : answer,
                "timestamp": datetime.utcnow().isoformat(),
            })
            history = history[-MAX_HISTORY:]
            self.r.setex(key, SESSION_TTL, json.dumps(history))
        except Exception as e:
            print(f"[Memory] Failed to save session turn: {e}")

    def get_recent_context(self, session_id: str, n: int = 6) -> str:
        """Return last n turns as a formatted string for LLM injection."""
        history = self.get_session_history(session_id)
        if not history:
            return ""
        turns = history[-n:]
        lines = []
        for t in turns:
            lines.append(f"User: {t['query']}")
            lines.append(f"Assistant: {t['answer']}")
        return "\n".join(lines)

    # ── User memory (cross-session) ───────────────────────────────
    def get_user_memory(self, user_id: str) -> dict:
        try:
            key  = f"user:{user_id}:memory"
            data = self.r.get(key)
            return json.loads(data) if data else {}
        except Exception:
            return {}

    def update_user_memory(self, user_id: str, query: str, answer: str):
        try:
            key    = f"user:{user_id}:memory"
            memory = self.get_user_memory(user_id)
            if "history_summary" not in memory:
                memory["history_summary"] = []
            memory["history_summary"].append({
                "query"    : query,
                "answer"   : answer,
                "timestamp": datetime.utcnow().isoformat(),
            })
            memory["history_summary"] = memory["history_summary"][-20:]
            self.r.setex(key, USER_TTL, json.dumps(memory))
        except Exception as e:
            print(f"[Memory] Failed to update user memory: {e}")

    # ── Helpers ───────────────────────────────────────────────────
    @staticmethod
    def new_session_id() -> str:
        return str(uuid.uuid4())
