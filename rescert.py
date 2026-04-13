import os
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

class TNeSevaiBackendAgent:     
    def __init__(self, json_payload):
        self.data = json_payload
        
        # Parse JSON into easily accessible variables
        self.creds = self.data.get("credentials", {})
        self.applicant = self.data.get("applicant_details", {})
        self.address = self.data.get("address_details", {})
        self.docs = self.data.get("documents", {})

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
                page.goto("https://www.tnesevai.tn.gov.in/")
                page.get_by_role("link", name="English Version").click()
                page.get_by_role("button", name="Citizen Login").click()
                
                self.log("Entering Credentials...")
                page.get_by_role("textbox", name="User Name").fill(self.creds.get("username"))
                page.get_by_role("textbox", name="Password").fill(self.creds.get("password"))

                # --- Captcha Handling (Agent Pause 1) ---
                self.log("Extracting Captcha...")
                captcha_img = page.locator("#captcha_image, img[src*='Captcha']").first
                captcha_path = "backend_captcha.png"
                captcha_img.screenshot(path=captcha_path)
                
                self.log(f"Captcha saved to {os.path.abspath(captcha_path)}")
                # In production, the agent sends this image to the user via API here.
                user_captcha = input("AGENT PROMPT -> Please enter the captcha code seen in the image: ")
                
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
                
                # In production, the agent waits for the user to reply with the OTP via API here.
                user_otp = input("AGENT PROMPT -> OTP sent to registered mobile. Enter OTP: ")
                
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
                # In production, the agent sends the PDF to the user, waits for them to send back
                # the signed PDF, Photo, and Address Proof, saves them locally, and then resumes.
                self.log("Waiting for user to provide signed documents...")
                input("AGENT PROMPT -> Ensure photo, signed declaration, and address proof are saved at the JSON paths. Press Enter to resume upload: ")

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
    bot = TNeSevaiBackendAgent(default_json_payload)
    bot.run()