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

    def _ws_prompt(self, event_dict, timeout=3000):
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

    def safe_select_dropdown(self, page, selector, value, field_name):
        """Safely select dropdown option with fallback strategies."""
        if not value:
            return False
        
        try:
            dropdown = page.locator(selector)
            
            # Wait for dropdown to be visible and enabled
            dropdown.wait_for(state="visible", timeout=5000)
            time.sleep(0.5)
            
            # Strategy 1: Try exact label match
            try:
                dropdown.select_option(label=value)
                self.log(f"✓ Selected {field_name}: {value}")
                return True
            except:
                pass
            
            # Strategy 2: Try case-insensitive partial match
            try:
                options = dropdown.locator('option').all_text_contents()
                for option in options:
                    if option.strip().upper() == "SELECT":
                        continue
                    if value.lower() in option.lower() or option.lower() in value.lower():
                        dropdown.select_option(label=option)
                        self.log(f"✓ Selected {field_name}: {option} (matched with {value})")
                        return True
            except:
                pass
            
            # Strategy 3: Try by value attribute
            try:
                dropdown.select_option(value=value)
                self.log(f"✓ Selected {field_name} by value: {value}")
                return True
            except:
                pass
            
            # Strategy 4: Try first non-SELECT option if exact match fails
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
            except:
                pass
            
            self.log(f"✗ WARNING: Could not select {field_name} with value '{value}'")
            return False
            
        except Exception as e:
            self.log(f"✗ ERROR selecting {field_name}: {str(e)}")
            return False

    PORTAL_URL = "https://www.tnesevai.tn.gov.in/"
    NAV_TIMEOUT = 90_000  # 90 seconds – government portals are slow
    MAX_GOTO_RETRIES = 3

    def _check_connectivity(self, max_retries=None, retry_delay=5):
        """
        Quick pre-flight check before launching the browser with automatic retry.
        
        Args:
            max_retries: Maximum number of retry attempts (None = infinite retries)
            retry_delay: Seconds to wait between retry attempts (default: 5)
        
        Returns:
            True when connection is successful
        """
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
                
                self.log(f"✗ Cannot reach portal (attempt {attempt}). Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

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
        """Run the automation in a separate thread to avoid asyncio conflicts."""
        import threading
        
        # Run Playwright in a separate thread
        thread = threading.Thread(target=self._run_playwright)
        thread.start()
        thread.join()
    
    def _run_playwright(self):
        """Internal method that runs the actual Playwright automation."""
        try:
            # --- Pre-flight connectivity check with infinite retry ---
            self.log("Checking portal connectivity...")
            self._check_connectivity(max_retries=None, retry_delay=5)  # Infinite retries every 5 seconds

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

                # --- Fill Applicant Details Form ---
                self.log("Filling Applicant Details and Address Form...")
                
                # Wait for form to be fully loaded
                page_form.wait_for_selector('[id="residence:cRvillageListId"]', timeout=10000)
                time.sleep(2)
                
                # Helper function to check if field is empty
                def is_field_empty(locator_str):
                    try:
                        element = page_form.locator(locator_str)
                        if element.count() == 0:
                            return True
                        value = element.input_value() if element.count() > 0 else ""
                        return not value or value.strip() == ""
                    except:
                        return True
                
                def is_dropdown_empty(locator_str):
                    try:
                        element = page_form.locator(locator_str)
                        if element.count() == 0:
                            return True
                        value = element.input_value() if element.count() > 0 else ""
                        # Check if it's still on default "SELECT" or empty
                        return not value or value.strip() == "" or value.strip().upper() == "SELECT"
                    except:
                        return True
                
                # Fill Applicant Name (if available and field is empty)
                if self.applicant.get("name") and is_field_empty('[id="residence:applicantName"]'):
                    try:
                        page_form.locator('[id="residence:applicantName"]').fill(self.applicant.get("name"))
                        self.log(f"Filled Applicant Name: {self.applicant.get('name')}")
                    except:
                        self.log("Applicant Name field not found")
                
                # Fill Father/Husband Name (if available and field is empty)
                if self.applicant.get("father_name") and is_field_empty('[id="residence:fatherName"]'):
                    try:
                        page_form.locator('[id="residence:fatherName"]').fill(self.applicant.get("father_name"))
                        self.log(f"Filled Father Name: {self.applicant.get('father_name')}")
                    except:
                        self.log("Father Name field not found")
                
                # Fill Gender dropdown (if available and dropdown is empty)
                if self.applicant.get("gender") and is_dropdown_empty('[id="residence:gender"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:gender"]', 
                                             self.applicant.get("gender"), "Gender")
                    time.sleep(1)
                
                # Fill Religion dropdown (if available and dropdown is empty)
                if self.applicant.get("religion") and is_dropdown_empty('[id="residence:religion"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:religion"]', 
                                             self.applicant.get("religion"), "Religion")
                    time.sleep(2)  # Wait for any dependent fields
                
                # Fill Community dropdown (if available and dropdown is empty)
                if self.applicant.get("community") and is_dropdown_empty('[id="residence:community"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:community"]', 
                                             self.applicant.get("community"), "Community")
                    time.sleep(2)  # Wait for any dependent fields
                
                # Fill State dropdown (if available and dropdown is empty)
                if self.address.get("state") and is_dropdown_empty('[id="residence:state"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:state"]', 
                                             self.address.get("state"), "State")
                    time.sleep(3)  # Wait longer for district dropdown to populate
                
                # Fill District dropdown (if available and dropdown is empty)
                if self.address.get("district") and is_dropdown_empty('[id="residence:district"]'):
                    self.safe_select_dropdown(page_form, '[id="residence:district"]', 
                                             self.address.get("district"), "District")
                    time.sleep(3)  # Wait longer for village dropdown to populate
                
                # Fill Revenue Village dropdown - CRITICAL: Use 'area' field, not 'village'
                # The Revenue Village dropdown should match the area/locality from extracted data
                revenue_village_value = self.address.get("area") or self.address.get("village")
                if is_dropdown_empty('[id="residence:cRvillageListId"]'):
                    self.log(f"Revenue Village dropdown is empty, attempting to fill...")
                    
                    # Try with extracted value first
                    if revenue_village_value:
                        self.log(f"Attempting to fill Revenue Village with: {revenue_village_value}")
                        success = self.safe_select_dropdown(page_form, '[id="residence:cRvillageListId"]', 
                                                 revenue_village_value, "Revenue Village")
                        
                        # If that fails, try to select the first available option
                        if not success:
                            self.log("Extracted value didn't match, trying first available option...")
                            try:
                                dropdown = page_form.locator('[id="residence:cRvillageListId"]')
                                options = dropdown.locator('option').all()
                                for option in options:
                                    option_text = option.text_content().strip()
                                    if option_text.upper() != "SELECT" and option_text:
                                        option_value = option.get_attribute('value')
                                        if option_value:
                                            dropdown.select_option(value=option_value)
                                            self.log(f"✓ Selected Revenue Village: {option_text} (first available)")
                                            break
                            except Exception as e:
                                self.log(f"✗ Could not select any Revenue Village option: {e}")
                    else:
                        # No extracted value, select first available option
                        self.log("No extracted value for Revenue Village, selecting first available option...")
                        try:
                            dropdown = page_form.locator('[id="residence:cRvillageListId"]')
                            options = dropdown.locator('option').all()
                            for option in options:
                                option_text = option.text_content().strip()
                                if option_text.upper() != "SELECT" and option_text:
                                    option_value = option.get_attribute('value')
                                    if option_value:
                                        dropdown.select_option(value=option_value)
                                        self.log(f"✓ Selected Revenue Village: {option_text} (first available)")
                                        break
                        except Exception as e:
                            self.log(f"✗ Could not select any Revenue Village option: {e}")
                    
                    time.sleep(2)
                
                # Fill Building/Door Number (if field is empty)
                if self.address.get("building_no") and is_field_empty('[id="residence:buildForList"]'):
                    page_form.locator('[id="residence:buildForList"]').fill(self.address.get("building_no"))
                    self.log(f"Filled Building No: {self.address.get('building_no')}")
                
                # Fill Street Name (if field is empty)
                if self.address.get("street_name") and is_field_empty('[id="residence:streetForList"]'):
                    page_form.locator('[id="residence:streetForList"]').fill(self.address.get("street_name"))
                    self.log(f"Filled Street Name: {self.address.get('street_name')}")
                
                # Fill Pincode (if field is empty)
                if self.address.get("pincode") and is_field_empty('[id="residence:pinForList"]'):
                    page_form.locator('[id="residence:pinForList"]').fill(self.address.get("pincode"))
                    self.log(f"Filled Pincode: {self.address.get('pincode')}")
                
                # Fill Permanent Address fields (if different from current)
                # Check if permanent address checkbox needs to be handled
                try:
                    same_address_checkbox = page_form.locator('[id="residence:sameAsCurrentAddress"]')
                    if same_address_checkbox.is_visible() and not same_address_checkbox.is_checked():
                        same_address_checkbox.check()
                        self.log("Checked 'Same as Current Address' for Permanent Address")
                        time.sleep(1)
                except:
                    self.log("Same address checkbox not found, checking permanent address fields")
                    # Fill permanent address fields only if they are empty
                    if self.address.get("perm_state") and is_dropdown_empty('[id="residence:pRstate"]'):
                        self.safe_select_dropdown(page_form, '[id="residence:pRstate"]', 
                                                 self.address.get("perm_state"), "Permanent State")
                        time.sleep(2)
                    if self.address.get("perm_district") and is_dropdown_empty('[id="residence:pRdistrict"]'):
                        self.safe_select_dropdown(page_form, '[id="residence:pRdistrict"]', 
                                                 self.address.get("perm_district"), "Permanent District")
                        time.sleep(2)
                    if self.address.get("perm_village") and is_dropdown_empty('[id="residence:pRvillageListId"]'):
                        self.safe_select_dropdown(page_form, '[id="residence:pRvillageListId"]', 
                                                 self.address.get("perm_village"), "Permanent Village")
                        time.sleep(1)
                    if self.address.get("perm_building_no") and is_field_empty('[id="residence:buildPerList"]'):
                        try:
                            page_form.locator('[id="residence:buildPerList"]').fill(self.address.get("perm_building_no"))
                        except:
                            pass
                    if self.address.get("perm_street_name") and is_field_empty('[id="residence:streetPerList"]'):
                        try:
                            page_form.locator('[id="residence:streetPerList"]').fill(self.address.get("perm_street_name"))
                        except:
                            pass
                    if self.address.get("perm_pincode") and is_field_empty('[id="residence:pinPerList"]'):
                        try:
                            page_form.locator('[id="residence:pinPerList"]').fill(self.address.get("perm_pincode"))
                        except:
                            pass
                
                # Fill Contact Details (only if empty)
                if self.applicant.get("mobile_number") and is_field_empty('[id="residence:mobileNumber"]'):
                    try:
                        page_form.locator('[id="residence:mobileNumber"]').fill(self.applicant.get("mobile_number"))
                        self.log(f"Filled Mobile Number: {self.applicant.get('mobile_number')}")
                    except:
                        self.log("Mobile number field not found")
                
                if self.applicant.get("email") and is_field_empty('[id="residence:email"]'):
                    try:
                        page_form.locator('[id="residence:email"]').fill(self.applicant.get("email"))
                        self.log(f"Filled Email: {self.applicant.get('email')}")
                    except:
                        self.log("Email field not found")
                
                # Fill Residence Period (From and To dates) - only if empty
                if self.address.get("from_date") and is_field_empty('[id="residence:fromDateListInputDate"]'):
                    fmt_from = self.format_date_for_injection(self.address.get("from_date"))
                    page_form.evaluate(f"document.getElementById('residence:fromDateListInputDate').value = '{fmt_from}';")
                    self.log(f"Filled Residing From Date: {fmt_from}")
                
                if self.address.get("to_date") and is_field_empty('[id="residence:toDateListInputDate"]'):
                    fmt_to = self.format_date_for_injection(self.address.get("to_date"))
                    page_form.evaluate(f"document.getElementById('residence:toDateListInputDate').value = '{fmt_to}';")
                    self.log(f"Filled Residing To Date: {fmt_to}")
                
                # Fill Ration Card Number (only if empty)
                if self.applicant.get("ration_card_no") and is_field_empty('[id="residence:rationCardId"]'):
                    page_form.locator('[id="residence:rationCardId"]').fill(self.applicant.get("ration_card_no"))
                    self.log(f"Filled Ration Card No: {self.applicant.get('ration_card_no')}")
                    time.sleep(2) 

                # Final verification before clicking Add button
                self.log("Verifying all required fields are filled before clicking Add...")
                time.sleep(2)
                
                # Check if Revenue Village is still on SELECT
                try:
                    revenue_dropdown = page_form.locator('[id="residence:cRvillageListId"]')
                    current_value = revenue_dropdown.input_value()
                    if not current_value or current_value.strip() == "" or current_value.strip().upper() == "SELECT":
                        self.log("⚠ WARNING: Revenue Village is still on SELECT, attempting to select first option...")
                        options = revenue_dropdown.locator('option').all()
                        for option in options:
                            option_text = option.text_content().strip()
                            if option_text.upper() != "SELECT" and option_text:
                                option_value = option.get_attribute('value')
                                if option_value:
                                    revenue_dropdown.select_option(value=option_value)
                                    self.log(f"✓ Selected Revenue Village: {option_text}")
                                    time.sleep(1)
                                    break
                except Exception as e:
                    self.log(f"Could not verify Revenue Village: {e}")

                self.log("Clicking Add button to submit address details...")
                page_form.get_by_role("button", name="Add").click()
                time.sleep(5)

                # Dialog Handler - Auto-accept any dialogs
                def safe_dialog_handler(dialog):
                    try: 
                        self.log(f"Auto-accepting dialog: {dialog.message}")
                        dialog.accept()
                    except Exception: 
                        pass 
                page_form.on("dialog", safe_dialog_handler) 

                self.log("Clicking Submit button to proceed to document upload page...")
                page_form.get_by_role("button", name="Submit").click()
                page_form.wait_for_load_state("networkidle")
                time.sleep(6)
                
                # Check for and click OK button on any popup/dialog
                try:
                    ok_button = page_form.get_by_role("button", name="OK")
                    if ok_button.is_visible(timeout=3000):
                        self.log("Found OK button on dialog, clicking it...")
                        ok_button.click()
                        time.sleep(2)
                except:
                    self.log("No OK button found or already dismissed")
                
                self.log("✓ Form submitted successfully! Now on document upload page.")

                # --- AUTOMATIC DOCUMENT UPLOAD (NO CONFIRMATION) ---
                self.log("Starting automatic document upload process...")
                time.sleep(2)

                # --- DOCUMENT UPLOAD FLOW ---
                self.log("Starting Document Upload Process...")
                
                # Helper function to convert file to image if needed
                def ensure_image_format(file_path):
                    """Convert file to image format if it's a PDF, otherwise return as-is."""
                    if not file_path or not os.path.exists(file_path):
                        return None
                    
                    # If already an image, return as-is
                    if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        self.log(f"File is already in image format: {file_path}")
                        return file_path
                    
                    # If PDF, convert to image
                    if file_path.lower().endswith('.pdf'):
                        self.log(f"Converting PDF to image: {file_path}")
                        try:
                            from pdf2image import convert_from_path
                            images = convert_from_path(file_path, first_page=1, last_page=1, dpi=200)
                            if images:
                                image_path = file_path.replace('.pdf', '_converted.jpg')
                                images[0].save(image_path, 'JPEG', quality=95)
                                self.log(f"✓ PDF converted to image: {image_path}")
                                return image_path
                        except ImportError:
                            self.log("✗ WARNING: pdf2image not installed. Trying to upload PDF directly...")
                            return file_path
                        except Exception as e:
                            self.log(f"✗ WARNING: PDF conversion failed: {e}. Trying to upload PDF directly...")
                            return file_path
                    
                    return file_path
                
                # ========== STEP 1: UPLOAD PHOTO ==========
                self.log("Step 1: Uploading Photo...")
                try:
                    # Get photo path from payload
                    photo_path = self.docs.get("photo_path")
                    self.log(f"Photo path from payload: {photo_path}")
                    
                    if not photo_path:
                        self.log("✗ ERROR: No photo path provided in payload!")
                        self.log(f"Available docs: {self.docs}")
                    elif not os.path.exists(photo_path):
                        self.log(f"✗ ERROR: Photo file does not exist at: {photo_path}")
                    else:
                        # Ensure it's in image format (load into memory)
                        photo_image = ensure_image_format(photo_path)
                        if photo_image:
                            # Select "Photo" from dropdown
                            page_form.get_by_role("combobox").first.select_option(label="Photo")
                            self.log("✓ Selected 'Photo' from dropdown")
                            time.sleep(1)
                            
                            # Find the file input element (hidden)
                            file_input = page_form.locator("input[type='file']").last
                            
                            # Set the file directly WITHOUT clicking Add button (no dialog)
                            file_input.set_input_files(photo_image)
                            self.log(f"✓ Photo file loaded into memory and set: {photo_image}")
                            time.sleep(2)
                            
                            # Now click the Add/Upload button to submit
                            page_form.locator("text=Add...").first.click()
                            self.log("✓ Clicked 'Add...' button to upload photo")
                            time.sleep(3)
                            
                            # Clean up converted file if it was created
                            if photo_image != photo_path and os.path.exists(photo_image):
                                try:
                                    os.remove(photo_image)
                                    self.log(f"✓ Cleaned up temporary file: {photo_image}")
                                except:
                                    pass
                        else:
                            self.log("✗ WARNING: Could not prepare photo for upload!")
                except Exception as e:
                    self.log(f"✗ ERROR uploading photo: {e}")
                    import traceback
                    traceback.print_exc()
                
                # ========== STEP 2: SELF-DECLARATION FORM ==========
                self.log("Step 2: Handling Self-Declaration Form...")
                
                # ALWAYS download the self-declaration form from the portal page
                self.log("Downloading Self-Declaration Form from portal...")
                try:
                    with page_form.expect_download(timeout=15000) as download_info:
                        # Click the "Download Self declaration form" link
                        page_form.get_by_text("Download Self declaration form").click()
                    
                    download = download_info.value
                    save_path = os.path.join(os.getcwd(), "Self_Declaration_Form_To_Sign.pdf")
                    download.save_as(save_path)
                    self.log(f"✓ Self-Declaration Form downloaded: {save_path}")
                    
                    # Send download notification to frontend
                    if self.ws_manager and self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self.ws_manager.send_event({
                                "type": "SELF_DECLARATION_DOWNLOADED",
                                "message": "Self-Declaration Form downloaded. Please download, sign it, and upload the signed version.",
                                "file_path": save_path,
                                "download_url": f"http://localhost:8000/download-declaration"
                            }),
                            self.loop
                        ).result(timeout=10)
                    
                    # WAIT for user to download, sign, and upload the signed version
                    self.log("Waiting for user to upload signed Self-Declaration Form...")
                    signed_form_response = self._ws_prompt({
                        "type": "REQUEST_SIGNED_DECLARATION",
                        "message": "Please download the Self-Declaration Form, sign it, and upload the signed version. You can also exit if needed.",
                        "download_path": save_path,
                        "download_url": f"http://localhost:8000/download-declaration",
                        "allow_exit": True
                    })
                    
                    # Check if user exited
                    if signed_form_response and signed_form_response.lower() == "exit":
                        self.log("User chose to exit. Stopping automation.")
                        return
                    
                    signed_form_path = signed_form_response
                    
                except Exception as e:
                    self.log(f"✗ ERROR downloading self-declaration: {e}")
                    return
                
                # Now upload the signed form to the portal
                try:
                    self.log("Uploading signed Self-Declaration Form to portal...")
                    
                    # Upload the signed form (convert to image if needed)
                    if signed_form_path and os.path.exists(signed_form_path):
                        signed_image = ensure_image_format(signed_form_path)
                        if signed_image:
                            # Select "Self-Declaration of Applicant" from dropdown
                            page_form.get_by_role("combobox").first.select_option(label="Self-Declaration of Applicant")
                            self.log("✓ Selected 'Self-Declaration of Applicant' from dropdown")
                            time.sleep(1)
                            
                            # Find the file input element and set file WITHOUT clicking Add
                            file_input = page_form.locator("input[type='file']").last
                            file_input.set_input_files(signed_image)
                            self.log(f"✓ Signed Self-Declaration file loaded into memory: {signed_image}")
                            time.sleep(2)
                            
                            # Now click Add button to submit
                            page_form.locator("text=Add...").first.click()
                            self.log("✓ Clicked 'Add...' button to upload signed declaration")
                            time.sleep(3)
                            
                            # Clean up converted file if it was created
                            if signed_image != signed_form_path and os.path.exists(signed_image):
                                try:
                                    os.remove(signed_image)
                                    self.log(f"✓ Cleaned up temporary file: {signed_image}")
                                except:
                                    pass
                        else:
                            self.log("✗ WARNING: Could not prepare signed declaration for upload!")
                    else:
                        self.log("✗ WARNING: Signed declaration file not provided or not found!")
                        
                except Exception as e:
                    self.log(f"✗ ERROR uploading Self-Declaration: {e}")
                    import traceback
                    traceback.print_exc()
                
                # ========== STEP 3: CURRENT ADDRESS PROOF (DRIVING LICENSE) ==========
                self.log("Step 3: Uploading Current Address Proof (Driving License)...")
                try:
                    # Get file paths from payload
                    driving_license_path = self.docs.get("driving_license_path")
                    address_proof_path = self.docs.get("address_proof_path")
                    
                    self.log(f"Driving License path from payload: {driving_license_path}")
                    self.log(f"Address Proof path from payload: {address_proof_path}")
                    
                    # Try driving license first, fallback to address proof if not available
                    upload_path = None
                    if driving_license_path and os.path.exists(driving_license_path):
                        upload_path = driving_license_path
                        self.log(f"✓ Using Driving License: {upload_path}")
                    elif address_proof_path and os.path.exists(address_proof_path):
                        upload_path = address_proof_path
                        self.log(f"✓ Using Address Proof (fallback): {upload_path}")
                    else:
                        self.log("✗ ERROR: No valid address proof document found!")
                        self.log(f"Available docs: {self.docs}")
                    
                    if upload_path:
                        # Convert to image format if needed (load into memory)
                        address_image = ensure_image_format(upload_path)
                        if address_image:
                            # Select "Current Address Proof" from dropdown
                            page_form.get_by_role("combobox").first.select_option(label="Current Address Proof")
                            self.log("✓ Selected 'Current Address Proof' from dropdown")
                            time.sleep(1)
                            
                            # Find the file input element and set file WITHOUT clicking Add
                            file_input = page_form.locator("input[type='file']").last
                            file_input.set_input_files(address_image)
                            self.log(f"✓ Address proof file loaded into memory: {address_image}")
                            time.sleep(2)
                            
                            # Now click Add button to open the form
                            page_form.locator("text=Add...").first.click()
                            self.log("✓ Clicked 'Add...' button")
                            time.sleep(2)
                            
                            # Ask user for document number
                            self.log("Requesting document number from user...")
                            doc_number = self._ws_prompt({
                                "type": "REQUEST_DOCUMENT_NUMBER",
                                "message": "Please enter the Document Number for Current Address Proof (Driving License number):"
                            })
                            
                            # Fill document number
                            if doc_number:
                                try:
                                    doc_input = page_form.locator('[id="ss:dscnum"]')
                                    doc_input.click()
                                    doc_input.fill(doc_number)
                                    doc_input.press("Tab")
                                    self.log(f"✓ Document number filled: {doc_number}")
                                    time.sleep(2)
                                except Exception as e:
                                    self.log(f"✗ Could not fill document number: {e}")
                            
                            # File should already be attached, wait for upload to complete
                            time.sleep(3)
                            
                            # Clean up converted file if it was created
                            if address_image != upload_path and os.path.exists(address_image):
                                try:
                                    os.remove(address_image)
                                    self.log(f"✓ Cleaned up temporary file: {address_image}")
                                except:
                                    pass
                        else:
                            self.log("✗ WARNING: Could not prepare address proof for upload!")
                    else:
                        self.log("✗ WARNING: No address proof file to upload!")
                        
                except Exception as e:
                    self.log(f"✗ ERROR uploading address proof: {e}")
                    import traceback
                    traceback.print_exc()
                
                # ========== FINAL STEP: SUBMIT/PROCEED ==========
                self.log("All documents uploaded! Looking for Submit/Proceed button...")
                try:
                    # Try to find and click Submit or Proceed button
                    time.sleep(3)
                    
                    # Try multiple button variations
                    button_clicked = False
                    for button_name in ["Proceed", "Submit", "Make Payment", "Continue"]:
                        try:
                            page_form.get_by_role("button", name=button_name).click(force=True)
                            self.log(f"✓ Clicked '{button_name}' button")
                            button_clicked = True
                            break
                        except:
                            continue
                    
                    if not button_clicked:
                        # Try by input value
                        for button_value in ["Proceed", "Submit", "Make Payment"]:
                            try:
                                page_form.locator(f'input[value="{button_value}"]').first.click(force=True)
                                self.log(f"✓ Clicked '{button_value}' button")
                                button_clicked = True
                                break
                            except:
                                continue
                    
                    if button_clicked:
                        page_form.wait_for_load_state("networkidle")
                        time.sleep(5)
                        self.log("✓ Form submitted successfully!")
                    else:
                        self.log("⚠ WARNING: Could not find Submit/Proceed button. Please check manually.")
                        
                except Exception as e:
                    self.log(f"✗ ERROR clicking final submit button: {e}")

                self.log("SUCCESS! Document upload process complete.")
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