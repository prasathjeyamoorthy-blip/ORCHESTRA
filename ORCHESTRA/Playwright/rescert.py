import os
import time
import json
import asyncio
import urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright  # type: ignore


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

    def _ws_prompt(self, event_dict, timeout=3000):
        if not self.ws_manager or not self.loop:
            return input(f"AGENT PROMPT -> {event_dict.get('message', 'Enter value')}: ")

        self.ws_manager.latest_response = None
        future = asyncio.run_coroutine_threadsafe(
            self.ws_manager.send_event(event_dict),
            self.loop
        )
        future.result(timeout=10) 
        self.log(f"Sent WS event to UI: {event_dict.get('type')}")

        elapsed = 0
        while elapsed < timeout:
            response = self.ws_manager.latest_response
            if response is not None:
                data = response.get("data", "")
                if isinstance(data, dict):
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

    def safe_select_dropdown(self, page, selector, value, field_name):
        if not value: return False
        try:
            dropdown = page.locator(selector)
            dropdown.wait_for(state="visible", timeout=5000)
            time.sleep(0.5)
            
            try:
                dropdown.select_option(label=value)
                self.log(f"✓ Selected {field_name}: {value}")
                return True
            except: pass
            
            try:
                options = dropdown.locator('option').all_text_contents()
                for option in options:
                    if option.strip().upper() == "SELECT": continue
                    if value.lower() in option.lower() or option.lower() in value.lower():
                        dropdown.select_option(label=option)
                        self.log(f"✓ Selected {field_name}: {option} (matched with {value})")
                        return True
            except: pass
            
            try:
                dropdown.select_option(value=value)
                self.log(f"✓ Selected {field_name} by value: {value}")
                return True
            except: pass
            
            try:
                options = dropdown.locator('option').all()
                for option in options:
                    option_text = option.text_content().strip()
                    if option_text.upper() != "SELECT" and option_text:
                        option_value = option.get_attribute('value')
                        if option_value:
                            dropdown.select_option(value=option_value)
                            self.log(f"✓ Selected {field_name}: {option_text} (first available option)")
                            return True
            except: pass
            
            self.log(f"✗ WARNING: Could not select {field_name} with value '{value}'")
            return False
        except Exception as e:
            self.log(f"✗ ERROR selecting {field_name}: {str(e)}")
            return False

    PORTAL_URL = "https://www.tnesevai.tn.gov.in/"
    NAV_TIMEOUT = 90_000
    MAX_GOTO_RETRIES = 3

    def _check_connectivity(self, max_retries=None, retry_delay=5):
        attempt = 0
        while True:
            attempt += 1
            try:
                self.log(f"Checking portal connectivity (attempt {attempt})...")
                urllib.request.urlopen(self.PORTAL_URL, timeout=15)
                self.log("✓ Portal is reachable!")
                return True
            except Exception as e:
                if max_retries and attempt >= max_retries:
                    self.log(f"✗ Failed to reach portal after {attempt} attempts")
                    return False
                self.log(f"✗ Cannot reach portal. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

    def _goto_with_retry(self, page, url):
        for attempt in range(1, self.MAX_GOTO_RETRIES + 1):
            try:
                self.log(f"Navigating to {url} (attempt {attempt}/{self.MAX_GOTO_RETRIES})...")
                page.goto(url, timeout=self.NAV_TIMEOUT, wait_until="domcontentloaded")
                return 
            except Exception as e:
                self.log(f"Navigation attempt {attempt} failed: {e}")
                if attempt == self.MAX_GOTO_RETRIES:
                    raise RuntimeError(f"Could not reach {url} after {self.MAX_GOTO_RETRIES} attempts.") from e
                time.sleep(5)

    def run(self):
        import threading
        thread = threading.Thread(target=self._run_playwright)
        thread.start()
        thread.join()
    
    def _run_playwright(self):
        try:
            self.log("Checking portal connectivity...")
            self._check_connectivity(max_retries=None, retry_delay=5)

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

                # --- Captcha Handling ---
                self.log("Extracting Captcha...")
                captcha_img = page.locator("#captcha_image, img[src*='Captcha']").first
                captcha_path = os.path.join(os.path.dirname(__file__), "backend_captcha.png")
                captcha_img.screenshot(path=captcha_path)
                
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
                
                try: aadhar_input.press_sequentially(self.applicant.get("aadhar_number"), delay=150)
                except AttributeError: aadhar_input.type(self.applicant.get("aadhar_number"), delay=150)
                
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
                
                # --- OTP Flow ---
                self.log("Requesting OTP from Server...")
                page_form.get_by_role("button", name="Generate OTP").click()
                time.sleep(3) 
                
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

                # --- Fill Form Details ---
                self.log("Filling Form Details...")
                page_form.wait_for_selector('[id="residence:cRvillageListId"]', timeout=10000)
                
                def is_field_empty(locator_str):
                    try:
                        element = page_form.locator(locator_str)
                        if element.count() == 0: return True
                        value = element.input_value() if element.count() > 0 else ""
                        return not value or value.strip() == ""
                    except: return True

                def is_dropdown_empty(locator_str):
                    try:
                        element = page_form.locator(locator_str)
                        if element.count() == 0: return True
                        value = element.input_value() if element.count() > 0 else ""
                        return not value or value.strip() == "" or value.strip().upper() == "SELECT"
                    except: return True

                if self.applicant.get("name") and is_field_empty('[id="residence:applicantName"]'):
                    try: page_form.locator('[id="residence:applicantName"]').fill(self.applicant.get("name"))
                    except: pass
                if self.applicant.get("father_name") and is_field_empty('[id="residence:fatherName"]'):
                    try: page_form.locator('[id="residence:fatherName"]').fill(self.applicant.get("father_name"))
                    except: pass

                if self.applicant.get("gender") and is_dropdown_empty('[id="residence:gender"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:gender"]', self.applicant.get("gender"), "Gender")
                if self.applicant.get("religion") and is_dropdown_empty('[id="residence:religion"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:religion"]', self.applicant.get("religion"), "Religion")
                if self.applicant.get("community") and is_dropdown_empty('[id="residence:community"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:community"]', self.applicant.get("community"), "Community")
                if self.address.get("state") and is_dropdown_empty('[id="residence:state"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:state"]', self.address.get("state"), "State")
                if self.address.get("district") and is_dropdown_empty('[id="residence:district"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:district"]', self.address.get("district"), "District")
                
                revenue_village_value = self.address.get("area") or self.address.get("village")
                if is_dropdown_empty('[id="residence:cRvillageListId"]'):
                    if revenue_village_value:
                        success = self.safe_select_dropdown(page_form, '[id="residence:cRvillageListId"]', revenue_village_value, "Revenue Village")
                        if not success:
                            try:
                                dropdown = page_form.locator('[id="residence:cRvillageListId"]')
                                options = dropdown.locator('option').all()
                                for option in options:
                                    if option.text_content().strip().upper() != "SELECT":
                                        dropdown.select_option(value=option.get_attribute('value'))
                                        break
                            except: pass

                if self.address.get("building_no") and is_field_empty('[id="residence:buildForList"]'):
                    page_form.locator('[id="residence:buildForList"]').fill(self.address.get("building_no"))
                if self.address.get("street_name") and is_field_empty('[id="residence:streetForList"]'):
                    page_form.locator('[id="residence:streetForList"]').fill(self.address.get("street_name"))
                if self.address.get("pincode") and is_field_empty('[id="residence:pinForList"]'):
                    page_form.locator('[id="residence:pinForList"]').fill(self.address.get("pincode"))

                if self.address.get("from_date") and is_field_empty('[id="residence:fromDateListInputDate"]'):
                    fmt_from = self.format_date_for_injection(self.address.get("from_date"))
                    page_form.evaluate(f"document.getElementById('residence:fromDateListInputDate').value = '{fmt_from}';")
                if self.address.get("to_date") and is_field_empty('[id="residence:toDateListInputDate"]'):
                    fmt_to = self.format_date_for_injection(self.address.get("to_date"))
                    page_form.evaluate(f"document.getElementById('residence:toDateListInputDate').value = '{fmt_to}';")
                
                if self.applicant.get("ration_card_no") and is_field_empty('[id="residence:rationCardId"]'):
                    page_form.locator('[id="residence:rationCardId"]').fill(self.applicant.get("ration_card_no"))
                    time.sleep(2) 

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

                # --- DOCUMENT UPLOAD HELPER ---
                def process_document_upload(doc_label, filepath, doc_no=None):
                    if not filepath or not os.path.exists(filepath):
                        self.log(f"WARNING: File not found at {filepath}. Skipping {doc_label}...")
                        return

                    self.log(f"Uploading {doc_label} from {filepath}...")

                    # 1. Select document type from dropdown
                    page_form.get_by_role("combobox").select_option(label=doc_label)
                    time.sleep(5)
                    
                    # 2. Fill document number BEFORE file upload (if needed)
                    if doc_no:
                        doc_input = page_form.locator('[id="ss:dscnum"]')
                        doc_input.click()
                        doc_input.fill(doc_no)
                        doc_input.press("Tab")
                        time.sleep(5)

                    # 3. Use set_input_files() to attach file WITHOUT opening file explorer
                    page_form.locator("input[type='file']").last.set_input_files(filepath)
                    time.sleep(8)

                    # 4. Click "Upload" button (NOT "Add..." which opens file explorer)
                    self.log(f"Clicking Upload for {doc_label}...")
                    page_form.get_by_text("Upload", exact=True).click(force=True)
                    time.sleep(10)

                # =============================================
                # STEP 1: UPLOAD PHOTO FIRST
                # =============================================
                self.log("Commencing Document Processing...")
                self.log("Step 1/3: Uploading Photo...")
                process_document_upload("Photo", self.docs.get("photo_path"))

                # =============================================
                # STEP 2: DOWNLOAD SELF DECLARATION → USER SIGNS → UPLOAD
                # =============================================
                self.log("Step 2/3: Downloading Self Declaration Form...")
                self_decl_save_name = "Self_Declaration_Form_To_Sign.pdf"
                self_decl_save_path = os.path.join(os.path.dirname(__file__), self_decl_save_name)
                
                try:
                    with page_form.expect_download(timeout=15000) as download_info:
                        page_form.get_by_role("link", name="Download Self declaration form").click(force=True)
                    download = download_info.value
                    download.save_as(self_decl_save_path)
                    self.log(f"Self Declaration Form saved at: {self_decl_save_path}")
                except Exception as e:
                    self.log(f"Download failed: {e}. Proceeding.")

                # Send event to frontend to show SelfDeclarationModal
                self.log("Sending Self Declaration to user for signing...")
                signed_decl_response = self._ws_prompt({
                    "type": "REQUEST_SIGNED_DECLARATION",
                    "message": "Please download the Self Declaration form, sign it, and upload the signed version.",
                    "download_path": self_decl_save_path
                })

                # The response contains the file path where the signed declaration was saved
                signed_decl_path = signed_decl_response.strip() if signed_decl_response else ""
                
                if signed_decl_path and signed_decl_path != "exit" and os.path.exists(signed_decl_path):
                    self.log(f"Received signed Self Declaration: {signed_decl_path}")
                    process_document_upload("Self-Declaration of Applicant", signed_decl_path)
                else:
                    self.log(f"WARNING: Signed Self Declaration not found at '{signed_decl_path}'. Skipping...")

                # =============================================
                # STEP 3: UPLOAD ADDRESS PROOF WITH DOC NUMBER
                # =============================================
                self.log("Step 3/3: Uploading Current Address Proof...")
                process_document_upload(
                    "Current Address Proof",
                    self.docs.get("address_proof_path"),
                    self.docs.get("address_doc_no")
                )

                # --- FINAL STEP ---
                self.log("All Documents Uploaded! Navigating to Payment...")
                time.sleep(3)
                
                button_clicked = False
                for button_name in ["Proceed", "Submit", "Make Payment", "Continue"]:
                    try:
                        page_form.get_by_role("button", name=button_name).click(force=True)
                        self.log(f"Clicked '{button_name}' button")
                        button_clicked = True
                        break
                    except: continue
                
                if not button_clicked:
                    for button_value in ["Proceed", "Submit", "Make Payment"]:
                        try:
                            page_form.locator(f'input[value="{button_value}"]').first.click(force=True)
                            self.log(f"Clicked '{button_value}' button")
                            button_clicked = True
                            break
                        except: continue

                self.log("SUCCESS! Payment page reached. Backend job complete.")
                time.sleep(5) 
                browser.close()

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")

if __name__ == "__main__":
    import argparse
    _defaults = {
        "credentials": {
            "username": "lohithg",
            "password": "Lohith@2007"
        },
        "applicant_details": {
            "can_number": "13318016498757",
            "aadhar_number": "607126530111",
            "dob": "23-Feb-2007",
            "ration_card_no": "333477513066"
        },
        "address_details": {
            "village": "Gundu Uppalavadi",
            "building_no": "55",
            "street_name": "World vision street thazhungda",
            "pincode": "607002",
            "from_date": "26/07/2023",
            "to_date": "01/03/2026"
        },
        "documents": {
            "photo_path": "D:/Playwright/3rdAgent/REQPICS/LOHITHG.jpg",
            "self_decl_path": "D:/Playwright/3rdAgent/REQPICS/SelfDeclarationForm_TN-1520260126407SIGNED (1).pdf",
            "aadhaar_path": "D:/Playwright/3rdAgent/REQPICS/in.gov.uidai-ADHAR.pdf",
            "address_proof_path": "D:/Playwright/3rdAgent/REQPICS/Screenshot 2026-01-26 200035.png",
            "address_doc_no": "TN31DL2026000123"
        }
    }

    parser = argparse.ArgumentParser(description="Run TNeSevai automation")
    parser.add_argument("--payload", help="Path to JSON file")
    args = parser.parse_args()

    if args.payload:
        with open(args.payload, "r") as f: payload = json.load(f)
    else: payload = _defaults

    bot = TNeSevaiBackendAgent(payload)
    bot.run()