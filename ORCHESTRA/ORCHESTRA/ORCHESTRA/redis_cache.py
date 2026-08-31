import os
import json
import hashlib
import requests
from typing import Optional, Any
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))

def _get_rest_credentials():
    load_dotenv(env_path, override=True)
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().strip('"').strip("'").rstrip("/")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip().strip('"').strip("'")
    return url, token

_REDIS_CLIENT = None

def _get_redis_client():
    global _REDIS_CLIENT
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT

    load_dotenv(env_path, override=True)
    redis_url = os.getenv("UPSTASH_REDIS_URL", "").strip().strip('"').strip("'") or os.getenv("REDIS_URL", "").strip().strip('"').strip("'")

    if redis_url:
        try:
            import redis
            _REDIS_CLIENT = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0)
            print("[Redis Cache] Connected via Redis protocol URL")
            return _REDIS_CLIENT
        except Exception as e:
            print(f"[Redis Cache] Note on redis-py client init: {e}")

    return None


def get_cache(key: str) -> Optional[Any]:
    """
    Retrieve JSON item from Upstash Redis (supports REST API & redis-py).
    """
    # 1. Try redis-py if available
    r_client = _get_redis_client()
    if r_client:
        try:
            val = r_client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            print(f"[Redis Cache] GET error: {e}")

    # 2. Fallback to Upstash REST API
    rest_url, rest_token = _get_rest_credentials()
    if rest_url and rest_token:
        try:
            url = f"{rest_url}/get/{key}"
            headers = {"Authorization": f"Bearer {rest_token}"}
            resp = requests.get(url, headers=headers, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result")
                if result:
                    return json.loads(result)
        except Exception as e:
            print(f"[Redis Cache] REST GET error: {e}")

    return None


def set_cache(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """
    Store JSON item in Upstash Redis with a TTL in seconds.
    """
    val_str = json.dumps(value)

    # 1. Try redis-py if available
    r_client = _get_redis_client()
    if r_client:
        try:
            r_client.setex(key, ttl_seconds, val_str)
            return True
        except Exception as e:
            print(f"[Redis Cache] SET error: {e}")

    # 2. Fallback to Upstash REST API
    rest_url, rest_token = _get_rest_credentials()
    if rest_url and rest_token:
        try:
            url = f"{rest_url}/set/{key}/EX/{ttl_seconds}"
            headers = {"Authorization": f"Bearer {rest_token}"}
            resp = requests.post(url, headers=headers, data=val_str, timeout=3.0)
            if resp.status_code == 200:
                return True
            
            # Alternative Upstash REST GET format: /set/key/value/EX/3600
            resp_get = requests.get(f"{rest_url}/set/{key}/{requests.utils.quote(val_str)}/EX/{ttl_seconds}", headers=headers, timeout=3.0)
            return resp_get.status_code == 200
        except Exception as e:
            print(f"[Redis Cache] REST SET error: {e}")

    return False


def make_cache_key(prefix: str, text: str) -> str:
    """
    Generate a deterministic MD5 hash key for caching.
    """
    h = hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()
    return f"{prefix}:{h}"

