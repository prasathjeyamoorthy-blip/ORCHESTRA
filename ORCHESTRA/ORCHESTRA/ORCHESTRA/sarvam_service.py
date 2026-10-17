import os
import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)

SARVAM_API_URL = "https://api.sarvam.ai/translate"


def get_sarvam_key() -> str:
    load_dotenv(env_path, override=True)
    return os.getenv("SARVAM_API_KEY", "").strip()


def is_sarvam_configured() -> bool:
    return bool(get_sarvam_key())


def translate_text(text: str, target_lang: str = "ta-IN", source_lang: str = "en-IN") -> str:
    """
    Translate text using Sarvam AI Translation API (api.sarvam.ai/translate).
    """
    api_key = get_sarvam_key()
    if not api_key or not text.strip():
        return text

    try:
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "input": text,
            "source_language_code": source_lang,
            "target_language_code": target_lang,
            "speaker_gender": "Female",
            "mode": "formal",
            "model": "mayura:v1"
        }
        resp = requests.post(SARVAM_API_URL, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            translated = data.get("translated_text") or data.get("translation") or text
            print(f"[Sarvam AI] Successfully translated text to {target_lang}")
            return translated
        else:
            print(f"[Sarvam AI] Translation API error ({resp.status_code}): {resp.text}")
            return text
    except Exception as e:
        print(f"[Sarvam AI] Exception during translation: {e}")
        return text


def translate_to_pure_tamil_llm(text: str) -> str:
    """
    Translates text into formal, pure Tamil script (தமிழ் எழுத்துக்கள்) using Groq LLM fallback.
    """
    try:
        from agent import groq_chat_completion_sync, LLM_MODEL
        res = groq_chat_completion_sync(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional Tamil translator. Translate the given text purely into formal, natural Tamil script (தமிழ் எழுத்துக்கள்). Do NOT output English or Tanglish (Tamil written in English characters)."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=0.1,
            max_tokens=600
        )
        return res.choices[0].message.content
    except Exception as e:
        print(f"[Tamil Translation LLM Fallback Error]: {e}")
        return text


def process_tamil_response(answer: str) -> str:
    """
    Tamil translation has been removed. Returns answer as-is.
    """
    return answer
