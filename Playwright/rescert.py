import os
import time
import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

import asyncio
import concurrent.futures

class TNeSevaiBackendAgent:
    def __init__(self, json_payload, ws_manager=None, loop=None):
        self.data = json_payload
        self.ws = ws_manager
        self.loop = loop
        
        # Parse JSON into easily accessible variables
        self.creds = self.data.get("credentials", {})
        self.applicant = self.data.get("applicant_details", {})
        self.address = self.data.get("address_details", {})
        self.docs = self.data.get("documents", {})

    def _emit_and_wait(self, event_type: str, payload: dict = None, page=None):
        if not self.ws or not self.loop:
            self.log(f"No WebSocket connection. Falling back to CLI for {event_type}")
            return input(f"AGENT PROMPT -> {event_type}: ")

        # Clear old response
        self.ws.latest_response = None
        
        event = {"type": event_type}
        if payload: event.update(payload)
            
        self.log(f"Emitting {event_type} to frontend...")
        asyncio.run_coroutine_threadsafe(self.ws.send_event(event), self.loop)
        
        self.log("Waiting for user response from frontend...")
        # Since this Playwright execution runs in a Starlette ThreadPool, we MUST wait synchronously
        # to block execution cleanly without tangling event loops.
        while self.ws.latest_response is None:
            if page:
                page.wait_for_timeout(1000)
            else:
                time.sleep(1)
            
        ans = self.ws.latest_response.get("data")
        self.ws.latest_response = None
        return ans

    def log(self, message):
        """Prints status updates to the terminal for the backend agent to read."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [STATUS] {message}")

    def format_date_for_injection(self, date_str):
        try:
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%b-%Y"):
                try: return datetime.strptime(date_str, fmt).strftime("%d-%b-%Y")
                except ValueError: continue
            return date_str 
        except: return date_str

    def run(self):
        try:
            with sync_playwright() as playwright:
                self.log("Launching Browser in HEADLESS mode...")
                # Headless is True. Slow_mo kept for stability against anti-bot measures
                browser = playwright.chromium.launch(headless=False, slow_mo=200)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()

                # --- Login ---
                self.log("Navigating to TNeSevai Portal...")
                # The TNeSevai server is notoriously slow or blocks fast connections.
                # Use a larger timeout and wait for domcontentloaded instead of 'load'
                try:
                    page.goto("https://www.tnesevai.tn.gov.in/", timeout=90000, wait_until="domcontentloaded")
                except Exception as e:
                    self.log(f"Initial load errored ({str(e)}). Retrying in 5 seconds...")
                    time.sleep(5)
                    page.goto("https://www.tnesevai.tn.gov.in/", timeout=120000, wait_until="domcontentloaded")
                
                time.sleep(2)
                page.get_by_role("link", name="English Version").click()
                time.sleep(1)
                page.get_by_role("button", name="Citizen Login").click()
                
                self.log("Entering Credentials...")
                page.get_by_role("textbox", name="User Name").fill(self.creds.get("username"))
                page.get_by_role("textbox", name="Password").fill(self.creds.get("password"))

                # --- Captcha Handling (Agent Pause 1) ---
                while True:
                    self.log("Extracting Captcha...")
                    # ensure image is loaded/refreshed
                    time.sleep(1)
                    captcha_img = page.locator("#captcha_image, img[src*='Captcha']").first
                    captcha_path = "backend_captcha.png"
                    captcha_img.screenshot(path=captcha_path)
                    
                    self.log(f"Captcha saved to {os.path.abspath(captcha_path)}")
                    
                    # Request Captcha through WebSocket
                    user_captcha = self._emit_and_wait(
                        "REQUEST_CAPTCHA", 
                        {"message": "Please enter the captcha code seen in the image."},
                        page=page
                    )
                    
                    page.get_by_role("textbox", name="Enter Captcha Code").fill(user_captcha)

                    # Click login and wait to see what happens
                    self.log("Clicking Login...")
                    page.get_by_role("button", name="Login").click()
                    
                    # Wait for either the successful dashboard or an error message
                    # Using a short timeout loop to check for the error text "Invalid Captcha" or similar
                    try:
                        # Wait for the next page or an error span to appear
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except:
                        pass
                        
                    # Check for common failure messages on the same page
                    if page.locator("text=Invalid Captcha").is_visible() or page.locator("text=Invalid Username or password").is_visible() or page.locator("text=Please Enter Valid Captcha").is_visible():
                        self.log("Login failed (Invalid user/password or Captcha). Let's try again...")
                        # Clear old input and let loop repeat
                        page.get_by_role("textbox", name="Enter Captcha Code").fill("")
                        continue
                    else:
                        # Success, we moved to the next page
                        self.log("Login Successful!")
                        break

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
                current_can = self.applicant.get('can_number', "")
                if not current_can or current_can.strip() == "":
                    self.log("Missing CAN Number. Requesting from user...")
                    user_provided_data = self._emit_and_wait(
                        "REQUEST_MISSING_DETAILS",
                        {
                            "message": "CAN Number is missing or was static. Please provide it:",
                            "missing_fields": ["CAN Number"]
                        },
                        page=page
                    )
                    if isinstance(user_provided_data, dict) and "CAN Number" in user_provided_data:
                        self.applicant["can_number"] = user_provided_data["CAN Number"]

                self.log(f"Searching CAN: {self.applicant.get('can_number')}...")
                page_form.locator('[id="statusform:aadhar"]').fill(self.applicant.get("can_number")) 
                
                self.log("Clicking Search...")
                search_btn = page_form.locator('input[value="Search"], button:has-text("Search")').first
                search_btn.click(force=True)
                time.sleep(8) 
                
                self.log("Selecting CAN record...")
                try: 
                    # Use a stable selector for the radio button in the search results table
                    radio_btn = page_form.locator('input[name="statusform:j_idt220"]').first
                    if radio_btn.count() == 0:
                        radio_btn = page_form.locator('input[type="radio"]').first
                    radio_btn.click()
                    time.sleep(3) # Wait for any AJAX updates triggered by selection
                except Exception as e:
                    self.log(f"Warning: Could not click CAN radio button. Proceeding anyway. {str(e)}")
                
                # --- Missing Details Check (Fallback 4) ---
                current_aadhar = self.applicant.get("aadhar_number", "")
                current_dob = self.applicant.get("dob", "")
                missing_fields = []
                
                if not current_aadhar or current_aadhar.strip() == "":
                    missing_fields.append("Aadhaar Number")
                if not current_dob or current_dob.strip() == "":
                    missing_fields.append("Date of Birth (DD/MM/YYYY)")
                    
                if missing_fields:
                    missing_str = " and ".join(missing_fields)
                    self.log(f"Missing {missing_str}. Requesting from user...")
                    
                    user_provided_data = self._emit_and_wait(
                        "REQUEST_MISSING_DETAILS",
                        {
                            "message": f"Could not extract {missing_str} from documents. Please provide them below:",
                            "missing_fields": missing_fields
                        },
                        page=page
                    )
                    
                    # user_provided_data should be a dict returned from the frontend
                    # e.g. {"Aadhaar Number": "1234", "Date of Birth (DD/MM/YYYY)": "01/01/2000"}
                    if isinstance(user_provided_data, dict):
                        if "Aadhaar Number" in user_provided_data:
                            self.applicant["aadhar_number"] = user_provided_data["Aadhaar Number"]
                        if "Date of Birth (DD/MM/YYYY)" in user_provided_data:
                            self.applicant["dob"] = user_provided_data["Date of Birth (DD/MM/YYYY)"]
                
                self.log("Typing Aadhaar Number securely...")
                # Fallback list of possible IDs for the Aadhaar input
                aadhar_locators = [
                    '[id="statusform:uid"]',
                    '[id="statusform:citAadharNo"]',
                    '[id="statusform:aadharNo"]',
                    '[id="statusform:txtAadharNo"]'
                ]
                
                aadhar_input = None
                for loc in aadhar_locators:
                    try:
                        if page_form.locator(loc).count() > 0 and page_form.locator(loc).first.is_visible():
                            aadhar_input = page_form.locator(loc).first
                            break
                    except Exception:
                        pass
                        
                if not aadhar_input:
                    # Final fallback to original ID in case it is somehow hidden or loading slow
                    self.log("Warning: Specific Aadhaar ID not found. Using default locator...")
                    aadhar_input = page_form.locator('[id="statusform:citAadharNo"]')

                try:
                    aadhar_input.click()
                    try:
                        aadhar_input.press_sequentially(self.applicant.get("aadhar_number"), delay=150)
                    except AttributeError:
                        aadhar_input.type(self.applicant.get("aadhar_number"), delay=150)
                    aadhar_input.press("Tab")
                except Exception as e:
                    self.log(f"Failed to fill Aadhaar: {str(e)}")
                
                time.sleep(5)
                
                # --- DOB Injection ---
                self.log("Injecting Date of Birth...")
                fmt_dob = self.format_date_for_injection(self.applicant.get("dob"))
                page_form.evaluate(f"""
                    var dobField = document.getElementById('statusform:citAapDOBInputDate')
                                || document.querySelector('input[id$="DOBInputDate"]')
                                || document.querySelector('input[id*="dobInputDate"]')
                                || document.querySelector('input[id*="DOBInput"]');
                    if (dobField) {{
                        dobField.value = '{fmt_dob}';
                        dobField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        dobField.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    }} else {{
                        console.error('DOB field not found!');
                    }}
                """)
                time.sleep(4)
                
                # --- OTP Flow (Agent Pause 2) ---
                self.log("Requesting OTP from Server...")
                # Ensure previously filled fields have triggered their onchange events
                page_form.keyboard.press("Tab")
                time.sleep(1)
                
                otp_btn = page_form.locator('input[value="Generate OTP"], button:has-text("Generate OTP")').first
                otp_btn.click(force=True)
                time.sleep(4)
                
                # Request OTP through WebSocket
                user_otp = self._emit_and_wait(
                    "REQUEST_OTP",
                    {"message": "OTP sent to registered mobile. Enter OTP:"},
                    page=page
                )
                
                page_form.locator('[id="statusform:otp_id"]').fill(user_otp)
                page_form.get_by_role("button", name="Confirm OTP").click()
                
                self.log("OTP Confirmed. Proceeding to Form...")
                page_form.get_by_role("button", name="Proceed").click()
                page_form.wait_for_load_state("networkidle")
                time.sleep(5)

                # --- Fill Address Details ---
                self.log("Validating Address Details...")
                missing_addr_fields = []
                if not self.applicant.get("ration_card_no"): missing_addr_fields.append("Ration Card Number")
                if not self.address.get("building_no"): missing_addr_fields.append("Building / Door No")
                if not self.address.get("street_name"): missing_addr_fields.append("Street Name")
                if not self.address.get("pincode"): missing_addr_fields.append("Pincode")

                if missing_addr_fields:
                    missing_str = ", ".join(missing_addr_fields)
                    self.log(f"Missing {missing_str}. Requesting from user...")
                    user_provided_data = self._emit_and_wait(
                        "REQUEST_MISSING_DETAILS",
                        {
                            "message": f"Could not extract {missing_str} from documents. Please provide them below:",
                            "missing_fields": missing_addr_fields
                        },
                        page=page
                    )
                    if isinstance(user_provided_data, dict):
                        if "Ration Card Number" in user_provided_data: self.applicant["ration_card_no"] = user_provided_data["Ration Card Number"]
                        if "Building / Door No" in user_provided_data: self.address["building_no"] = user_provided_data["Building / Door No"]
                        if "Street Name" in user_provided_data: self.address["street_name"] = user_provided_data["Street Name"]
                        if "Pincode" in user_provided_data: self.address["pincode"] = user_provided_data["Pincode"]

                self.log("Filling Address and Form Details...")
                
                try:
                    if self.address.get("building_no"): 
                        page_form.locator('[id="residence:buildForList"], input[id$="buildForList"]').first.fill(self.address.get("building_no"))
                    if self.address.get("street_name"): 
                        page_form.locator('[id="residence:streetForList"], input[id$="streetForList"]').first.fill(self.address.get("street_name"))
                    if self.address.get("pincode"): 
                        page_form.locator('[id="residence:pinForList"], input[id$="pinForList"]').first.fill(self.address.get("pincode"))

                    fmt_from = self.format_date_for_injection(self.address.get("from_date"))
                    page_form.evaluate(f"var el = document.getElementById('residence:fromDateListInputDate') || document.querySelector('input[id$=\"fromDateListInputDate\"]'); if(el) el.value = '{fmt_from}';")
                    fmt_to = self.format_date_for_injection(self.address.get("to_date"))
                    page_form.evaluate(f"var el = document.getElementById('residence:toDateListInputDate') || document.querySelector('input[id$=\"toDateListInputDate\"]'); if(el) el.value = '{fmt_to}';")
                    
                    if self.applicant.get("ration_card_no"):
                        page_form.locator('[id="residence:rationCardId"], input[id$="rationCardId"], input[id*="rationCard"], input[id$="rationCardNo"]').first.fill(self.applicant.get("ration_card_no"))
                        page_form.keyboard.press("Tab")
                        time.sleep(2) 
                except Exception as e:
                    self.log(f"Failed filling form details: {str(e)}")

                self.log("Submitting Details Table by clicking Add...")
                try:
                    # Look for the specific Add button that is just below the address entry row
                    # using exact name match or button properties
                    add_btn = page_form.locator('input[value="Add"], button:has-text("Add")').first
                    add_btn.click(force=True)
                    self.log("Clicked Add. Waiting for table to update...")
                    time.sleep(5)
                except Exception as e:
                    self.log(f"Warning: Failed to click Add button: {str(e)}")

                # Dialog Handler for Submit confirmation prompts
                def safe_dialog_handler(dialog):
                    try: dialog.accept()
                    except Exception: pass 
                page_form.on("dialog", safe_dialog_handler) 

                self.log("Submitting the entire form...")
                try:
                    # Look for the specific Submit button
                    submit_btn = page_form.get_by_role("button", name="Submit").first
                    if not submit_btn.is_visible():
                        submit_btn = page_form.locator('input[value="Submit"], button[type="submit"]:has-text("Submit")').first
                    submit_btn.click(force=True)
                    self.log("Clicked Submit. Waiting for network to settle...")
                    page_form.wait_for_load_state("networkidle")
                    time.sleep(6) 
                except Exception as e:
                    self.log(f"Warning: Failed to click Submit button: {str(e)}")

                # --- DOWNLOAD FORM ---
                self.log("Downloading Self Declaration Form...")
                self_decl_upload_path = self.docs.get("self_decl_path", "")
                try:
                    with page_form.expect_download(timeout=15000) as download_info:
                        page_form.get_by_role("link", name="Download Self declaration form").click(force=True)
                    download = download_info.value
                    save_path = os.path.join(os.getcwd(), "Self_Declaration_Form_For_User.pdf")
                    download.save_as(save_path)
                    self.log(f"Form saved locally at: {save_path}")
                    self_decl_upload_path = save_path
                except Exception as e:
                    self.log("Download skipped or failed. Proceeding.")
                    if not self_decl_upload_path or not os.path.exists(self_decl_upload_path):
                        self_decl_upload_path = os.path.join(os.getcwd(), "Self_Declaration_Form_For_User.pdf")

                # --- Document Upload Await (Agent Pause 3) ---
                self.log("Waiting for user to confirm signed documents...")
                self._emit_and_wait(
                    "REQUEST_SIGNED_DOCS",
                    {"message": "Ensure signed declaration is saved. Ready to resume upload?"},
                    page=page
                )

                # --- DOCUMENT UPLOADS ---
                def process_document_upload(doc_label, filepath, doc_no=None):
                    if not os.path.exists(filepath):
                        self.log(f"WARNING: File not found at {filepath}. Skipping {doc_label}...")
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
                process_document_upload("Self-Declaration of Applicant", self_decl_upload_path)
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


if __name__ == "__main__":
    # Simulate the JSON payload received from your AI Agent
    default_json_payload = {
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
            "address_proof_path": "D:/Playwright/3rdAgent/REQPICS/Screenshot 2026-01-26 200035.png",
            "address_doc_no": "TN3120250006924"
        }
    }

    # Initialize and run the backend bot
    bot = TNeSevaiBackendAgent(default_json_payload, ws_manager=None, loop=None)
    bot.run()