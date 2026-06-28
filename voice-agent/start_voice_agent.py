"""
Voice Agent Startup Script

This script:
1. Validates environment configuration
2. Performs health checks
3. Starts the voice agent service on port 8002
4. Provides startup diagnostics and logging
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def check_environment():
    """Validate required environment variables"""
    print("🔧 Checking environment configuration...")
    
    required_vars = [
        "SARVAM_API_KEY",
        "NVIDIA_API_KEY",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in voice-agent/.env file")
        return False
    
    print("✅ Environment variables configured")
    return True

def check_dependencies():
    """Check if required Python packages are installed"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "sarvamai",
        "av",
        "numpy",
        "httpx"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed")
    return True

async def run_health_check():
    """Run the health check script"""
    print("🏥 Running health checks...")
    
    try:
        # Run the health check script
        result = subprocess.run([
            sys.executable, "health_check.py"
        ], cwd=Path(__file__).parent, capture_output=True, text=True, timeout=60)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Health check timed out")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def start_voice_service():
    """Start the voice agent service"""
    print("🚀 Starting voice agent service on port 8002...")
    
    # Set up environment
    env = os.environ.copy()
    env["VOICE_AGENT_PORT"] = "8002"
    env["VOICE_AGENT_HOST"] = "0.0.0.0"
    
    try:
        # Change to pan-rag directory to use existing voice_main.py
        pan_rag_dir = Path(__file__).parent.parent / "pan-rag"
        
        # Start the voice service using uvicorn
        cmd = [
            sys.executable, "-m", "uvicorn",
            "api.voice_main:app",
            "--host", "0.0.0.0",
            "--port", "8002",
            "--reload",
            "--log-level", "info"
        ]
        
        print(f"Executing: {' '.join(cmd)}")
        print(f"Working directory: {pan_rag_dir}")
        print("Press Ctrl+C to stop the service")
        print("-" * 50)
        
        # Run the service
        subprocess.run(cmd, cwd=pan_rag_dir, env=env, check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Voice agent service stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start voice service: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

async def main():
    """Main startup sequence"""
    print("🎤 Voice Agent Startup")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Step 1: Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Cannot start voice agent.")
        return 1
    
    # Step 2: Check dependencies  
    if not check_dependencies():
        print("\n❌ Dependency check failed. Cannot start voice agent.")
        return 1
    
    # Step 3: Run health checks (but don't fail startup if they fail)
    print()
    health_ok = await run_health_check()
    if not health_ok:
        print("⚠️  Some health checks failed, but starting service anyway...")
        print("The service may have limited functionality.")
    
    print("\n" + "=" * 50)
    
    # Step 4: Start the service
    if start_voice_service():
        print("✅ Voice agent service started successfully")
        return 0
    else:
        print("❌ Failed to start voice agent service")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Startup interrupted by user")
        sys.exit(1)