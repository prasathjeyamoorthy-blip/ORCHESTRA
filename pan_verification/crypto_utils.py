import os
import json
import base64
from typing import Any, Dict

from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Ensure .env is loaded even when this module is imported directly
load_dotenv()



def _get_key_bytes() -> bytes:
    """Get 32-byte key from env.

    Expected: DATA_ENCRYPTION_KEY is base64-encoded 32 bytes.
    """
    key_b64 = os.getenv("DATA_ENCRYPTION_KEY")
    if not key_b64:
        raise RuntimeError(
            "Missing DATA_ENCRYPTION_KEY env var. "
            "Set it to base64 of 32-byte key."
        )

    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise RuntimeError(
            f"DATA_ENCRYPTION_KEY must decode to 32 bytes for AES-256-GCM, got {len(key)} bytes."
        )
    return key


def encrypt_json(data: Dict[str, Any]) -> str:
    """Encrypt dict as JSON string using AES-256-GCM.

    Returns base64 string containing: nonce(12) || ciphertext+tag.
    """
    key = _get_key_bytes()
    aesgcm = AESGCM(key)

    nonce = os.urandom(12)
    plaintext = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    # ciphertext includes auth tag at end
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def decrypt_json(token_b64: str) -> Dict[str, Any]:
    """Decrypt base64 token created by encrypt_json back into dict."""
    key = _get_key_bytes()
    aesgcm = AESGCM(key)

    raw = base64.b64decode(token_b64)
    if len(raw) < 12:
        raise ValueError("Invalid encrypted payload")

    nonce = raw[:12]
    ciphertext = raw[12:]

    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    return json.loads(plaintext.decode("utf-8"))

