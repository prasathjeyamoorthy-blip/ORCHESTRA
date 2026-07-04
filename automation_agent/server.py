"""
FastAPI server for automation_agent.
Accepts POST /run with application data, runs browser automation, returns payment URL.

Start with:
    cd automation_agent
    .venv\Scripts\activate
    uvicorn server:app --port 8003 --reload
"""

import json
import traceback
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(title="PAN Automation Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── State ─────────────────────────────────────────────────────────────────────
_lock = threading.Lock()
_status = {"running": False, "result": None, "error": None}


class RunRequest(BaseModel):
    data: Dict[str, Any]          # The 30-field automation data
    session_id: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "running": _status["running"]}


@app.post("/run")
def run_automation(req: RunRequest):
    """
    Accept application data, write INPUT.json, run Playwright automation.
    Returns payment URL when complete.
    This is synchronous — caller should use a long timeout (300s).
    """
    with _lock:
        if _status["running"]:
            raise HTTPException(status_code=409, detail="Automation already running. Wait for it to finish.")
        _status["running"] = True
        _status["result"] = None
        _status["error"] = None

    try:
        data = req.data
        base_dir = Path(__file__).parent

        # Write INPUT.json so main.py logic can be reused
        input_path = base_dir / "INPUT.json"
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[server] Wrote INPUT.json ({len(data)} fields)")

        # Run the automation inline (same process, Playwright handles its own thread)
        from playwright.sync_api import sync_playwright
        from browser_manager import BrowserManager
        from workflow import PANApplicationWorkflow
        from data_handler import DataHandler

        applicant_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
        print(f"[server] Starting automation for: {applicant_name or 'N/A'}")

        payment_info = {}
        with sync_playwright() as playwright:
            browser = BrowserManager.create_browser(playwright, headless=False)
            context = BrowserManager.create_context(browser)
            page = BrowserManager.create_page(context)
            try:
                workflow = PANApplicationWorkflow(page, data)
                payment_info = workflow.execute()

                DataHandler.save_payment_info(
                    payment_url=payment_info["url"],
                    screenshot_path=payment_info.get("screenshot", "payment_page.png"),
                    data=data,
                )
                print(f"[server] ✓ Automation complete. Payment URL: {payment_info.get('url')}")
            finally:
                context.close()
                browser.close()

        result = {
            "status": "success",
            "payment_url": payment_info.get("url"),
            "payment_info": payment_info,
            "message": "✅ Application submitted successfully!",
        }
        _status["result"] = result
        return result

    except Exception as e:
        traceback.print_exc()
        err = str(e)
        _status["error"] = err
        raise HTTPException(status_code=500, detail=err)

    finally:
        _status["running"] = False


@app.get("/status")
def get_status():
    """Poll this to check if automation is still running."""
    return {
        "running": _status["running"],
        "result": _status["result"],
        "error": _status["error"],
    }
