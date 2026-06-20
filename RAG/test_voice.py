"""
Quick voice server test
Run: python test_voice.py
"""
import requests

print("Testing voice server on port 8002...")

# Test 1: Health check
try:
    res = requests.get("http://localhost:8002/api/health", timeout=5)
    print(f"✅ Health check: {res.status_code} - {res.json()}")
except Exception as e:
    print(f"❌ Health check failed: {e}")

# Test 2: Root endpoint
try:
    res = requests.get("http://localhost:8002/", timeout=5)
    print(f"✅ Root endpoint: {res.status_code} - {res.json()}")
except Exception as e:
    print(f"❌ Root endpoint failed: {e}")

# Test 3: Check if STT endpoint exists (will fail without audio, but should not 404)
try:
    res = requests.post("http://localhost:8002/api/voice/stt", timeout=5)
    # Expect 422 (validation error) not 404
    if res.status_code == 404:
        print(f"❌ STT endpoint not found (404)")
    elif res.status_code == 422:
        print(f"✅ STT endpoint exists (422 validation error is expected without audio)")
    else:
        print(f"⚠️  STT endpoint returned {res.status_code}")
except Exception as e:
    print(f"❌ STT test failed: {e}")

# Test 4: Check if TTS endpoint exists
try:
    res = requests.post("http://localhost:8002/api/voice/tts", timeout=5)
    if res.status_code == 404:
        print(f"❌ TTS endpoint not found (404)")
    elif res.status_code == 422 or res.status_code == 400:
        print(f"✅ TTS endpoint exists ({res.status_code} validation error is expected without text)")
    else:
        print(f"⚠️  TTS endpoint returned {res.status_code}")
except Exception as e:
    print(f"❌ TTS test failed: {e}")

print("\n=== Summary ===")
print("If all tests passed, voice server is working correctly.")
print("If STT/TTS endpoints return 404, the voice server needs to be restarted:")
print("  cd e:\\PAN_APP\\pan-rag")
print("  .venv\\Scripts\\activate")
print("  uvicorn api.voice_main:app --host 0.0.0.0 --port 8002 --reload")
