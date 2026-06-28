"""
Voice Agent Health Check Script

This script verifies:
1. SARVAM_API_KEY and NVIDIA_API_KEY connectivity
2. Sarvam AI STT/TTS service availability
3. NVIDIA NIM service connectivity 
4. Voice service endpoints status
5. Port 8002 availability
"""

import os
import sys
import asyncio
import tempfile
import wave
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_sarvam_connectivity():
    """Test Sarvam AI STT and TTS services"""
    print("🔍 Checking Sarvam AI connectivity...")
    
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("❌ SARVAM_API_KEY not found in environment")
        return False
        
    try:
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=api_key)
        
        # Test TTS with minimal text
        print("  Testing Sarvam TTS (bulbul:v3)...")
        tts_response = client.text_to_speech.convert(
            model="bulbul:v3",
            text="Hello",
            target_language_code="en-IN",
            speaker="aditya",
            speech_sample_rate=22050,
        )
        
        if hasattr(tts_response, "audios") and tts_response.audios:
            print("  ✅ Sarvam TTS working")
        else:
            print("  ❌ Sarvam TTS failed - no audio returned")
            return False
            
        # Test STT with generated audio
        print("  Testing Sarvam STT (saaras:v3)...")
        
        # Create a test WAV file
        test_wav_path = tempfile.mktemp(suffix=".wav")
        sample_rate = 16000
        duration = 1  # 1 second
        frequency = 440  # A4 note
        
        # Generate a simple sine wave
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
        
        with wave.open(test_wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) 
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
            
        try:
            with open(test_wav_path, "rb") as f:
                stt_response = client.speech_to_text.transcribe(
                    file=f,
                    model="saaras:v3",
                    mode="transcribe", 
                    language_code="en-IN"
                )
            print("  ✅ Sarvam STT accessible (note: test audio may not transcribe)")
        finally:
            Path(test_wav_path).unlink(missing_ok=True)
            
        return True
        
    except ImportError:
        print("  ❌ Sarvam AI SDK not installed - run: pip install sarvamai")
        return False
    except Exception as e:
        print(f"  ❌ Sarvam AI connection failed: {e}")
        return False

async def check_nvidia_connectivity():
    """Test NVIDIA NIM API connectivity"""
    print("🔍 Checking NVIDIA NIM connectivity...")
    
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("❌ NVIDIA_API_KEY not found in environment")
        return False
        
    try:
        import httpx
        
        # Test NVIDIA API endpoint
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Test with a simple chat completion request
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": "meta/llama-3.3-70b-instruct",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
            )
            
        if response.status_code == 200:
            print("  ✅ NVIDIA NIM API accessible")
            return True
        else:
            print(f"  ❌ NVIDIA API returned status {response.status_code}")
            return False
            
    except ImportError:
        print("  ❌ httpx not installed - run: pip install httpx")
        return False
    except Exception as e:
        print(f"  ❌ NVIDIA NIM connection failed: {e}")
        return False

async def check_voice_service_port():
    """Check if port 8002 is available for voice service"""
    print("🔍 Checking voice service port availability...")
    
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(("localhost", 8002))
        sock.close()
        
        if result == 0:
            print("  ⚠️  Port 8002 is already in use - voice service may be running")
            return True
        else:
            print("  ✅ Port 8002 is available")
            return True
            
    except Exception as e:
        print(f"  ❌ Port check failed: {e}")
        return False

async def check_voice_service_health():
    """Check if voice service is running and healthy"""
    print("🔍 Checking voice service health endpoint...")
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("http://localhost:8002/api/health")
            
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Voice service healthy: {data}")
            return True
        else:
            print(f"  ❌ Voice service returned status {response.status_code}")
            return False
            
    except httpx.ConnectError:
        print("  ⚠️  Voice service not running on port 8002")
        return False
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
        return False

async def main():
    """Run all health checks"""
    print("🚀 Voice Agent Health Check")
    print("=" * 50)
    
    checks = [
        ("Sarvam AI Connectivity", check_sarvam_connectivity()),
        ("NVIDIA NIM Connectivity", check_nvidia_connectivity()),
        ("Voice Service Port", check_voice_service_port()),
        ("Voice Service Health", check_voice_service_health()),
    ]
    
    results = {}
    for name, check in checks:
        try:
            results[name] = await check
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}")
            results[name] = False
        print()
    
    print("📊 Health Check Summary")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All health checks passed! Voice agent is ready.")
        return 0
    else:
        print("⚠️  Some health checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)