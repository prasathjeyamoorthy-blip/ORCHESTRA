import os
import time
import json
import asyncio
import urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright


class TNeSevaiBackendAgent:
    def __init__(self, json_payload, ws_manager=None, loop=None):
        self.data = json_payload
        self.ws_manager = ws_manager
        self.loop = loop

        # Parse JSON into easily accessible variables
        self.creds = self.data.get("credentials", {})
        self.applicant = self.data.get("applicant_details", {})
        self.address = self.data.get("address_details", {})
        self.docs = self.data.get("documents", {})

    def log(self, message):
        """Prints status updates to the terminal for the backend agent to read."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [STATUS] {message}")

    def _ws_prompt(self, event_dict, timeout=300):
        """
        Send an event to the frontend via WebSocket and wait for the user's answer.
        Falls back to terminal input() if no ws_manager is connected (e.g. standalone run).
        
        Args:
            event_dict: dict with at minimum {"type": "...", "message": "..."}
            timeout: seconds to wait for user response before raising TimeoutError
        Returns:
            The string answer the user submitted from the UI.
        """
        if not self.ws_manager or not self.loop:
            # Fallback: running standalone without WebSocket
            return input(f"AGENT PROMPT -> {event_dict.get('message', 'Enter value')}: ")

        # Clear any stale previous response
        self.ws_manager.latest_response = None

        # Push the event to the React UI
        future = asyncio.run_coroutine_threadsafe(
            self.ws_manager.send_event(event_dict),
            self.loop
        )
        future.result(timeout=10)  # Wait up to 10s for the send to complete
        self.log(f"Sent WS event to UI: {event_dict.get('type')}")

        # Spin-poll until user responds or timeout
        elapsed = 0
        while elapsed < timeout:
            response = self.ws_manager.latest_response
            if response is not None:
                # Response from React: {"type": "USER_ANSWER", "data": "..."}
                data = response.get("data", "")
                if isinstance(data, dict):
                    # For multi-field responses, join values
                    return " ".join(str(v) for v in data.values())
                return str(data)
            time.sleep(1)
            elapsed += 1

        raise TimeoutError(f"No user response received within {timeout}s for event: {event_dict.get('type')}")

    def format_date_for_injection(self, date_str):
        try:
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%b-%Y"):
                try: return datetime.strptime(date_str, fmt).strftime("%d-%b-%Y")
                except ValueError: continue
            return date_str 
        except: return date_str

    PORTAL_URL = "https://www.tnesevai.tn.gov.in/"
    NAV_TIMEOUT = 90_000  # 90 seconds – government portals are slow
    MAX_GOTO_RETRIES = 3

    def _check_connectivity(self):
        """Quick pre-flight check before launching the browser."""
        try:
            urllib.request.urlopen(self.PORTAL_URL, timeout=15)
            return True
        except Exception:
            return False

    def _goto_with_retry(self, page, url):
        """Navigate with automatic retries on timeout/network errors."""
        for attempt in range(1, self.MAX_GOTO_RETRIES + 1):
            try:
                self.log(f"Navigating to {url} (attempt {attempt}/{self.MAX_GOTO_RETRIES})...")
                page.goto(url, timeout=self.NAV_TIMEOUT, wait_until="domcontentloaded")
                return  # success
            except Exception as e:
                self.log(f"Navigation attempt {attempt} failed: {e}")
                if attempt == self.MAX_GOTO_RETRIES:
                    raise RuntimeError(
                        f"Could not reach {url} after {self.MAX_GOTO_RETRIES} attempts. "
                        "Please check your internet connection or try again later."
                    ) from e
                time.sleep(5)  # brief pause before retry

    def run(self):
        try:
            # --- Pre-flight connectivity check ---
            self.log("Checking portal connectivity...")
            if not self._check_connectivity():
                msg = ("Cannot reach the TNeSevai portal. "
                       "Please verify your internet connection and try again.")
                self.log(f"CONNECTIVITY ERROR: {msg}")
                if self.ws_manager and self.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.ws_manager.send_event({"type": "CONNECTIVITY_ERROR", "message": msg}),
                        self.loop
                    ).result(timeout=10)
                return

            with sync_playwright() as playwright:
                self.log("Launching Browser...")
                browser = playwright.chromium.launch(headless=False, slow_mo=200)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()

                # --- Login ---
                self._goto_with_retry(page, self.PORTAL_URL)
                page.get_by_role("link", name="English Version").click()
                page.get_by_role("button", name="Citizen Login").click()
                
                self.log("Entering Credentials...")
                page.get_by_role("textbox", name="User Name").fill(self.creds.get("username"))
                page.get_by_role("textbox", name="Password").fill(self.creds.get("password"))

                # --- Captcha Handling (Agent Pause 1) ---
                self.log("Extracting Captcha...")
                captcha_img = page.locator("#captcha_image, img[src*='Captcha']").first
                captcha_path = os.path.join(os.path.dirname(__file__), "backend_captcha.png")
                captcha_img.screenshot(path=captcha_path)
                
                self.log(f"Captcha saved to {os.path.abspath(captcha_path)}")

                # Prompt user via WebSocket UI
                user_captcha = self._ws_prompt({
                    "type": "REQUEST_CAPTCHA",
                    "message": "Please look at the captcha image and enter the code shown below."
                })
                
                page.get_by_role("textbox", name="Enter Captcha Code").fill(user_captcha)

                with page.expect_navigation(timeout=60000):
                    self.log("Clicking Login...")
                    page.get_by_role("button", name="Login").click()

                # --- Nav to Certificate ---
                self.log("Navigating to Residence Certificate...")
                page.wait_for_load_state("networkidle")
                page.get_by_role("link", name="Revenue Department").click()
                page.get_by_role("link", name="2", exact=True).click()
                with page.expect_popup() as popup_info:
                    page.get_by_role("link", name="REV-116 Residence certificate").click()
                
                page_form = popup_info.value
                page_form.wait_for_load_state("domcontentloaded")
                time.sleep(4)
                page_form.get_by_role("button", name="Proceed").click()
                time.sleep(4)
                
                # --- CAN Search & Aadhaar ---
                self.log(f"Searching CAN: {self.applicant.get('can_number')}...")
                page_form.locator('[id="statusform:aadhar"]').fill(self.applicant.get("can_number")) 
                page_form.get_by_role("button", name="Search").click()
                time.sleep(8) 
                
                try: page_form.get_by_label("").check() 
                except: pass 
                
                self.log("Typing Aadhaar Number securely...")
                aadhar_input = page_form.locator('[id="statusform:citAadharNo"]')
                aadhar_input.click()
                
                try:
                    aadhar_input.press_sequentially(self.applicant.get("aadhar_number"), delay=150)
                except AttributeError:
                    aadhar_input.type(self.applicant.get("aadhar_number"), delay=150)
                
                aadhar_input.press("Tab")
                time.sleep(5)
                
                # --- DOB Injection ---
                self.log("Injecting Date of Birth...")
                fmt_dob = self.format_date_for_injection(self.applicant.get("dob"))
                page_form.evaluate(f"""
                    var dobField = document.getElementById('statusform:citAapDOBInputDate');
                    if (dobField) {{
                        dobField.value = '{fmt_dob}';
                        dobField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        dobField.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    }}
                """)
                time.sleep(4)
                
                # --- OTP Flow (Agent Pause 2) ---
                self.log("Requesting OTP from Server...")
                page_form.get_by_role("button", name="Generate OTP").click()
                time.sleep(3) 
                
                # Prompt user via WebSocket UI
                user_otp = self._ws_prompt({
                    "type": "REQUEST_OTP",
                    "message": "An OTP has been sent to your registered mobile number. Please enter the OTP below."
                })
                
                page_form.locator('[id="statusform:otp_id"]').fill(user_otp)
                page_form.get_by_role("button", name="Confirm OTP").click()
                
                self.log("OTP Confirmed. Proceeding to Form...")
                page_form.get_by_role("button", name="Proceed").click()
                page_form.wait_for_load_state("networkidle")
                time.sleep(5)

                # --- Fill Address Details ---
                self.log("Filling Address and Form Details...")
                if self.address.get("village"): page_form.locator('[id="residence:cRvillageListId"]').select_option(label=self.address.get("village"))
                if self.address.get("building_no"): page_form.locator('[id="residence:buildForList"]').fill(self.address.get("building_no"))
                if self.address.get("street_name"): page_form.locator('[id="residence:streetForList"]').fill(self.address.get("street_name"))
                if self.address.get("pincode"): page_form.locator('[id="residence:pinForList"]').fill(self.address.get("pincode"))

                fmt_from = self.format_date_for_injection(self.address.get("from_date"))
                page_form.evaluate(f"document.getElementById('residence:fromDateListInputDate').value = '{fmt_from}';")
                fmt_to = self.format_date_for_injection(self.address.get("to_date"))
                page_form.evaluate(f"document.getElementById('residence:toDateListInputDate').value = '{fmt_to}';")
                
                if self.applicant.get("ration_card_no"):
                    page_form.locator('[id="residence:rationCardId"]').fill(self.applicant.get("ration_card_no"))
                    time.sleep(4) 

                self.log("Submitting Details Table...")
                page_form.get_by_role("button", name="Add").click()
                time.sleep(5)

                # Dialog Handler
                def safe_dialog_handler(dialog):
                    try: dialog.accept()
                    except Exception: pass 
                page_form.on("dialog", safe_dialog_handler) 

                self.log("Submitting Form...")
                page_form.get_by_role("button", name="Submit").click()
                page_form.wait_for_load_state("networkidle")
                time.sleep(6) 

                # --- DOWNLOAD FORM ---
                self.log("Downloading Self Declaration Form...")
                try:
                    with page_form.expect_download(timeout=15000) as download_info:
                        page_form.get_by_role("link", name="Download Self declaration form").click(force=True)
                    download = download_info.value
                    save_path = os.path.join(os.getcwd(), "Self_Declaration_Form_For_User.pdf")
                    download.save_as(save_path)
                    self.log(f"Form saved locally at: {save_path}")
                except Exception as e:
                    self.log("Download skipped or failed. Proceeding.")

                # --- Document Upload Await (Agent Pause 3) ---
                self.log("Waiting for user to confirm documents are ready for upload...")

                # Notify the user via WebSocket UI to confirm upload
                self._ws_prompt({
                    "type": "REQUEST_RESUME",
                    "message": "The Self-Declaration Form has been downloaded. Please ensure your photo, signed declaration, and address proof are ready. Click Submit to continue with document upload."
                })

                # --- DOCUMENT UPLOADS ---
                def process_document_upload(doc_label, filepath, doc_no=None):
                    if not filepath or not os.path.exists(filepath):
                        self.log(f"WARNING: File not found at '{filepath}'. Skipping {doc_label}...")
                        return

                    self.log(f"Uploading {doc_label} from {filepath}...")
                    page_form.get_by_role("combobox").select_option(label=doc_label)
                    time.sleep(5)
                    
                    if doc_no:
                        doc_input = page_form.locator('[id="ss:dscnum"]')
                        doc_input.click()
                        doc_input.fill(doc_no)
                        doc_input.press("Tab") 
                        time.sleep(5)

                    page_form.locator("input[type='file']").last.set_input_files(filepath)
                    time.sleep(8) 

                    self.log(f"Clicking Upload for {doc_label}...")
                    page_form.get_by_text("Upload", exact=True).click(force=True)
                    time.sleep(10) 

                self.log("Commencing Document Processing...")
                process_document_upload("Photo", self.docs.get("photo_path"))
                process_document_upload("Self-Declaration of Applicant", self.docs.get("self_decl_path"))
                process_document_upload("Current Address Proof", self.docs.get("address_proof_path"), self.docs.get("address_doc_no"))

                # --- FINAL STEP ---
                self.log("All Documents Uploaded! Navigating to Payment...")
                try:
                    page_form.get_by_role('button', name='Make Payment').click(force=True)
                except:
                    page_form.locator('input[value="Make Payment"]').first.click(force=True)

                self.log("SUCCESS! Payment page reached. Backend job complete.")
                time.sleep(5) 
                browser.close()

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys
    import argparse

    # ── Default values (used as fallback / prefill for interactive mode) ──────
    _defaults = {
        "credentials": {
            "username":  "lohithg",
            "password":  "Lohith@2007"
        },
        "applicant_details": {
            "can_number":     "13318016498757",
            "aadhar_number":  "607126530111",
            "dob":            "23-Feb-2007",
            "ration_card_no": "333477513066"
        },
        "address_details": {
            "village":      "Gundu Uppalavadi",
            "building_no":  "55",
            "street_name":  "World vision street thazhungda",
            "pincode":      "607002",
            "from_date":    "26/07/2023",
            "to_date":      "01/03/2026"
        },
        "documents": {
            "photo_path":         "D:/Playwright/3rdAgent/REQPICS/LOHITHG.jpg",
            "self_decl_path":     "D:/Playwright/3rdAgent/REQPICS/SelfDeclarationForm_TN-1520260126407SIGNED (1).pdf",
            "address_proof_path": "D:/Playwright/3rdAgent/REQPICS/Screenshot 2026-01-26 200035.png",
            "address_doc_no":     "TN3120250006924"
        }
    }

    parser = argparse.ArgumentParser(description="Run TNeSevai automation standalone")
    parser.add_argument("--payload", metavar="FILE",
                        help="Path to a JSON file containing the full payload "
                             "(e.g. the one saved by the document extraction pipeline).")
    parser.add_argument("--interactive", action="store_true",
                        help="Prompt for each field interactively, pre-filled with defaults.")
    args = parser.parse_args()

    # ── Mode 1: Load from JSON file ───────────────────────────────────────────
    if args.payload:
        with open(args.payload, "r", encoding="utf-8") as f:
            payload = json.load(f)
        print(f"[INFO] Loaded payload from: {args.payload}")

    # ── Mode 2: Interactive prompt (pre-filled with defaults/extracted data) ──
    elif args.interactive:
        def _prompt(label, default):
            val = input(f"  {label} [{default}]: ").strip()
            return val if val else default

        print("\n── Credentials ──────────────────────────────────")
        username  = _prompt("TNeSevai Username", _defaults["credentials"]["username"])
        password  = _prompt("Password",          _defaults["credentials"]["password"])

        print("\n── Applicant Details ────────────────────────────")
        can       = _prompt("CAN Number",        _defaults["applicant_details"]["can_number"])
        aadhar    = _prompt("Aadhaar Number",     _defaults["applicant_details"]["aadhar_number"])
        dob       = _prompt("Date of Birth",      _defaults["applicant_details"]["dob"])
        ration    = _prompt("Ration Card No",     _defaults["applicant_details"]["ration_card_no"])

        print("\n── Address Details ──────────────────────────────")
        village   = _prompt("Village/Taluk",      _defaults["address_details"]["village"])
        bldg      = _prompt("Building No",        _defaults["address_details"]["building_no"])
        street    = _prompt("Street Name",        _defaults["address_details"]["street_name"])
        pincode   = _prompt("Pincode",            _defaults["address_details"]["pincode"])
        from_dt   = _prompt("Residing From (DD/MM/YYYY)", _defaults["address_details"]["from_date"])
        to_dt     = _prompt("Residing To   (DD/MM/YYYY)", _defaults["address_details"]["to_date"])

        print("\n── Document Paths ───────────────────────────────")
        photo     = _prompt("Photo path",         _defaults["documents"]["photo_path"])
        self_decl = _prompt("Self-Decl PDF path", _defaults["documents"]["self_decl_path"])
        addr_pf   = _prompt("Address Proof path", _defaults["documents"]["address_proof_path"])
        addr_no   = _prompt("Address Doc No",     _defaults["documents"]["address_doc_no"])
        print()

        payload = {
            "credentials":      {"username": username,  "password": password},
            "applicant_details":{"can_number": can, "aadhar_number": aadhar, "dob": dob, "ration_card_no": ration},
            "address_details":  {"village": village, "building_no": bldg, "street_name": street,
                                 "pincode": pincode, "from_date": from_dt, "to_date": to_dt},
            "documents":        {"photo_path": photo, "self_decl_path": self_decl,
                                 "address_proof_path": addr_pf, "address_doc_no": addr_no}
        }

    # ── Mode 3: Use hardcoded defaults (original behaviour) ──────────────────
    else:
        payload = _defaults

    # Run the agent (standalone mode — no WebSocket, uses input() fallback for CAPTCHA/OTP)
    bot = TNeSevaiBackendAgent(payload)
    bot.run()