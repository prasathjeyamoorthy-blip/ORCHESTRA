"""
Protean PAN Card — Resume Application + DOM Data Extraction
=============================================================
- Resumes a PAN application using a previously generated temporary token
- Reads all configuration from pan_config.json (editable by user)
- Extracts prefilled DOM data after login
- Continues to fill remaining form steps (3–9)
- OTP received via HTTP POST JSON from your backend
  → POST http://localhost:5055/otp  body: {"otp": "123456"}
  → GET  http://localhost:5055/status  (shows current step)
  → GET  http://localhost:5055/extracted  (shows scraped DOM data)

Usage:
    python pan_resume.py                    # uses pan_config.json
    python pan_resume.py --config my.json   # uses custom config file

Install:
    pip install DrissionPage speechrecognition pydub requests flask
    sudo apt install ffmpeg   # or: brew install ffmpeg
"""

import argparse
import json
import logging
import os
import threading
import time

from flask import Flask, request, jsonify
from DrissionPage import ChromiumPage, ChromiumOptions

# Import shared utilities from the main PAN script
from pan_apply_full import (
    safe_select,
    safe_input,
    click_next,
    _env_flag,
    _detect_browser_path,
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("pan_resume")

URL = "https://onlineservices.proteantech.in/paam/endUserRegisterContact.html"
DEFAULT_CONFIG = "pan_config.json"

# ══════════════════════════════════════════════════════════════
#  CONFIG LOADER — reads pan_config.json
# ══════════════════════════════════════════════════════════════
def load_config(config_path: str) -> dict:
    """Load configuration from a JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Please create {config_path} with your resume and applicant data."
        )
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    log.info(f"Config loaded from {config_path}")
    return cfg


# ══════════════════════════════════════════════════════════════
#  OTP + DATA SERVER  (Flask – runs in background thread)
# ══════════════════════════════════════════════════════════════
_otp_store  = {"otp": None, "step": "idle"}
_otp_event  = threading.Event()
_extracted  = {}    # DOM data stored here after extraction

flask_app = Flask(__name__)


@flask_app.route("/otp", methods=["POST"])
def receive_otp():
    data = request.get_json(force=True)
    if not data or "otp" not in data:
        return jsonify({"error": 'Send JSON body: {"otp": "123456"}'}), 400
    _otp_store["otp"] = str(data["otp"]).strip()
    _otp_event.set()
    log.info(f"[OTP Server] Received OTP: {_otp_store['otp']}")
    return jsonify({"status": "ok", "otp_received": _otp_store["otp"]}), 200


@flask_app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "current_step":    _otp_store["step"],
        "waiting_for_otp": not _otp_event.is_set(),
    }), 200


@flask_app.route("/extracted", methods=["GET"])
def get_extracted():
    """Return the DOM data scraped after resume login."""
    return jsonify(_extracted), 200


def start_flask_server(port: int):
    log.info(f"[Server] Listening on http://0.0.0.0:{port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def wait_for_otp_local(label: str, port: int, timeout: int = 300) -> str:
    """Block until OTP is POSTed, then return it."""
    _otp_store["step"] = label
    _otp_event.clear()
    log.info(f"[OTP] Waiting for OTP ({label}) — POST to http://localhost:{port}/otp")
    received = _otp_event.wait(timeout=timeout)
    if not received:
        raise TimeoutError(f"OTP not received within {timeout}s for step: {label}")
    otp = _otp_store["otp"]
    _otp_store["otp"] = None
    return otp


# ══════════════════════════════════════════════════════════════
#  DOM DATA EXTRACTION
# ══════════════════════════════════════════════════════════════
def extract_page_data(page) -> dict:
    """
    Extract all form field values and page state from the current DOM.
    Captures inputs, selects, textareas, visible messages, and page metadata.
    """
    fields = {}

    # ── Input fields ───────────────────────────────────────────
    try:
        for el in page.eles("tag:input"):
            try:
                name = el.attr("name") or el.attr("id") or ""
                input_type = (el.attr("type") or "text").lower()
                if not name or input_type in ("hidden", "submit", "button", "reset"):
                    continue
                if input_type in ("checkbox", "radio"):
                    fields[name] = {
                        "value":   el.attr("value") or "",
                        "checked": bool(el.attr("checked")),
                        "type":    input_type,
                    }
                else:
                    fields[name] = el.attr("value") or ""
            except Exception:
                continue
    except Exception as e:
        log.warning(f"[Extract] Error reading inputs: {e}")

    # ── Select dropdowns ───────────────────────────────────────
    try:
        for el in page.eles("tag:select"):
            try:
                name = el.attr("name") or el.attr("id") or ""
                if not name:
                    continue
                # Get selected option text and value
                try:
                    selected_opts = el.eles("tag:option")
                    selected_text = ""
                    selected_value = ""
                    all_options = []
                    for opt in selected_opts:
                        opt_text = opt.text.strip()
                        opt_val = opt.attr("value") or ""
                        all_options.append({"value": opt_val, "text": opt_text})
                        if opt.attr("selected") is not None:
                            selected_text = opt_text
                            selected_value = opt_val
                    fields[name] = {
                        "selected_value": selected_value,
                        "selected_text":  selected_text,
                        "options":        all_options,
                        "type":           "select",
                    }
                except Exception:
                    fields[name] = {"type": "select", "selected_value": ""}
            except Exception:
                continue
    except Exception as e:
        log.warning(f"[Extract] Error reading selects: {e}")

    # ── Textarea fields ────────────────────────────────────────
    try:
        for el in page.eles("tag:textarea"):
            try:
                name = el.attr("name") or el.attr("id") or ""
                if name:
                    fields[name] = el.text or ""
            except Exception:
                continue
    except Exception as e:
        log.warning(f"[Extract] Error reading textareas: {e}")

    # ── Visible messages / errors / alerts ─────────────────────
    messages = []
    for selector in [
        "xpath://*[contains(@class,'error')]",
        "xpath://*[contains(@class,'alert')]",
        "xpath://*[contains(@class,'success')]",
        "xpath://*[contains(@class,'msg')]",
        "xpath://*[contains(@class,'message')]",
        "xpath://*[contains(@id,'error')]",
        "xpath://*[contains(@id,'msg')]",
    ]:
        try:
            for el in page.eles(selector, timeout=2):
                txt = el.text.strip()
                if txt and len(txt) < 500:
                    messages.append(txt)
        except Exception:
            continue

    # ── Page heading / step indicator ──────────────────────────
    headings = []
    for tag in ["h1", "h2", "h3", "h4", "h5"]:
        try:
            for el in page.eles(f"tag:{tag}", timeout=2):
                txt = el.text.strip()
                if txt:
                    headings.append(txt)
        except Exception:
            continue

    result = {
        "title":    page.title,
        "url":      page.url,
        "fields":   fields,
        "messages": list(set(messages)),
        "headings": headings,
    }
    return result


def save_extracted_data(data: dict, path: str = "pan_extracted.json"):
    """Save extracted DOM data to a JSON file for inspection."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        log.info(f"Extracted data saved to {path}")
    except Exception as e:
        log.warning(f"Could not save extracted data: {e}")


# ══════════════════════════════════════════════════════════════
#  RESUME STEP R1 — Navigate + Click Resume Tab
# ══════════════════════════════════════════════════════════════
def step_r1_navigate(page):
    log.info("=== Resume R1: Navigate to PAAM page ===")
    page.get(URL)
    log.info("[R1] Page loaded.")

    # Wait for tab structure to appear
    try:
        page.ele("tag:a@id:resumeappl", timeout=15)
    except Exception:
        log.warning("[R1] Resume tab not found within timeout.")

    # Click "Resume Application" tab
    try:
        page.ele("tag:a@id:resumeappl", timeout=8).click()
        time.sleep(1)
        log.info("[R1] Resume Application tab clicked.")
    except Exception as e:
        log.error(f"[R1] Could not click Resume tab: {e}")
        raise RuntimeError("Resume tab not available on the page.")


# ══════════════════════════════════════════════════════════════
#  RESUME STEP R2 — Fill Token / Email / DOB
# ══════════════════════════════════════════════════════════════
def step_r2_fill_resume_form(page, resume_data: dict):
    log.info("=== Resume R2: Fill resume form ===")

    token = resume_data.get("token_number", "")
    email = resume_data.get("email", "")
    dob   = resume_data.get("dob", "")

    if not token:
        raise ValueError("token_number is required in config")
    if not email:
        raise ValueError("email is required in config")
    if not dob:
        raise ValueError("dob is required in config")

    token_ok = safe_input(page, "tag:input@id:token_number", token)
    email_ok = safe_input(page, "tag:input@id:email_id1", email)
    dob_ok   = safe_input(page, "tag:input@id:dob", dob)

    if not all([token_ok, email_ok, dob_ok]):
        raise RuntimeError(
            f"Resume form fields not filled: token={token_ok}, email={email_ok}, dob={dob_ok}"
        )
    log.info(f"[R2] Form filled — Token: {token}, Email: {email}, DOB: {dob}")



# ══════════════════════════════════════════════════════════════
#  RESUME STEP R3 — Solve reCAPTCHA + Submit
#  Uses GoogleRecaptchaBypass/RecaptchaSolver for audio bypass.
#  Falls back to manual solve for Enterprise reCAPTCHA (no audio).
# ══════════════════════════════════════════════════════════════

def step_r3_captcha_and_submit(page):
    log.info("=== Resume R3: reCAPTCHA + Submit ===")

    # ── Import solver ─────────────────────────────────────────
    import sys
    solver_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GoogleRecaptchaBypass")
    if solver_dir not in sys.path:
        sys.path.insert(0, solver_dir)
    from RecaptchaSolver import RecaptchaSolver

    # ── Handle dual-reCAPTCHA ─────────────────────────────────
    # Rename tab1's iframe title so the solver ignores it.
    try:
        page.run_js("""
            var tab1 = document.getElementById('left-icon-tab1');
            if (tab1) {
                tab1.querySelectorAll('iframe[title="reCAPTCHA"]').forEach(function(f) {
                    f.title = 'reCAPTCHA-hidden';
                });
            }
            var tab2 = document.getElementById('left-icon-tab2');
            if (tab2) {
                var rc = tab2.querySelectorAll('.g-recaptcha');
                if (rc.length > 0)
                    rc[rc.length - 1].scrollIntoView({behavior: 'smooth', block: 'center'});
            }
        """)
        time.sleep(1)
        log.info("[R3] Tab1 reCAPTCHA hidden — targeting Resume tab")
    except Exception as e:
        log.warning(f"[R3] Could not hide tab1 reCAPTCHA: {e}")

    # ── Click the checkbox (using same API as RecaptchaSolver) ─
    log.info("[R3] Clicking reCAPTCHA checkbox...")
    try:
        page.wait.ele_displayed("@title=reCAPTCHA", timeout=10)
        time.sleep(0.3)
        iframe_inner = page("@title=reCAPTCHA")
        iframe_inner.wait.ele_displayed(".rc-anchor-content", timeout=10)
        iframe_inner(".rc-anchor-content", timeout=3).click()
        time.sleep(2)
    except Exception as e:
        raise RuntimeError(f"Could not click reCAPTCHA checkbox: {e}")

    # ── Check if passed instantly ─────────────────────────────
    solver = RecaptchaSolver(page)
    if solver.is_solved():
        log.info("[R3] reCAPTCHA passed instantly (no challenge)!")
        _restore_captcha_titles(page)
        _submit_resume_form(page)
        return

    # ── Try audio bypass (works on standard, fails on Enterprise) ──
    log.info("[R3] Challenge appeared — trying audio bypass...")
    audio_solved = False
    try:
        # Find the challenge bframe
        iframe = solver._get_challenge_iframe()

        # Try to click audio button
        try:
            iframe.wait.ele_displayed("#recaptcha-audio-button", timeout=5)
            iframe("#recaptcha-audio-button", timeout=3).click()
            time.sleep(0.5)
            log.info("[R3] Audio button clicked — processing audio challenge...")
        except Exception:
            log.warning("[R3] No audio button — this is Enterprise reCAPTCHA (audio blocked)")
            raise Exception("Enterprise reCAPTCHA — no audio button")

        # If audio button worked, use the solver's full audio loop
        if solver.is_detected():
            raise Exception("Bot detected")

        for _ in range(5):
            try:
                src = solver._get_audio_source_url()
                text = solver._process_audio_challenge(src)
                log.info(f"[R3] Audio recognized: '{text}'")
                solver._submit_audio_response(text)
                time.sleep(0.5)

                if solver.is_solved():
                    audio_solved = True
                    log.info("[R3] reCAPTCHA SOLVED via audio bypass!")
                    break

                solver._reload_audio_challenge()
                time.sleep(0.5)
            except Exception as e:
                log.warning(f"[R3] Audio attempt failed: {e}")
                solver._reload_audio_challenge()
                time.sleep(0.5)

    except Exception as e:
        log.info(f"[R3] Audio bypass not available: {e}")

    # ── Manual fallback ───────────────────────────────────────
    if not audio_solved and not solver.is_solved():
        is_headless = _env_flag("PAN_HEADLESS", os.name != "nt")
        if is_headless:
            _restore_captcha_titles(page)
            raise RuntimeError(
                "reCAPTCHA requires manual solve. Run with PAN_HEADLESS=0."
            )

        log.info("")
        log.info("  ┌──────────────────────────────────────────────┐")
        log.info("  │  MANUAL CAPTCHA REQUIRED                     │")
        log.info("  │  Solve the image challenge in the browser,   │")
        log.info("  │  then the script will continue automatically.│")
        log.info("  │  Timeout: 180 seconds                        │")
        log.info("  └──────────────────────────────────────────────┘")
        log.info("")

        deadline = time.time() + 180
        while time.time() < deadline:
            if solver.is_solved():
                log.info("[R3] reCAPTCHA solved manually!")
                break
            time.sleep(2)
        else:
            _restore_captcha_titles(page)
            raise RuntimeError("reCAPTCHA not solved within 180s timeout.")

    _restore_captcha_titles(page)
    _submit_resume_form(page)


def _restore_captcha_titles(page):
    """Restore renamed reCAPTCHA iframe titles."""
    try:
        page.run_js("""
            document.querySelectorAll('iframe[title="reCAPTCHA-hidden"]').forEach(function(f) {
                f.title = 'reCAPTCHA';
            });
        """)
    except Exception:
        pass



def _submit_resume_form(page):
    """Click Submit on the resume tab after captcha is solved."""
    time.sleep(1)
    try:
        page.ele("tag:button@id:submitFormLogin", timeout=5).click()
        time.sleep(4)
        log.info("[R3] Submit clicked.")
    except Exception:
        if not click_next(page):
            raise RuntimeError("Could not submit the resume form.")

    # Check for error messages
    try:
        error_els = page.eles("xpath://*[contains(@class,'error') or contains(@class,'alert-danger')]", timeout=3)
        for el in error_els:
            txt = el.text.strip()
            if txt:
                log.warning(f"[R3] Error message: {txt}")
    except Exception:
        pass

    log.info("[R3] Resume form submitted successfully.")

# ══════════════════════════════════════════════════════════════
#  RESUME STEP R4 — Extract DOM Data After Login
# ══════════════════════════════════════════════════════════════
def step_r4_extract_data(page) -> dict:
    log.info("=== Resume R4: Extracting DOM data ===")

    # Wait for the next page to fully load
    time.sleep(3)

    data = extract_page_data(page)
    _extracted.update(data)  # Store globally for /extracted endpoint

    save_extracted_data(data)

    log.info(f"[R4] Extracted {len(data['fields'])} fields from page: {data['title']}")
    if data["headings"]:
        log.info(f"[R4] Page headings: {data['headings']}")
    if data["messages"]:
        for msg in data["messages"]:
            log.info(f"[R4] Message: {msg}")

    return data


# ══════════════════════════════════════════════════════════════
#  POST-LOGIN WIZARD — Helpers
# ══════════════════════════════════════════════════════════════
def _select2_set(page, container_id: str, option_text: str):
    """
    Set a Select2 dropdown value by opening it, typing search text,
    and selecting the matching option.
    
    container_id: the id of the Select2 container span (e.g. 'select2-gender-container')
    option_text:  text to search and select
    """
    if not option_text:
        return False
    try:
        # Click the Select2 container to open it
        page.ele(f"@id:{container_id}", timeout=5).click()
        time.sleep(0.5)
        # Type into the search input
        try:
            search = page.ele("tag:input@class:select2-search__field", timeout=3)
            search.clear()
            search.input(option_text)
            time.sleep(0.8)
        except Exception:
            pass
        # Click the first matching result
        try:
            result = page.ele("xpath://li[contains(@class,'select2-results__option')]", timeout=3)
            result.click()
            time.sleep(0.3)
            log.info(f"[Select2] Set '{container_id}' → '{option_text}'")
            return True
        except Exception:
            # Try clicking highlighted result
            try:
                page.ele(".select2-results__option--highlighted", timeout=2).click()
                time.sleep(0.3)
                return True
            except Exception:
                pass
    except Exception as e:
        log.warning(f"[Select2] Failed to set '{container_id}': {e}")
    return False


def _wizard_click_next(page) -> bool:
    """Click the wizard 'Next' button (.button-next)."""
    for sel in [
        "xpath://button[contains(@class,'button-next')]",
        "xpath://a[contains(@class,'button-next')]",
        "xpath://*[contains(@class,'button-next')]",
        "xpath://button[contains(text(),'Next')]",
        "xpath://a[contains(text(),'Next')]",
    ]:
        try:
            btn = page.ele(sel, timeout=3)
            btn.click()
            time.sleep(2)
            log.info("[Wizard] Clicked 'Next'")
            return True
        except Exception:
            continue
    log.warning("[Wizard] Could not find 'Next' button")
    return False


def _wizard_click_back(page) -> bool:
    """Click the wizard 'Back' button (.button-back)."""
    for sel in [
        "xpath://button[contains(@class,'button-back')]",
        "xpath://a[contains(@class,'button-back')]",
        "xpath://button[contains(text(),'Back')]",
    ]:
        try:
            page.ele(sel, timeout=3).click()
            time.sleep(2)
            log.info("[Wizard] Clicked 'Back'")
            return True
        except Exception:
            continue
    return False


def _wizard_save_draft(page):
    """Click 'Save Draft' button if available."""
    try:
        page.ele("@id:saveForm", timeout=2).click()
        time.sleep(1.5)
        log.info("[Wizard] Draft saved.")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
#  WIZARD STEP 2 — Personal Details (Guidelines is Step 1)
# ══════════════════════════════════════════════════════════════
def wizard_step2_personal(page, cfg: dict):
    """
    Fill the Personal Details wizard step.
    
    Fields on this page (IDs from live DOM):
      - eVerfication4 / eVerfication3 / eVerfication1: Submission mode radios
      - appli_epan_op1_y / appli_epan_op1_n: Physical PAN or e-PAN only
      - aadhaarNo_2: Last 4 digits of Aadhaar
      - consentEkyc: Aadhaar photo consent (Select2: select2-consentEkyc-container)
      - f_name, m_name, l_name: Applicant name
      - date_of_birth: DOB (readonly, prefilled)
      - gender: Gender (Select2: select2-gender-container)
      - faf_name, fam_name, fal_name: Father's name
      - mof_name, mom_name, mol_name: Mother's name  
      - parent_father / parent_mother: Which parent name on card (radio)
    """
    log.info("=== Wizard Step 2: Personal Details ===")

    # Step 1 (Guidelines) is typically auto-passed or is just info — skip to 2
    # Click through guidelines if visible
    _wizard_click_next(page)
    time.sleep(1)

    # ── Submission mode: e-KYC via Aadhaar (most common) ──────
    ekyc_mode = cfg.get("submission_mode", "aadhaar_ekyc")
    mode_ids = {
        "aadhaar_ekyc": "eVerfication4",
        "scanned":      "eVerfication3",
        "physical":     "eVerfication1",
    }
    mode_id = mode_ids.get(ekyc_mode, "eVerfication4")
    try:
        page.ele(f"@id:{mode_id}", timeout=5).click()
    except Exception as e:
        log.warning(f"[Step2] Could not click submission mode {mode_id}: {e}")
    time.sleep(0.5)

    # ── PAN type: Physical + e-PAN or e-PAN only ──────────────
    paperless = cfg.get("paperless", True)
    if paperless:
        try:
            page.ele("@id:appli_epan_op1_n", timeout=3).click()
        except Exception:
            pass
    else:
        try:
            page.ele("@id:appli_epan_op1_y", timeout=3).click()
        except Exception:
            pass
    time.sleep(0.3)

    # ── Aadhaar last 4 digits ─────────────────────────────────
    aadhaar = cfg.get("aadhaar_number", "")
    if aadhaar and len(aadhaar) >= 4:
        last4 = aadhaar[-4:]
        safe_input(page, "@id:aadhaarNo_2", last4)

    # ── Aadhaar photo consent ─────────────────────────────────
    consent = cfg.get("aadhaar_photo_consent", "Yes")
    _select2_set(page, "select2-consentEkyc-container", consent)

    # ── Applicant Name ────────────────────────────────────────
    # Name fields may be readonly if prefilled from Aadhaar e-KYC
    safe_input(page, "@id:l_name", cfg.get("last_name", ""))
    safe_input(page, "@id:f_name", cfg.get("first_name", ""))
    safe_input(page, "@id:m_name", cfg.get("middle_name", ""))

    # DOB (likely readonly/prefilled)
    safe_input(page, "@id:date_of_birth", cfg.get("dob", ""))

    # ── Gender ────────────────────────────────────────────────
    gender_map = {"M": "Male", "F": "Female", "T": "Transgender"}
    gender = cfg.get("gender", "M")
    _select2_set(page, "select2-gender-container", gender_map.get(gender, gender))

    # ── Father's Name ─────────────────────────────────────────
    safe_input(page, "@id:fal_name", cfg.get("father_last", ""))
    safe_input(page, "@id:faf_name", cfg.get("father_first", ""))
    safe_input(page, "@id:fam_name", cfg.get("father_middle", ""))

    # ── Mother's Name ─────────────────────────────────────────
    safe_input(page, "@id:mol_name", cfg.get("mother_last", ""))
    safe_input(page, "@id:mof_name", cfg.get("mother_first", ""))
    safe_input(page, "@id:mom_name", cfg.get("mother_middle", ""))

    # ── Parent name on card ───────────────────────────────────
    name_on_card = cfg.get("name_on_card", "father")
    if name_on_card.lower() == "mother":
        try:
            page.ele("@id:parent_mother", timeout=3).click()
        except Exception:
            pass
    else:
        try:
            page.ele("@id:parent_father", timeout=3).click()
        except Exception:
            pass

    time.sleep(0.5)
    _wizard_click_next(page)
    log.info("[Step2] Personal details completed → Next")


# ══════════════════════════════════════════════════════════════
#  WIZARD STEP 3 — Contact & Other Details
# ══════════════════════════════════════════════════════════════
def wizard_step3_contact(page, cfg: dict):
    """
    Fill Contact & Other Details wizard step.
    
    Fields (IDs from live DOM):
      - sal_id, buss, inc_house, no_income: Source of Income checkboxes
      - Residence / Office: Communication address radio
      - country_name (Select2): Country
      - flat_door, building, road_street, area, city, state, pin_code: Address
      - state (Select2): State
      - mobile_num, email_id, tel_num_stdcode, tel_num: Contact
      - residential_status_r / residential_status_n: Resident status radio
      - passport_num, tin_num: TIN/Passport
      - rep_assessee_y / rep_assessee_n: Representative Assessee radio
    """
    log.info("=== Wizard Step 3: Contact & Other Details ===")

    # ── Source of Income ──────────────────────────────────────
    income = cfg.get("source_of_income", "No income").lower()
    if "no income" in income:
        try:
            page.ele("@id:no_income", timeout=3).click()
        except Exception:
            pass
    elif "salary" in income:
        try:
            page.ele("@id:sal_id", timeout=3).click()
        except Exception:
            pass
    elif "business" in income:
        try:
            page.ele("@id:buss", timeout=3).click()
        except Exception:
            pass
    elif "house" in income:
        try:
            page.ele("@id:inc_house", timeout=3).click()
        except Exception:
            pass

    # ── Communication Address: Residence ──────────────────────
    addr_type = cfg.get("address_type", "Residence")
    if addr_type.lower() == "office":
        try:
            page.ele("@id:Office", timeout=3).click()
        except Exception:
            pass
    else:
        try:
            page.ele("@id:Residence", timeout=3).click()
        except Exception:
            pass
    time.sleep(0.3)

    # ── Country ───────────────────────────────────────────────
    country = cfg.get("address_country", "India")
    _select2_set(page, "select2-country_name-container", country)
    time.sleep(0.5)

    # ── Address fields ────────────────────────────────────────
    safe_input(page, "@id:flat_door", cfg.get("address_flat", ""))
    safe_input(page, "@id:building", cfg.get("address_building", ""))
    safe_input(page, "@id:road_street", cfg.get("address_street", ""))
    safe_input(page, "@id:area", cfg.get("address_area", ""))
    safe_input(page, "@id:city", cfg.get("address_city", ""))
    safe_input(page, "@id:pin_code", cfg.get("address_pin", ""))

    # ── State (Select2) ──────────────────────────────────────
    state = cfg.get("address_state", "")
    if state:
        _select2_set(page, "select2-state-container", state)

    # ── Contact ───────────────────────────────────────────────
    safe_input(page, "@id:mobile_num", cfg.get("mobile", ""))
    safe_input(page, "@id:email_id", cfg.get("email", ""))
    safe_input(page, "@id:tel_num_stdcode", cfg.get("tel_std_code", ""))
    safe_input(page, "@id:tel_num", cfg.get("tel_number", ""))

    # ── Residential Status ────────────────────────────────────
    res_status = cfg.get("residential_status", "Resident")
    if "non" in res_status.lower():
        try:
            page.ele("@id:residential_status_n", timeout=3).click()
        except Exception:
            pass
    else:
        try:
            page.ele("@id:residential_status_r", timeout=3).click()
        except Exception:
            pass

    # ── Passport / TIN ────────────────────────────────────────
    safe_input(page, "@id:passport_num", cfg.get("passport_number", ""))
    safe_input(page, "@id:tin_num", cfg.get("taxpayer_id", ""))

    # ── Representative Assessee ───────────────────────────────
    rep = cfg.get("representative_assessee", False)
    if rep:
        try:
            page.ele("@id:rep_assessee_y", timeout=3).click()
        except Exception:
            pass
    else:
        try:
            page.ele("@id:rep_assessee_n", timeout=3).click()
        except Exception:
            pass

    time.sleep(0.5)
    _wizard_click_next(page)
    log.info("[Step3] Contact details completed → Next")


# ══════════════════════════════════════════════════════════════
#  WIZARD STEP 4 — AO Code
# ══════════════════════════════════════════════════════════════
def wizard_step4_ao_code(page, cfg: dict):
    """
    Fill AO Code wizard step.
    
    Fields (IDs from live DOM):
      - area_code, ao_type, range_code, ao_num: Tax jurisdiction
      - state_ao_help, city_ao_help: Helper dropdowns for code lookup
      
    The AO Code table is auto-populated when using Aadhaar e-KYC.
    If already selected, just click Next.
    """
    log.info("=== Wizard Step 4: AO Code ===")

    # Check if AO codes are already prefilled (common with e-KYC)
    ao_area = ""
    try:
        el = page.ele("@id:area_code", timeout=3)
        ao_area = el.attr("value") or ""
    except Exception:
        pass

    if ao_area:
        log.info(f"[Step4] AO Code already filled: {ao_area}")
    else:
        # Try to auto-select via helper dropdowns
        state_ao = cfg.get("ao_state", cfg.get("address_state", ""))
        city_ao = cfg.get("ao_city", cfg.get("address_city", ""))

        if state_ao:
            try:
                page.ele("@id:state_ao_help", timeout=3)
                safe_select(page, "@id:state_ao_help", state_ao)
                time.sleep(1)
            except Exception:
                pass

        if city_ao:
            try:
                safe_select(page, "@id:city_ao_help", city_ao)
                time.sleep(1)
            except Exception:
                pass

        # Try to select first AO entry from the table
        try:
            ao_row = page.ele("xpath://table//tr[contains(@onclick,'selectAO')]", timeout=3)
            ao_row.click()
            time.sleep(0.5)
            log.info("[Step4] AO Code selected from table")
        except Exception:
            # Manual AO entry
            safe_input(page, "@id:area_code", cfg.get("ao_area_code", ""))
            safe_input(page, "@id:ao_type", cfg.get("ao_type", ""))
            safe_input(page, "@id:range_code", cfg.get("ao_range_code", ""))
            safe_input(page, "@id:ao_num", cfg.get("ao_number", ""))

    time.sleep(0.5)
    _wizard_click_next(page)
    log.info("[Step4] AO Code completed → Next")


# ══════════════════════════════════════════════════════════════
#  WIZARD STEP 5 — Document Details + Declaration + Submit
# ══════════════════════════════════════════════════════════════
def wizard_step5_documents(page, cfg: dict):
    """
    Fill Document Details and Declaration wizard step.
    
    Fields (IDs from live DOM):
      - identity_doc (Select2): Proof of Identity
      - dob_doc (Select2): Proof of DOB
      - address_doc (Select2): Proof of Address (may be same page)
      - declarationName: Declaration name
      - verifierPlace: Verification place
      - currentDateId: Current date (auto-filled)
      - docsUpload / doc1: Document upload (PDF, max 300KB)
      - submitFormSTM: Final submit button
    """
    log.info("=== Wizard Step 5: Documents & Declaration ===")

    # ── Proof of Identity ─────────────────────────────────────
    id_proof = cfg.get("proof_identity", "Aadhaar Card")
    _select2_set(page, "select2-identity_doc-container", id_proof)
    time.sleep(0.3)

    # ── Proof of Date of Birth ────────────────────────────────
    dob_proof = cfg.get("proof_dob", "Aadhaar Card")
    _select2_set(page, "select2-dob_doc-container", dob_proof)
    time.sleep(0.3)

    # ── Proof of Address (if visible on same page) ────────────
    addr_proof = cfg.get("proof_address", "Aadhaar Card")
    try:
        _select2_set(page, "select2-address_doc-container", addr_proof)
    except Exception:
        pass

    # ── Declaration Name ──────────────────────────────────────
    decl_name = cfg.get("declaration_name", "")
    if not decl_name:
        # Build from first/last name
        fn = cfg.get("first_name", "")
        ln = cfg.get("last_name", "")
        decl_name = f"{fn} {ln}".strip()
    safe_input(page, "@id:declarationName", decl_name)

    # ── Verification Place ────────────────────────────────────
    place = cfg.get("verification_place", cfg.get("address_city", ""))
    safe_input(page, "@id:verifierPlace", place)

    # ── Document Upload (skip if using e-KYC — not required) ──
    doc_path = cfg.get("document_upload_path", "")
    if doc_path and os.path.exists(doc_path):
        try:
            upload = page.ele("@id:docsUpload", timeout=3)
            upload.input(doc_path)
            time.sleep(1)
            log.info(f"[Step5] Document uploaded: {doc_path}")
        except Exception:
            try:
                upload = page.ele("@id:doc1", timeout=3)
                upload.input(doc_path)
                time.sleep(1)
            except Exception as e:
                log.warning(f"[Step5] Document upload failed: {e}")

    log.info("[Step5] Documents & declaration filled")

    # ── Final Submit ──────────────────────────────────────────
    # Don't auto-submit — let the user review first
    log.info("[Step5] Ready for final submission.")
    log.info("[Step5] Review the form in the browser, then:")
    log.info("[Step5]   → Click 'Submit' (id=submitFormSTM) manually, OR")
    log.info("[Step5]   → Type 'submit' below to auto-submit.")

    return True


def wizard_final_submit(page):
    """Click the final submit button."""
    try:
        page.ele("@id:submitFormSTM", timeout=5).click()
        time.sleep(3)
        log.info("[Submit] Final form submitted!")
        return True
    except Exception as e:
        log.error(f"[Submit] Could not click submit: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  RESUME STEP R5 — Orchestrate Wizard Steps 2–5
# ══════════════════════════════════════════════════════════════
def step_r5_continue_application(page, applicant_data: dict, otp_port: int):
    """
    After resume login, the application opens at the Personal Details wizard.
    The post-login page (endUserLogin.html?type=A) has a 5-step wizard:
      Step 1: Guidelines (auto-skip)
      Step 2: Personal Details
      Step 3: Contact & Other Details
      Step 4: AO Code
      Step 5: Document Details + Declaration + Submit
    """
    log.info("=== Resume R5: Continuing application (5-step wizard) ===")
    steps_completed = []

    # Detect which wizard step we're on
    current_step = _detect_wizard_step(page)
    log.info(f"[R5] Currently on wizard step: {current_step}")

    # ── Step 2: Personal Details ──────────────────────────────
    if current_step <= 2:
        try:
            wizard_step2_personal(page, applicant_data)
            steps_completed.append("personal_details")
            # Re-extract after step
            data = extract_page_data(page)
            save_extracted_data(data, "pan_step3_contact.json")
        except Exception as e:
            log.error(f"[R5] Personal details failed: {e}")
            return steps_completed

    # ── Step 3: Contact & Other Details ───────────────────────
    if current_step <= 3:
        try:
            wizard_step3_contact(page, applicant_data)
            steps_completed.append("contact_details")
            data = extract_page_data(page)
            save_extracted_data(data, "pan_step4_ao.json")
        except Exception as e:
            log.error(f"[R5] Contact details failed: {e}")
            return steps_completed

    # ── Step 4: AO Code ───────────────────────────────────────
    if current_step <= 4:
        try:
            wizard_step4_ao_code(page, applicant_data)
            steps_completed.append("ao_code")
            data = extract_page_data(page)
            save_extracted_data(data, "pan_step5_docs.json")
        except Exception as e:
            log.error(f"[R5] AO Code failed: {e}")
            return steps_completed

    # ── Step 5: Documents + Declaration ───────────────────────
    if current_step <= 5:
        try:
            wizard_step5_documents(page, applicant_data)
            steps_completed.append("documents")
        except Exception as e:
            log.error(f"[R5] Documents failed: {e}")
            return steps_completed

    return steps_completed


def _detect_wizard_step(page) -> int:
    """
    Detect the current wizard step number (1-5) based on the
    active step indicator in the progress bar.
    """
    try:
        # Look for active step in the wizard progress bar
        body_text = page.ele("tag:body").text.lower()

        # Check progress bar markers
        if "guidelines" in body_text and "personal detail" not in body_text:
            return 1
        if "personal detail" in body_text:
            # Check if any personal detail fields are visible
            try:
                page.ele("@id:f_name", timeout=2)
                return 2
            except Exception:
                pass
        if "contact" in body_text:
            try:
                page.ele("@id:mobile_num", timeout=2)
                return 3
            except Exception:
                pass
        if "ao code" in body_text:
            try:
                page.ele("@id:area_code", timeout=2)
                return 4
            except Exception:
                pass
        if "document" in body_text:
            return 5
    except Exception:
        pass

    # Default: start from the beginning
    return 1


# ══════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Resume PAN application with token")
    parser.add_argument(
        "--config", "-c",
        default=DEFAULT_CONFIG,
        help=f"Path to JSON config file (default: {DEFAULT_CONFIG})"
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only login and extract DOM data, don't proceed with form filling"
    )
    parser.add_argument(
        "--auto-submit",
        action="store_true",
        help="Auto-submit the final form without manual confirmation"
    )
    args = parser.parse_args()

    # ── Load config ────────────────────────────────────────────
    cfg = load_config(args.config)
    resume_data    = cfg.get("resume", {})
    applicant_data = cfg.get("applicant", {})
    otp_port       = cfg.get("server", {}).get("otp_port", 5055)

    # ── Start OTP + data server in background ──────────────────
    t = threading.Thread(target=start_flask_server, args=(otp_port,), daemon=True)
    t.start()
    time.sleep(1)

    # ── Launch browser ─────────────────────────────────────────
    opts = ChromiumOptions()
    opts.set_argument("--disable-blink-features=AutomationControlled")
    opts.set_argument("--disable-gpu")

    is_linux = os.name != "nt"
    headless = _env_flag("PAN_HEADLESS", is_linux)
    if headless:
        opts.headless(True)

    if _env_flag("PAN_NO_SANDBOX", is_linux):
        opts.set_argument("--no-sandbox")

    if _env_flag("PAN_DISABLE_DEV_SHM", is_linux):
        opts.set_argument("--disable-dev-shm-usage")

    browser_path = _detect_browser_path()
    if browser_path:
        opts.set_browser_path(browser_path)
        log.info(f"[Browser] Using executable: {browser_path}")

    page = ChromiumPage(addr_or_opts=opts)
    if not headless:
        page.set.window.max()

    try:
        # ── R1: Navigate and click Resume tab ──────────────────
        step_r1_navigate(page)

        # ── R2: Fill token / email / DOB ───────────────────────
        step_r2_fill_resume_form(page, resume_data)

        # ── R3: Solve captcha and submit ───────────────────────
        step_r3_captcha_and_submit(page)

        # ── R4: Extract DOM data ───────────────────────────────
        extracted = step_r4_extract_data(page)

        log.info("=" * 55)
        log.info("  RESUME LOGIN SUCCESSFUL")
        log.info(f"  Page: {extracted.get('title', 'N/A')}")
        log.info(f"  Fields found: {len(extracted.get('fields', {}))}")
        log.info(f"  Data saved to: pan_extracted.json")
        log.info(f"  API endpoint: http://localhost:{otp_port}/extracted")
        log.info("=" * 55)

        if args.extract_only:
            log.info("--extract-only mode: stopping after extraction.")
            log.info("Review pan_extracted.json and update pan_config.json as needed.")
            input("\nPress ENTER to close browser…")
            return

        # ── R5: Fill wizard steps 2–5 ──────────────────────────
        steps = step_r5_continue_application(page, applicant_data, otp_port)

        log.info("=" * 55)
        log.info("  WIZARD STEPS COMPLETED")
        log.info(f"  Steps filled: {steps}")
        log.info("=" * 55)

        if "documents" in steps:
            if args.auto_submit:
                wizard_final_submit(page)
                log.info("  ✅  FORM SUBMITTED AUTOMATICALLY")
            else:
                log.info("  Review the form in the browser window.")
                user_input = input(
                    "\n  Type 'submit' to auto-submit, or press ENTER to keep browser open: "
                ).strip().lower()
                if user_input == "submit":
                    wizard_final_submit(page)
                    log.info("  ✅  FORM SUBMITTED")
                else:
                    log.info("  Form NOT submitted — complete manually in browser.")

        # ── Final extraction ───────────────────────────────────
        final_data = extract_page_data(page)
        save_extracted_data(final_data, "pan_final_state.json")

        log.info("=" * 55)
        log.info("  ⏩  NEXT STEPS:")
        log.info("  1. Complete PAYMENT if prompted (₹107 India / ₹1017 abroad)")
        log.info("  2. Complete Aadhaar e-KYC OTP when prompted")
        log.info("     POST OTP to: http://localhost:{}/otp".format(otp_port))
        log.info("  3. Complete e-Sign if prompted")
        log.info("=" * 55)

        input("\nPress ENTER to close browser…")

    except TimeoutError as e:
        log.error(f"Timed out: {e}")
    except Exception as e:
        log.exception(f"Fatal error: {e}")
    finally:
        page.quit()
        log.info("Browser closed.")


if __name__ == "__main__":
    main()

