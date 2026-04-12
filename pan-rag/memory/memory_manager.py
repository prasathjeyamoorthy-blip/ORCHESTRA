import redis
import json
import uuid
from datetime import datetime

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

SESSION_TTL = 60 * 60 * 24        # 24 hours (in-session memory)
USER_TTL = 60 * 60 * 24 * 30      # 30 days (cross-session memory)
MAX_HISTORY = 10                   # last 10 turns per session

class MemoryManager:
    def __init__(self):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

    # ── Session Memory (per conversation) ──────────────────────────
    def get_session_history(self, session_id: str) -> list:
        """Get conversation history for this session."""
        key = f"session:{session_id}:history"
        data = self.r.get(key)
        return json.loads(data) if data else []

    def add_to_session(self, session_id: str, query: str, answer: str):
        """Append a Q&A turn to session history."""
        key = f"session:{session_id}:history"
        history = self.get_session_history(session_id)
        history.append({
            "query": query,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Keep only last MAX_HISTORY turns
        history = history[-MAX_HISTORY:]
        self.r.setex(key, SESSION_TTL, json.dumps(history))

    # ── User Memory (cross-session) ─────────────────────────────────
    def get_user_memory(self, user_id: str) -> dict:
        """Get persistent user memory."""
        key = f"user:{user_id}:memory"
        data = self.r.get(key)
        return json.loads(data) if data else {}

    def update_user_memory(self, user_id: str, query: str, answer: str):
        """Store important facts about the user across sessions."""
        key = f"user:{user_id}:memory"
        memory = self.get_user_memory(user_id)
        if "history_summary" not in memory:
            memory["history_summary"] = []
        memory["history_summary"].append({
            "query": query,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        })
        memory["history_summary"] = memory["history_summary"][-20:]  # keep last 20
        self.r.setex(key, USER_TTL, json.dumps(memory))

    # ── Session ID helper ───────────────────────────────────────────
    @staticmethod
    def new_session_id() -> str:
        return str(uuid.uuid4())