"""
FastAPI server for automation_agent.
Accepts POST /run with application data, runs browser automation, returns payment URL.

Start with:
    cd automation_agent
    .venv\Scripts\activate
    uvicorn server:app --port 8003 --reload
"""

import json
import asyncio
import traceback
import threading
from pathlib import Path

# On Windows, force ProactorEventLoop globally so Playwright can spawn subprocesses.
if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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

        # Write INPUT.json — merge with any existing data so manually edited
        # fields are preserved. New data from the request takes priority.
        input_path = base_dir / "INPUT.json"
        existing_data = {}
        if input_path.exists():
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                pass  # corrupt file — start fresh

        # Merge: request data overrides existing, but keeps any extra fields
        merged_data = {**existing_data, **data}
        # Always stamp the last-updated time
        import datetime
        merged_data["_last_updated"] = datetime.datetime.now().isoformat()
        merged_data["_session_id"]   = req.session_id or ""

        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=4, ensure_ascii=False)
        print(f"[server] Wrote INPUT.json ({len(merged_data)} fields)")

        applicant_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
        print(f"[server] Starting automation for: {applicant_name or 'N/A'}")

        # sync_playwright() cannot run inside uvicorn's async event loop.
        # Run it in a dedicated thread that owns its own clean event loop.
        result_holder = {}

        def _run_in_thread():
            import asyncio
            # On Windows, the default SelectorEventLoop cannot spawn subprocesses.
            # Playwright needs subprocess support, so force ProactorEventLoop.
            if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            from playwright.sync_api import sync_playwright
            from browser_manager import BrowserManager
            from workflow import PANApplicationWorkflow
            from data_handler import DataHandler

            try:
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

                result_holder["result"] = {
                    "status": "success",
                    "payment_url": payment_info.get("url"),
                    "payment_info": payment_info,
                    "message": "✅ Application submitted successfully!",
                }
            except Exception as exc:
                result_holder["error"] = exc
                traceback.print_exc()

        t = threading.Thread(target=_run_in_thread, daemon=True)
        t.start()
        t.join(timeout=600)   # wait up to 10 minutes

        if t.is_alive():
            raise HTTPException(status_code=504, detail="Automation timed out after 10 minutes.")

        if "error" in result_holder:
            raise result_holder["error"]

        result = result_holder["result"]
        _status["result"] = result
        return result

    except HTTPException:
        raise
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
