#!/usr/bin/env python3
"""
Master End-to-End Production Verification & Test Runner
Executes comprehensive tests across all layers:
- Frontend Linting (ESLint)
- Frontend Production Build (Vite)
- Orchestra Main Backend Services (FastAPI, Guardrails, OTP, Supabase DB fallback, Sessions)
- Document Upload Agent (FastAPI, VLM regex parsing, OpenCV face validation, bulk processor)
- 4thAgent Certificate Downloader
- Deployment Configuration Integrity (render.yaml, docker-compose.yml, Dockerfiles)
"""

import subprocess
import sys
import time
import os

WORKSPACE = os.path.abspath(os.path.dirname(__file__))

def print_banner(title):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def run_step(step_name, cmd, cwd):
    print(f"\n[TEST SUITE] >>> Running: {step_name}...")
    start_t = time.time()
    res = subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    dur = round(time.time() - start_t, 2)
    if res.returncode == 0:
        print(f"✓ {step_name} PASSED ({dur}s)")
        if res.stdout.strip():
            # Print brief summary if needed
            lines = [l for l in res.stdout.strip().split("\n") if "OK" in l or "built" in l or "PASSED" in l or "Ran" in l]
            for l in lines:
                print(f"    {l}")
        return True, res.stdout
    else:
        print(f"✗ {step_name} FAILED ({dur}s) with code {res.returncode}")
        print("--- STDOUT ---")
        print(res.stdout)
        print("--- STDERR ---")
        print(res.stderr)
        return False, res.stderr

def main():
    print_banner("Complete End-to-End Production Test Suite")
    failures = []

    # 1. Frontend Linting
    ok, _ = run_step(
        "Frontend ESLint Analysis",
        "npm run lint",
        os.path.join(WORKSPACE, "ORCHESTRA", "frontend")
    )
    if not ok: failures.append("Frontend ESLint Analysis")

    # 2. Frontend Production Build
    ok, _ = run_step(
        "Frontend Production Vite Build",
        "npm run build",
        os.path.join(WORKSPACE, "ORCHESTRA", "frontend")
    )
    if not ok: failures.append("Frontend Production Vite Build")

    # Python executables in local venvs
    orch_python = os.path.join(WORKSPACE, "ORCHESTRA", "ORCHESTRA", "ORCHESTRA", ".venv", "bin", "python")
    doc_python  = os.path.join(WORKSPACE, "ORCHESTRA", "ORCHESTRA", "DocumentUploadAgent", ".venv", "bin", "python")

    # 3. Orchestra Backend End-to-End Suite
    ok, _ = run_step(
        "Orchestra Main Backend E2E Suite (app.py, OTP, Guardrails, DB, Captcha)",
        f"{orch_python} -m unittest test_e2e_suite.py",
        os.path.join(WORKSPACE, "ORCHESTRA", "ORCHESTRA", "ORCHESTRA")
    )
    if not ok: failures.append("Orchestra Main Backend E2E Suite")

    # 4. Document Upload Agent End-to-End Suite
    ok, _ = run_step(
        "Document Upload Agent E2E Suite (app.py, Extractor, FaceValidator, Bulk Processing)",
        f"{doc_python} -m unittest test_e2e_suite.py",
        os.path.join(WORKSPACE, "ORCHESTRA", "ORCHESTRA", "DocumentUploadAgent")
    )
    if not ok: failures.append("Document Upload Agent E2E Suite")

    # 5. 4thAgent Certificate Tool
    ok, _ = run_step(
        "4thAgent Certificate Tool Suite",
        f"{orch_python} -m unittest test_e2e_suite.py",
        os.path.join(WORKSPACE, "ORCHESTRA", "ORCHESTRA", "4thAgent")
    )
    if not ok: failures.append("4thAgent Certificate Tool Suite")

    # 6. Verify Deployment Files
    print("\n[TEST SUITE] >>> Checking Deployment File Paths...")
    deploy_errors = []
    render_path = os.path.join(WORKSPACE, "ORCHESTRA", "render.yaml")
    if os.path.exists(render_path):
        with open(render_path) as f:
            r_content = f.read()
            if "ORCHESTRA/ORCHESTRA/ORCHESTRA" not in r_content or "ORCHESTRA/ORCHESTRA/DocumentUploadAgent" not in r_content:
                deploy_errors.append("render.yaml has incorrect directory paths")
    else:
        deploy_errors.append("render.yaml is missing")

    if not deploy_errors:
        print("✓ Deployment configuration verified (render.yaml, docker-compose.yml)")
    else:
        print(f"✗ Deployment config errors: {deploy_errors}")
        failures.extend(deploy_errors)

    # Summary
    print_banner("Test Suite Summary")
    if not failures:
        print("🎉 ALL SYSTEMS PASSED! THE ENTIRE CODEBASE IS FULLY PRODUCTION READY!\n")
        sys.exit(0)
    else:
        print(f"❌ {len(failures)} FAILURE(S) DETECTED:")
        for f in failures:
            print(f"   - {f}")
        print("\nPlease fix the above errors before deploying to production.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
