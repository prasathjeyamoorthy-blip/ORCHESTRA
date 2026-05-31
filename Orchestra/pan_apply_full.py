"""
Protean PAN Card Application — Full Automation
=====================================================
- Automates ALL steps except payment
- Aadhaar OTP received via HTTP POST JSON from your backend
  → POST http://localhost:5055/otp  body: {"otp": "123456"}
  → GET  http://localhost:5055/status  (shows current step)

Install:
    pip install DrissionPage speechrecognition pydub requests flask
    sudo apt install ffmpeg   # or: brew install ffmpeg
"""

import json
import logging
import os
import re
import shutil
import tempfile
import threading
import time
from flask import Flask, request, jsonify
from DrissionPage import ChromiumPage, ChromiumOptions
from pydub import AudioSegment
import speech_recognition as sr
import requests as req

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("pan_bot")

# ══════════════════════════════════════════════════════════════
#  APPLICANT CONFIG
#  Fill everything here — the bot drives the full form
# ══════════════════════════════════════════════════════════════
APPLICANT = {
    # ── Page 1 – Contact info ─────────────────────────────────
    "application_type": "49A",        # 49A | 49AA | CORR
    "category":         "Individual",
    "title":            "Mr",         # Mr | Mrs | Ms | M/s
    "last_name":        "Sharma",
    "first_name":       "Rahul",
    "middle_name":      "",
    "dob":              "15/08/1995", # DD/MM/YYYY
    "email":            "rahul@example.com",
    "mobile":           "9876543210",

    # ── Page 2 – Personal details ─────────────────────────────
    "gender":           "M",          # M | F | T (Transgender)
    "marital_status":   "S",          # S=Single | M=Married
    "father_last":      "Sharma",
    "father_first":     "Suresh",
    "father_middle":    "",
    "mother_last":      "Sharma",     # optional — leave "" to skip
    "mother_first":     "Sunita",
    "mother_middle":    "",
    "name_on_card":     "RAHUL SHARMA", # abbreviated name to print on PAN

    # ── Page 3 – Address ─────────────────────────────────────
    "address_flat":     "A-101",
    "address_building": "Green Apartments",
    "address_street":   "MG Road",
    "address_area":     "Koramangala",
    "address_city":     "Bengaluru",
    "address_state":    "Karnataka",
    "address_pin":      "560034",
    "address_country":  "India",      # change for 49AA applicants

    # Source of income (checkboxes — can be multiple, comma-separated)
    "source_of_income": "Salary",     # Salary | Income from Business / Profession | Income from House property | Income from Other sources | Capital Gains | No income

    # Address for communication
    "address_for_comm": "Residence",  # Residence | Office | Representative Assessee (RA)

    # Aadhaar photo on PAN card
    "aadhaar_photo_consent": True,    # True = Yes (agree) | False = No (disagree)

    # Residential status
    "residential_status": "Resident", # Resident | Non-resident | Resident but not ordinarily resident

    # TIN and Passport (required for Non-resident / foreign applicants)
    "passport_number":  "",           # e.g. "A1234567" — leave blank for residents
    "tin_number":       "",           # Taxpayer Identification Number — leave blank if not applicable

    # Representative Assessee
    "representative_assessee": False, # True = Yes | False = No

    # ── Page 4 – AO Code (skip if using Aadhaar auto-fill) ───
    # Leave all blank to use Aadhaar-based auto-fill
    "ao_area_code":  "",  # e.g. "MUM"
    "ao_type":       "",  # e.g. "W"
    "ao_range_code": "",  # e.g. "101"
    "ao_number":     "",  # e.g. "1"

    # ── Page 5 – Document proofs (paperless Aadhaar mode) ────
    # Set paperless=True to use Aadhaar e-KYC (no uploads needed)
    "paperless":       True,
    "aadhaar_number": "1234 5678 9012",  # 12-digit Aadhaar

    # Physical upload mode (used only if paperless=False)
    "proof_identity":  "Aadhaar Card",
    "proof_address":   "Aadhaar Card",
    "proof_dob":       "Aadhaar Card",
}

URL = "https://onlineservices.proteantech.in/paam/endUserRegisterContact.html"
OTP_SERVER_PORT = 5055
CAPTCHA_MAX_ATTEMPTS = 5

# ── Dropdown maps ─────────────────────────────────────────────
APP_TYPE_MAP = {
    "49A":  "New PAN - Form no. 93 & 94 (Indian Citizen)",
    "49AA": "New PAN - Form no. 95 & 96 (Foreign Citizen)",
    "CORR": "Changes or Correction in existing PAN Data / Reprint of PAN Card (No changes in existing PAN Data)",
}
APP_TYPE_VALUE_MAP = {"49A": "49A", "49AA": "49AA", "CORR": "CR", "CR": "CR"}
CATEGORY_VALUE_MAP = {
    "INDIVIDUAL": "P",
    "ASSOCIATION OF PERSONS": "A",
    "BODY OF INDIVIDUALS": "B",
    "COMPANY": "C",
    "TRUST": "T",
    "LIMITED LIABILITY PARTNERSHIP": "E",
    "FIRM": "F",
    "GOVERNMENT": "G",
    "HINDU UNDIVIDED FAMILY": "H",
    "ARTIFICIAL JURIDICAL PERSON": "J",
    "LOCAL AUTHORITY": "L",
}
GENDER_MAP  = {"M": "Male", "F": "Female", "T": "Transgender"}
MARITAL_MAP = {"S": "Single", "M": "Married"}

# ══════════════════════════════════════════════════════════════
#  OTP SERVER  (Flask – runs in background thread)
# ══════════════════════════════════════════════════════════════
_otp_store = {"otp": None, "step": "idle"}
_otp_event = threading.Event()

app = Flask(__name__)

@app.route("/otp", methods=["POST"])
def receive_otp():
    data = request.get_json(force=True)
    if not data or "otp" not in data:
        return jsonify({"error": 'Send JSON body: {"otp": "123456"}'}), 400
    _otp_store["otp"] = str(data["otp"]).strip()
    _otp_event.set()
    log.info(f"[OTP Server] Received OTP: {_otp_store['otp']}")
    return jsonify({"status": "ok", "otp_received": _otp_store["otp"]}), 200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "current_step":  _otp_store["step"],
        "waiting_for_otp": not _otp_event.is_set(),
    }), 200

def start_otp_server():
    log.info(f"[OTP Server] Listening on http://0.0.0.0:{OTP_SERVER_PORT}")
    app.run(host="0.0.0.0", port=OTP_SERVER_PORT, debug=False, use_reloader=False)

def wait_for_otp(label: str, timeout: int = 300) -> str:
    """Block until OTP is POSTed, then return it."""
    _otp_store["step"] = label
    _otp_event.clear()
    log.info(f"[OTP] Waiting for OTP ({label}) — POST to http://localhost:{OTP_SERVER_PORT}/otp")
    received = _otp_event.wait(timeout=timeout)
    if not received:
        raise TimeoutError(f"OTP not received within {timeout} seconds for step: {label}")
    otp = _otp_store["otp"]
    _otp_store["otp"] = None
    return otp


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_tool_path(tool_name: str):
    found = shutil.which(tool_name)
    if found:
        return found

    if os.name != "nt":
        return None

    candidates = [
        os.path.join(os.getenv("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links", f"{tool_name}.exe"),
        os.path.join(os.getenv("ProgramFiles", ""), "ffmpeg", "bin", f"{tool_name}.exe"),
        os.path.join(os.getenv("ProgramFiles(x86)", ""), "ffmpeg", "bin", f"{tool_name}.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _configure_audio_tools():
    ffmpeg_path = _resolve_tool_path("ffmpeg")
    ffprobe_path = _resolve_tool_path("ffprobe")

    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
    if ffprobe_path:
        AudioSegment.ffprobe = ffprobe_path


def _detect_browser_path():
    env_path = os.getenv("PAN_BROWSER_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    candidates = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


# ══════════════════════════════════════════════════════════════
#  reCAPTCHA v2 AUDIO BYPASS
# ══════════════════════════════════════════════════════════════
def _frame_has_audio_controls(frame) -> bool:
    for locator in (
        "#recaptcha-audio-button",
        ".rc-audiochallenge-tdownload-link",
        "#audio-source",
        "#audio-response",
    ):
        try:
            frame.ele(locator, timeout=1)
            return True
        except Exception:
            continue
    return False


def _get_challenge_frame(page: ChromiumPage, retries: int = 10):
    selectors = [
        "//iframe[contains(@src,'recaptcha/enterprise/bframe')]",
        "//iframe[contains(@src,'recaptcha/api2/bframe')]",
        "//iframe[contains(@title,'challenge')]",
        "//iframe[contains(@src,'recaptcha')]",
    ]
    last_error = None

    for _ in range(retries):
        for selector in selectors:
            try:
                frame = page.get_frame(selector, timeout=1)
                if frame and _frame_has_audio_controls(frame):
                    return frame
            except Exception as exc:
                last_error = exc
        time.sleep(0.25)

    raise Exception(f"Challenge frame not available: {last_error}")


def _extract_audio_url(frame, timeout: int = 8):
    candidates = [
        (".rc-audiochallenge-tdownload-link", "href"),
        ("#audio-source", "src"),
        ("xpath://a[contains(@href,'recaptcha/enterprise/payload')]", "href"),
        ("xpath://a[contains(@href,'recaptcha/api2/payload')]", "href"),
    ]

    loops = max(1, int(timeout / 0.25))
    for _ in range(loops):
        for locator, attr_name in candidates:
            try:
                value = frame.ele(locator, timeout=1).attr(attr_name)
                if value:
                    return value
            except Exception:
                continue
        time.sleep(0.25)

    return None


def _reload_audio(frame):
    try:
        frame.ele("#recaptcha-reload-button", timeout=2).click()
        time.sleep(0.6)
    except Exception:
        pass


def _wait_for_manual_recaptcha(page: ChromiumPage, timeout: int = 180) -> bool:
    """Wait for user to solve checkbox manually without relying on stdin prompts."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            anchor = _get_anchor_frame(page, retries=2)
            if anchor.ele(".recaptcha-checkbox-checked", timeout=1):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _get_anchor_frame(page: ChromiumPage, retries: int = 15):
    selectors = [
        "//iframe[contains(@src,'recaptcha/enterprise/anchor')]",
        "//iframe[contains(@src,'recaptcha/api2/anchor')]",
        "//iframe[contains(@title,'reCAPTCHA')]",
        "//iframe[contains(@src,'recaptcha')]",
    ]
    last_error = None

    for _ in range(retries):
        for selector in selectors:
            try:
                frame = page.get_frame(selector, timeout=1)
                if frame:
                    try:
                        frame.ele("#recaptcha-anchor", timeout=1)
                        return frame
                    except Exception:
                        continue
            except Exception as exc:
                last_error = exc

        time.sleep(0.3)

    raise Exception(f"Anchor frame not available: {last_error}")


def solve_recaptcha(page: ChromiumPage) -> bool:
    _configure_audio_tools()

    try:
        anchor = _get_anchor_frame(page)
        anchor.ele("#recaptcha-anchor", timeout=10).click()
        time.sleep(1.5)
        if anchor.ele(".recaptcha-checkbox-checked", timeout=2):
            log.info("[CAPTCHA] Passed instantly.")
            return True

        for attempt in range(1, CAPTCHA_MAX_ATTEMPTS + 1):
            log.info(f"[CAPTCHA] Audio solve attempt {attempt}/{CAPTCHA_MAX_ATTEMPTS}")
            bframe = _get_challenge_frame(page)

            try:
                bframe.ele("#recaptcha-audio-button", timeout=2).click()
                time.sleep(0.6)
            except Exception:
                pass

            audio_url = _extract_audio_url(bframe, timeout=8)
            if not audio_url:
                log.warning("[CAPTCHA] Audio URL not found; reloading challenge.")
                _reload_audio(bframe)
                continue

            tmp_dir = tempfile.gettempdir()
            suffix = f"{int(time.time() * 1000)}_{attempt}"
            mp3 = os.path.join(tmp_dir, f"rc_{suffix}.mp3")
            wav = os.path.join(tmp_dir, f"rc_{suffix}.wav")

            try:
                response = req.get(audio_url, timeout=20)
                response.raise_for_status()
                with open(mp3, "wb") as f:
                    f.write(response.content)

                audio_segment = AudioSegment.from_mp3(mp3).set_channels(1).set_frame_rate(16000)
                audio_segment.export(wav, format="wav")

                rec = sr.Recognizer()
                with sr.AudioFile(wav) as src:
                    audio = rec.record(src)

                text = re.sub(r"[^a-z0-9 ]", "", rec.recognize_google(audio).lower()).strip()
                if not text:
                    log.warning("[CAPTCHA] Empty transcription; reloading challenge.")
                    _reload_audio(bframe)
                    continue

                log.info(f"[CAPTCHA] Recognized: '{text}'")

                answer_box = bframe.ele("#audio-response", timeout=5)
                try:
                    answer_box.clear()
                except Exception:
                    pass
                answer_box.input(text)

                time.sleep(0.4)
                bframe.ele("#recaptcha-verify-button", timeout=5).click()
                time.sleep(1.8)

                anchor = _get_anchor_frame(page, retries=6)
                if anchor.ele(".recaptcha-checkbox-checked", timeout=4):
                    log.info("[CAPTCHA] Solved!")
                    return True

                log.warning("[CAPTCHA] Answer rejected; requesting new audio.")
                _reload_audio(bframe)

            except Exception as exc:
                log.warning(f"[CAPTCHA] Attempt failed: {exc}")
                _reload_audio(bframe)

            finally:
                for path in (mp3, wav):
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass

        return False

    except Exception as e:
        log.error(f"[CAPTCHA] Exception: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def safe_select(page, selector, value, timeout=5):
    selectors = selector if isinstance(selector, (list, tuple)) else [selector]
    values = value if isinstance(value, (list, tuple)) else [value]
    last_error = None

    for sel in selectors:
        try:
            element = page.ele(sel, timeout=timeout)
            for val in values:
                try:
                    element.select(val)
                    time.sleep(0.3)
                    return True
                except Exception as e:
                    last_error = e
        except Exception as e:
            last_error = e

    if last_error and "disconnected" in str(last_error).lower():
        raise RuntimeError(f"Page disconnected while selecting {selectors}.")

    log.warning(f"select({selectors}, {values}): {last_error}")
    return False

def safe_input(page, selector, value, timeout=5, clear=True):
    selectors = selector if isinstance(selector, (list, tuple)) else [selector]
    last_error = None

    for sel in selectors:
        try:
            el = page.ele(sel, timeout=timeout)
            if clear:
                el.clear()
            el.input(value)
            time.sleep(0.2)
            return True
        except Exception as e:
            last_error = e

    if last_error and "disconnected" in str(last_error).lower():
        raise RuntimeError(f"Page disconnected while filling {selectors}.")

    log.warning(f"input({selectors}): {last_error}")
    return False

def click_next(page):
    """Click any Next / Proceed / Continue submit button."""
    for sel in [
        "tag:button@id:submitForm",
        "tag:button@value:Submit",
        "tag:button@text():Submit",
        "tag:input@value:Next",
        "tag:input@value:Proceed",
        "tag:button@text():Next",
        "tag:button@text():Continue",
        "tag:input@type:submit",
    ]:
        try:
            page.ele(sel, timeout=4).click()
            time.sleep(3)
            return True
        except Exception:
            pass
    log.warning("[Nav] No Next/Submit button found — check browser manually.")
    return False


# ══════════════════════════════════════════════════════════════
#  STEP 1 — Contact / Applicant Info + reCAPTCHA
# ══════════════════════════════════════════════════════════════
def step1_contact_form(page, d):
    log.info("=== Step 1: Contact Form ===")
    page.get(URL)
    log.info("[Step1] Page loaded.")

    try:
        page.ele("tag:a@id:newappl", timeout=8).click()
        time.sleep(0.4)
        log.info("[Step1] New Application tab selected.")
    except Exception:
        log.info("[Step1] New Application tab not clicked (already active or not required).")

    for locator in ["tag:select@id:type", "tag:select@name:requestType"]:
        try:
            page.ele(locator, timeout=15)
            break
        except Exception:
            continue

    app_type_key = d.get("application_type", "").upper()
    app_type_ok = safe_select(
        page,
        ["tag:select@id:type", "tag:select@name:requestType"],
        [
            APP_TYPE_VALUE_MAP.get(app_type_key, d.get("application_type")),
            APP_TYPE_MAP.get(app_type_key, d.get("application_type")),
        ],
        10,
    )
    log.info("[Step1] Application type selection attempted.")

    category_text = str(d.get("category", "")).strip()
    category_key = category_text.upper()
    category_ok = safe_select(
        page,
        ["tag:select@id:cat_applicant1", "tag:select@name:category"],
        [
            CATEGORY_VALUE_MAP.get(category_key, category_text),
            category_key,
            category_text,
        ],
    )
    log.info("[Step1] Category selection attempted.")

    last_name_ok = safe_input(page, ["tag:input@id:l_name_end", "tag:input@name:lastName"], d["last_name"])
    first_name_ok = True
    if category_key == "INDIVIDUAL":
        first_name_ok = safe_input(page, ["tag:input@id:f_name_end", "tag:input@name:firstName"], d["first_name"])
        if d["middle_name"]:
            safe_input(page, ["tag:input@id:m_name_end", "tag:input@name:middleName"], d["middle_name"])
    log.info("[Step1] Name fields fill attempted.")

    # DOB — text field or split dropdowns
    try:
        dob_ok = safe_input(page, ["tag:input@id:date_of_birth_reg", "tag:input@name:dateOfBirth"], d["dob"])
    except Exception:
        dd, mm, yyyy = d["dob"].split("/")
        safe_select(page, "tag:select@name:dobDay",   dd)
        safe_select(page, "tag:select@name:dobMonth", mm)
        safe_select(page, "tag:select@name:dobYear",  yyyy)
        dob_ok = True
    log.info("[Step1] DOB fill attempted.")

    email_ok = safe_input(page, ["tag:input@id:email_id2", "tag:input@name:emailId"], d["email"])
    mobile_ok = safe_input(page, ["tag:input@id:rvContactNo", "tag:input@name:rvContactNo", "tag:input@name:mobile"], d["mobile"])
    log.info("[Step1] Contact fields fill attempted.")

    required_ok = all([app_type_ok, category_ok, last_name_ok, first_name_ok, dob_ok, email_ok, mobile_ok])
    if not required_ok:
        raise RuntimeError("Step 1 required fields were not fully filled. Check selectors/page state.")

    # Consent checkbox
    try:
        cb = page.ele("tag:input@id:consent", timeout=3)
        if not cb.attr("checked"):
            cb.click()
    except Exception:
        pass

    log.info("[Step1] Consent handling attempted.")

    log.info("[Step1] Starting reCAPTCHA solve.")
    solved = solve_recaptcha(page)
    if not solved:
        if _env_flag("PAN_HEADLESS", os.name != "nt"):
            raise RuntimeError(
                "reCAPTCHA solve failed in headless mode. "
                "Retry with PAN_HEADLESS=0 (GUI/Xvfb) or solve manually."
            )

        log.warning("reCAPTCHA unsolved — waiting up to 180s for manual checkbox solve.")
        if not _wait_for_manual_recaptcha(page, timeout=180):
            raise RuntimeError("Manual reCAPTCHA solve not detected within timeout.")

    if not click_next(page):
        raise RuntimeError("Step 1 submit failed: submit/next button not found.")

    log.info("Step 1 done.")


# ══════════════════════════════════════════════════════════════
#  STEP 2 — Token page → Continue
# ══════════════════════════════════════════════════════════════
def step2_get_token(page, applicant_data=None) -> str:
    log.info("=== Step 2: Token ===")
    token = ""
    try:
        el = page.ele(
            "xpath://*[contains(text(),'Token') or contains(@class,'token') or contains(@id,'token')]",
            timeout=8)
        m = re.search(r"\d{10,}", el.text or "")
        token = m.group() if m else el.text.strip()
        log.info(f"Token: {token}")
        with open("pan_token.txt", "w") as f:
            f.write(token)
    except Exception:
        log.warning("Token element not found.")

    # Save resume session data for later use by pan_resume.py
    if token:
        session = {
            "token": token,
            "email": (applicant_data or {}).get("email", ""),
            "dob":   (applicant_data or {}).get("dob", ""),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            with open("pan_session.json", "w") as f:
                json.dump(session, f, indent=2)
            log.info("Session saved to pan_session.json for resume.")
        except Exception as e:
            log.warning(f"Could not save session: {e}")

    # Click "Continue with PAN Application Form"
    for txt in ["Continue with PAN Application Form", "Continue"]:
        try:
            page.ele(f"xpath://input[contains(@value,'{txt}')] | //button[contains(text(),'{txt}')]",
                     timeout=6).click()
            time.sleep(3)
            break
        except Exception:
            pass
    return token


# ══════════════════════════════════════════════════════════════
#  STEP 3 — Personal Details
# ══════════════════════════════════════════════════════════════
def step3_personal_details(page, d):
    log.info("=== Step 3: Personal Details ===")

    # ── Select submission mode ────────────────────────────────
    # First option = Aadhaar-based Online PAN Application (eKYC)
    # This must be selected before filling other fields
    if d.get("paperless", True):
        for sel in [
            "xpath://input[@type='radio' and (@value='E' or contains(@value,'aadhaar') or contains(@value,'Aadhaar') or contains(@value,'ekyc') or contains(@value,'EKYC'))]",
            "xpath://input[@type='radio'][1]",  # fallback: first radio on the page
        ]:
            try:
                radio = page.ele(sel, timeout=4)
                if radio and not radio.attr("checked"):
                    radio.click()
                    time.sleep(0.5)
                    log.info("[Step3] Aadhaar-based submission mode selected.")
                break
            except Exception:
                continue

        # Delivery mode: Physical copy + soft copy (first option)
        for sel in [
            "xpath://input[@type='radio' and (contains(@value,'physical') or contains(@value,'Physical') or contains(@value,'both') or contains(@value,'P'))]",
            "xpath://fieldset//input[@type='radio'][1]",
        ]:
            try:
                radio = page.ele(sel, timeout=3)
                if radio and not radio.attr("checked"):
                    radio.click()
                    time.sleep(0.3)
                    log.info("[Step3] Physical + soft copy delivery selected.")
                break
            except Exception:
                continue

    # Gender
    safe_select(page, "tag:select@name:gender", GENDER_MAP.get(d["gender"], d["gender"]))
    safe_select(page, "tag:select@name:maritalStatus", MARITAL_MAP.get(d["marital_status"], d["marital_status"]))

    # Father's name
    safe_input(page, "tag:input@name:fatherLastName",   d["father_last"])
    safe_input(page, "tag:input@name:fatherFirstName",  d["father_first"])
    if d["father_middle"]:
        safe_input(page, "tag:input@name:fatherMiddleName", d["father_middle"])

    # Mother's name (optional)
    if d.get("mother_last"):
        safe_input(page, "tag:input@name:motherLastName",  d["mother_last"])
        safe_input(page, "tag:input@name:motherFirstName", d["mother_first"])

    # Name to print on PAN card
    if d.get("name_on_card"):
        safe_input(page, "tag:input@name:nameOnCard", d["name_on_card"])

    # ── Aadhaar photo consent dropdown ───────────────────────────
    consent = d.get("aadhaar_photo_consent", True)
    consent_val = "Y" if consent else "N"
    for sel in [
        "tag:select@name:aadhaarPhotoConsent",
        "xpath://select[contains(@name,'photo') or contains(@name,'Photo') or contains(@name,'consent') or contains(@name,'Consent')]",
    ]:
        try:
            page.ele(sel, timeout=3).select(consent_val)
            log.info(f"[Step3] Aadhaar photo consent set to: {'Yes' if consent else 'No'}")
            break
        except Exception:
            continue

    if not click_next(page):
        raise RuntimeError("Step 3 could not proceed to next page.")
    log.info("Step 3 done.")


# ══════════════════════════════════════════════════════════════
#  STEP 4 — Contact & Address Details
# ══════════════════════════════════════════════════════════════
def step4_address(page, d):
    log.info("=== Step 4: Address & Contact Details ===")

    # ── Source of income checkboxes (multiple allowed) ────────────
    soi_map = {
        "Salary":                              "salary",
        "Income from Business / Profession":   "business",
        "Income from House property":          "house",
        "Income from Other sources":           "other",
        "Capital Gains":                       "capital",
        "No income":                           "noincome",
    }
    selected_soi = d.get("source_of_income", "")
    for label, val in soi_map.items():
        if label.lower() in selected_soi.lower():
            for sel in [
                f"xpath://input[@type='checkbox' and contains(@value,'{val}')]",
                f"xpath://label[contains(text(),'{label}')]/preceding-sibling::input[@type='checkbox']",
                f"xpath://label[contains(text(),'{label}')]/..//input[@type='checkbox']",
            ]:
                try:
                    cb = page.ele(sel, timeout=2)
                    if cb and not cb.attr("checked"):
                        cb.click()
                        time.sleep(0.2)
                    break
                except Exception:
                    continue

    # ── Address for communication radio ──────────────────────────
    addr_comm = d.get("address_for_comm", "Residence")
    addr_val_map = {
        "Residence":                    ["R", "residence", "Residence"],
        "Office":                       ["O", "office", "Office"],
        "Representative Assessee (RA)": ["RA", "representative", "Representative"],
    }
    for val in addr_val_map.get(addr_comm, ["R"]):
        for sel in [
            f"xpath://input[@type='radio' and @value='{val}']",
            f"xpath://label[contains(text(),'{addr_comm}')]/preceding-sibling::input[@type='radio']",
            f"xpath://label[contains(text(),'{val}')]/..//input[@type='radio']",
        ]:
            try:
                radio = page.ele(sel, timeout=2)
                if radio and not radio.attr("checked"):
                    radio.click()
                    time.sleep(0.3)
                    log.info(f"[Step4] Address for communication set to: {addr_comm}")
                break
            except Exception:
                continue

    # ── Residential Status radio ──────────────────────────────────
    res_map = {
        "Resident":                              "R",
        "Non-resident":                          "N",
        "Resident but not ordinarily resident":  "O",
    }
    res_val = res_map.get(d.get("residential_status", "Resident"), "R")
    for sel in [
        f"xpath://input[@type='radio' and @value='{res_val}']",
        f"xpath://label[contains(text(),\"{d.get('residential_status','Resident')}\")]/..//input[@type='radio']",
    ]:
        try:
            radio = page.ele(sel, timeout=3)
            if radio and not radio.attr("checked"):
                radio.click(); time.sleep(0.3)
                log.info(f"[Step4] Residential status: {d.get('residential_status')}")
            break
        except Exception:
            continue

    # ── TIN and Passport ──────────────────────────────────────────
    if d.get("passport_number"):
        safe_input(page, [
            "tag:input@name:passportNumber",
            "tag:input@id:passportNumber",
            "xpath://input[contains(@name,'passport') or contains(@id,'passport')]",
        ], d["passport_number"])

    if d.get("tin_number"):
        safe_input(page, [
            "tag:input@name:tinNumber",
            "tag:input@name:taxpayerIdNumber",
            "xpath://input[contains(@name,'tin') or contains(@name,'TIN') or contains(@name,'taxpayer')]",
        ], d["tin_number"])

    # ── Representative Assessee ───────────────────────────────────
    ra = d.get("representative_assessee", False)
    ra_val = "Y" if ra else "N"
    for sel in [
        f"xpath://input[@type='radio' and @value='{ra_val}' and (contains(@name,'representative') or contains(@name,'Representative'))]",
        f"xpath://label[text()=\"{'Yes' if ra else 'No'}\"]/..//input[@type='radio']",
    ]:
        try:
            radio = page.ele(sel, timeout=3)
            if radio and not radio.attr("checked"):
                radio.click(); time.sleep(0.3)
                log.info(f"[Step4] Representative Assessee: {'Yes' if ra else 'No'}")
            break
        except Exception:
            continue

    safe_input(page, "tag:input@name:flatDoorBldgNo",    d["address_flat"])
    safe_input(page, "tag:input@name:nameBldgVillage",   d["address_building"])
    safe_input(page, "tag:input@name:roadStreet",        d["address_street"])
    safe_input(page, "tag:input@name:areaLocality",      d["address_area"])
    safe_input(page, "tag:input@name:townCityDistrict",  d["address_city"])
    safe_select(page, "tag:select@name:state",           d["address_state"])
    safe_input(page, "tag:input@name:pinCode",           d["address_pin"])
    safe_select(page, "tag:select@name:country",         d["address_country"])

    if not click_next(page):
        raise RuntimeError("Step 4 could not proceed to next page.")
    log.info("Step 4 done.")


# ══════════════════════════════════════════════════════════════
#  STEP 5 — AO Code
# ══════════════════════════════════════════════════════════════
def step5_ao_code(page, d):
    log.info("=== Step 5: AO Code ===")
    if d["ao_area_code"]:
        safe_input(page, "tag:input@name:areaCode",  d["ao_area_code"])
        safe_select(page, "tag:select@name:aoType",  d["ao_type"])
        safe_input(page, "tag:input@name:rangeCode", d["ao_range_code"])
        safe_input(page, "tag:input@name:aoNumber",  d["ao_number"])
    else:
        # Try "Continue" without filling — Aadhaar may auto-populate
        log.info("AO code not provided — skipping (will be auto-filled via Aadhaar).")

    if not click_next(page):
        raise RuntimeError("Step 5 could not proceed to next page.")
    log.info("Step 5 done.")


# ══════════════════════════════════════════════════════════════
#  STEP 6 — Document / Proof Selection
# ══════════════════════════════════════════════════════════════
def step6_documents(page, d):
    log.info("=== Step 6: Document Proofs ===")

    if d["paperless"]:
        # Select Aadhaar e-KYC / paperless mode radio button
        for sel in [
            "xpath://input[@type='radio' and (@value='E' or @value='e' or contains(@value,'aadhaar') or contains(@value,'Aadhaar') or contains(@value,'ekyc') or contains(@value,'paperless'))]",
            "xpath://input[@type='radio'][1]",
        ]:
            try:
                radio = page.ele(sel, timeout=4)
                if radio and not radio.attr("checked"):
                    radio.click()
                    time.sleep(0.5)
                    log.info("[Step6] Aadhaar e-KYC mode selected.")
                break
            except Exception:
                continue

        # Enter Aadhaar number
        aadhaar = d["aadhaar_number"].replace(" ", "").replace("-", "")
        safe_input(page, [
            "tag:input@name:aadhaarNumber",
            "tag:input@id:aadhaarNumber",
            "tag:input@placeholder:Aadhaar",
        ], aadhaar)
    else:
        safe_select(page, "tag:select@name:proofOfIdentity", d["proof_identity"])
        safe_select(page, "tag:select@name:proofOfAddress",  d["proof_address"])
        safe_select(page, "tag:select@name:proofOfDob",      d["proof_dob"])

    if not click_next(page):
        raise RuntimeError("Step 6 could not proceed to next page.")
    log.info("Step 6 done.")


# ══════════════════════════════════════════════════════════════
#  STEP 7 — Declaration / Review & Submit
# ══════════════════════════════════════════════════════════════
def step7_declaration(page):
    log.info("=== Step 7: Declaration ===")
    # Tick declaration checkbox if present
    try:
        cb = page.ele(
            "xpath://input[@type='checkbox' and contains(@name,'declar')]",
            timeout=5)
        if not cb.attr("checked"):
            cb.click()
        time.sleep(0.4)
    except Exception:
        pass

    if not click_next(page):
        raise RuntimeError("Step 7 could not proceed to next page.")
    log.info("Step 7 done.")


# ══════════════════════════════════════════════════════════════
#  STEP 8 — Aadhaar e-KYC OTP  (received via POST /otp)
# ══════════════════════════════════════════════════════════════
def step8_aadhaar_otp(page):
    log.info("=== Step 8: Aadhaar e-KYC OTP ===")

    # 1) Trigger OTP send (click "Send OTP" button)
    for label in ["Send OTP", "Generate OTP", "Get OTP"]:
        try:
            page.ele(f"xpath://button[contains(text(),'{label}')] | //input[contains(@value,'{label}')]",
                     timeout=5).click()
            time.sleep(2)
            log.info(f"Clicked '{label}' button.")
            break
        except Exception:
            pass

    # 2) Wait for OTP from your backend
    otp = wait_for_otp("aadhaar_kyc_otp", timeout=300)

    # 3) Enter OTP
    safe_input(page, "tag:input@name:otpValue", otp)
    time.sleep(0.5)

    # 4) Submit OTP
    for label in ["Submit OTP", "Validate OTP", "Verify OTP"]:
        try:
            page.ele(f"xpath://button[contains(text(),'{label}')] | //input[contains(@value,'{label}')]",
                     timeout=5).click()
            time.sleep(3)
            log.info("OTP submitted.")
            return
        except Exception:
            pass

    click_next(page)
    log.info("Step 8 done.")


# ══════════════════════════════════════════════════════════════
#  STEP 9 — e-Sign OTP (second Aadhaar OTP for digital signature)
# ══════════════════════════════════════════════════════════════
def step9_esign_otp(page):
    log.info("=== Step 9: e-Sign OTP ===")

    for label in ["Send OTP", "Generate OTP"]:
        try:
            page.ele(f"xpath://button[contains(text(),'{label}')] | //input[contains(@value,'{label}')]",
                     timeout=5).click()
            time.sleep(2)
            break
        except Exception:
            pass

    otp = wait_for_otp("esign_otp", timeout=300)
    safe_input(page, "tag:input@name:otpValue", otp)
    time.sleep(0.5)
    if not click_next(page):
        raise RuntimeError("Step 9 could not proceed to next page.")
    log.info("Step 9 done.")


# ══════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════
def main():
    # Start OTP server in background
    t = threading.Thread(target=start_otp_server, daemon=True)
    t.start()
    time.sleep(1)

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
        step1_contact_form(page, APPLICANT)
        token = step2_get_token(page, APPLICANT)
        step3_personal_details(page, APPLICANT)
        step4_address(page, APPLICANT)
        step5_ao_code(page, APPLICANT)
        step6_documents(page, APPLICANT)
        step7_declaration(page)
        step8_aadhaar_otp(page)         # waits for POST /otp
        step9_esign_otp(page)           # waits for POST /otp (second OTP)

        log.info("=" * 55)
        log.info("  ALL AUTOMATED STEPS COMPLETE")
        log.info(f"  Token: {token}")
        log.info("  ⏩  NEXT: Complete PAYMENT manually in the browser")
        log.info("  Payment amount: ₹107 (India) / ₹1017 (abroad)")
        log.info("=" * 55)

        input("\nPress ENTER after completing payment to close browser…")

    except TimeoutError as e:
        log.error(f"Timed out: {e}")
    except Exception as e:
        log.exception(f"Fatal error: {e}")
    finally:
        page.quit()
        log.info("Browser closed.")


if __name__ == "__main__":
    main()
