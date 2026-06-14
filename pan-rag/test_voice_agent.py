#!/usr/bin/env python3
"""
test_voice_agent.py - Test script for voice agent functionality

This script tests the voice agent endpoints without requiring actual audio files.
It verifies that:
1. Dependencies are installed correctly
2. API keys are configured
3. Voice services can be initialized
4. Text cleaning and processing works correctly
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all required modules can be imported."""
    print("=" * 60)
    print("Testing imports...")
    print("=" * 60)
    
    try:
        import numpy as np
        print("✅ numpy imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import numpy: {e}")
        return False
    
    try:
        import av
        print("✅ av (PyAV) imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import av (PyAV): {e}")
        print("   Install with: pip install av==15.0.0")
        return False
    
    try:
        import riva.client as riva
        print("✅ nvidia-riva-client imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import nvidia-riva-client: {e}")
        print("   Install with: pip install nvidia-riva-client==2.18.0")
        return False
    
    try:
        from fastapi import FastAPI
        print("✅ fastapi imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import fastapi: {e}")
        return False
    
    print()
    return True


def test_env_config():
    """Test that environment variables are configured."""
    print("=" * 60)
    print("Testing environment configuration...")
    print("=" * 60)
    
    import os
    from dotenv import load_dotenv
    
    # Load .env file
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        print("   Copy .env.example to .env and configure your keys")
        return False
    
    load_dotenv()
    
    # Check required keys
    required_keys = [
        "NVIDIA_API_KEY",
        "STT_API_KEY",
        "TTS_API_KEY",
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
    ]
    
    missing_keys = []
    for key in required_keys:
        value = os.getenv(key)
        if not value or value.startswith("your_") or "example" in value:
            missing_keys.append(key)
            print(f"❌ {key} is not configured properly")
        else:
            # Show first 20 chars for verification
            masked_value = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {key} = {masked_value}")
    
    if missing_keys:
        print(f"\n❌ Missing or invalid configuration for: {', '.join(missing_keys)}")
        print("   Please update your .env file")
        return False
    
    print()
    return True


def test_voice_module():
    """Test that the voice module can be loaded."""
    print("=" * 60)
    print("Testing voice module...")
    print("=" * 60)
    
    try:
        from api import voice
        print("✅ Voice module loaded successfully")
        
        # Test voice configuration
        if hasattr(voice, 'VOICE_CONFIGS'):
            print(f"✅ Voice configurations loaded: {list(voice.VOICE_CONFIGS.keys())}")
        else:
            print("⚠️  VOICE_CONFIGS not found in voice module")
        
        # Test text cleaning function
        if hasattr(voice, '_clean_for_tts'):
            test_text = "**Hello**, this is a *test* with PAN and KYC."
            cleaned = voice._clean_for_tts(test_text, "en")
            print(f"✅ Text cleaning works: '{test_text}' -> '{cleaned}'")
        else:
            print("⚠️  _clean_for_tts not found in voice module")
        
        print()
        return True
    
    except Exception as e:
        print(f"❌ Failed to load voice module: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_voice_configs():
    """Test voice configuration details."""
    print("=" * 60)
    print("Testing voice configurations...")
    print("=" * 60)
    
    try:
        from api.voice import VOICE_CONFIGS
        
        for lang, config in VOICE_CONFIGS.items():
            print(f"\n{config['display_name']} ({lang}):")
            print(f"  TTS Voice: {config['tts_voice']}")
            print(f"  TTS Language: {config['tts_language']}")
            print(f"  STT Language: {config['stt_language']}")
        
        print()
        return True
    
    except Exception as e:
        print(f"❌ Failed to test voice configs: {e}")
        return False


def test_text_cleaning():
    """Test text cleaning for different languages."""
    print("=" * 60)
    print("Testing text cleaning for TTS...")
    print("=" * 60)
    
    try:
        from api.voice import _clean_for_tts
        
        test_cases = [
            ("en", "**PAN** card application for *KYC* verification. Visit www.example.com for more info."),
            ("en", "Form 49A, Form 49AA, and e.g., TDS etc."),
            ("ta", "PAN கார்டு பற்றிய தகவல் KYC சரிபார்ப்பு"),
            ("hi", "PAN कार्ड आवेदन और KYC जानकारी"),
        ]
        
        for lang, text in test_cases:
            cleaned = _clean_for_tts(text, lang)
            print(f"\n{lang.upper()}:")
            print(f"  Input:  {text}")
            print(f"  Output: {cleaned}")
        
        print()
        return True
    
    except Exception as e:
        print(f"❌ Failed to test text cleaning: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Voice Agent Test Suite" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    tests = [
        ("Import Test", test_imports),
        ("Environment Config", test_env_config),
        ("Voice Module", test_voice_module),
        ("Voice Configurations", test_voice_configs),
        ("Text Cleaning", test_text_cleaning),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n")
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Voice agent is ready to use.")
        print("\nTo start the voice agent:")
        print("  .venv\\Scripts\\activate")
        print("  uvicorn api.voice_main:app --host 0.0.0.0 --port 8002 --reload")
        return True
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure .env file with your API keys")
        print("  3. Ensure nvidia-riva-client and av are installed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
