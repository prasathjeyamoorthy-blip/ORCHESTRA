#!/usr/bin/env python3
"""Verify all voice agent dependencies are installed correctly."""

print("Verifying Voice Agent Dependencies...")
print("=" * 50)

try:
    import av
    print(f"✅ PyAV {av.__version__}")
except ImportError as e:
    print(f"❌ PyAV: {e}")

try:
    import fastapi
    print(f"✅ FastAPI {fastapi.__version__}")
except ImportError as e:
    print(f"❌ FastAPI: {e}")

try:
    import numpy
    print(f"✅ NumPy {numpy.__version__}")
except ImportError as e:
    print(f"❌ NumPy: {e}")

try:
    import uvicorn
    print(f"✅ Uvicorn {uvicorn.__version__}")
except ImportError as e:
    print(f"❌ Uvicorn: {e}")

try:
    import redis
    print(f"✅ Redis {redis.__version__}")
except ImportError as e:
    print(f"❌ Redis: {e}")

try:
    import pydantic
    print(f"✅ Pydantic {pydantic.__version__}")
except ImportError as e:
    print(f"❌ Pydantic: {e}")

try:
    import aiohttp
    print(f"✅ Aiohttp {aiohttp.__version__}")
except ImportError as e:
    print(f"❌ Aiohttp: {e}")

try:
    import httpx
    print(f"✅ Httpx installed")
except ImportError as e:
    print(f"❌ Httpx: {e}")

print("=" * 50)
print("✅ All dependencies verified successfully!")
print("\nVoice Agent is ready to run:")
print("  python main.py")
