import os
import time
import json
import asyncio
import urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright  # type: ignore


class TNeSevaiBackendAgent:
    def __init__(self, json_payload, ws_manager=None):
        self.data = json_payload
        self.ws_manager = ws_manager

        # Parse JSON into easily accessible variables
        self.creds = self.data.get("credentials", {})
        self.applicant = self.data.get("applicant_details", {})
        self.address = self.data.get("address_details", {})
        self.docs = self.data.get("documents", {})

    # Maps raw log messages to friendly user-facing status text
    _FRIENDLY = [
        ("Checking portal connectivity",       "Checking if the portal is online…"),
        ("Portal is reachable",                "Portal is online ✓"),
        ("Launching Browser",                  "Starting the browser…"),
        ("Entering Credentials",               "Logging in to your account…"),
        ("Extracting Captcha",                 "Loading the captcha image…"),
        ("Sent WS event",                      None),   # suppress internal events
        ("Clicking Login",                     "Submitting login…"),
        ("Navigating to Residence Certificate","Opening Residence Certificate service…"),
        ("Searching CAN",                      "Looking up your account…"),
        ("Typing Aadhaar Number",              "Entering your Aadhaar number securely…"),
        ("Injecting Date of Birth",            "Filling in your date of birth…"),
        ("Requesting OTP",                     "Sending OTP to your mobile number…"),
        ("OTP Confirmed",                      "OTP verified ✓ — loading the form…"),
        ("Filling Form Details",               "Filling in your application details…"),
        ("Submitting Details Table",           "Saving your address details…"),
        ("Submitting Form",                    "Submitting the application form…"),
        ("Commencing Document Processing",     "Starting document uploads…"),
        ("Step 1/3: Uploading Photo",          "Uploading your photograph…"),
        ("Step 2/3: Downloading Self Declaration", "Downloading the Self Declaration form…"),
        ("Sending Self Declaration",           "Waiting for your signed declaration…"),
        ("Received signed Self Declaration",   "Signed declaration received ✓"),
        ("Step 3/3: Uploading Current Address Proof", "Uploading your address proof…"),
        ("All Documents Uploaded",             "All documents uploaded ✓ — going to payment…"),
        ("SUCCESS",                            "Done! Payment page reached ✓"),
        ("Wrong captcha",                      "❌ Wrong captcha — please try again with the new image."),
        ("Wrong OTP",                          "❌ Wrong OTP — please check your mobile and retry."),
        ("CRITICAL ERROR",                     "Something went wrong. Please try again."),
        ("WARNING",                            None),   # suppress warnings from UI
        ("Navigation attempt",                 None),   # suppress retry noise
        ("Navigating to",                      None),   # suppress raw URLs
        ("Selected",                           None),   # suppress field-level noise
    ]

    def log(self, message):
        """Prints status to terminal and sends a friendly update to the frontend."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [STATUS] {message}")

        if not self.ws_manager:
            return

        # Find the first matching friendly label
        friendly = None
        for keyword, label in self._FRIENDLY:
            if keyword.lower() in message.lower():
                friendly = label
                break

        # None means suppress this message from the UI
        if friendly is None:
            return

        self.ws_manager.send_event_sync({
            "type": "STATUS_UPDATE",
            "message": friendly
        })

    def _ws_prompt(self, event_dict, timeout=300):
        if not self.ws_manager:
            return input(f"AGENT PROMPT -> {event_dict.get('message', 'Enter value')}: ")

        self.ws_manager.latest_response = None
        self.ws_manager.send_event_sync(event_dict)
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

    def _ws_prompt_captcha(self, page, timeout=300):
        """Prompt for captcha, handling REFRESH_CAPTCHA action messages in the loop."""
        import base64

        def _screenshot_captcha():
            captcha_img = page.locator("#captcha_image, img[src*='Captcha'], img[src*='captcha']").first
            img_bytes = captcha_img.screenshot(type="png")
            return "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")

        def _click_captcha_refresh():
            """Click the refresh icon next to the captcha for a near-instant new captcha."""
            try:
                # The green circular arrows icon is an <img> near the captcha image.
                clicked = page.evaluate("""() => {
                    const captcha = document.querySelector('#captcha_image, img[src*="Captcha"], img[src*="captcha"]');
                    if (!captcha) return false;
                    for (let el = captcha.parentElement; el; el = el.parentElement) {
                        const imgs = el.querySelectorAll('img');
                        for (const img of imgs) {
                            if (img !== captcha) { img.click(); return true; }
                        }
                        const links = el.querySelectorAll('a');
                        for (const a of links) { a.click(); return true; }
                        if (el.tagName === 'TABLE' || el.tagName === 'FORM') break;
                    }
                    return false;
                }""")
                if clicked:
                    self.log("Captcha refresh icon clicked.")
                    # Wait for captcha image to reload
                    time.sleep(1.5)
                    # Always re-fill both credentials — portal clears them on captcha refresh
                    try:
                        user_field = page.get_by_role("textbox", name="User Name")
                        pass_field = page.get_by_role("textbox", name="Password")
                        user_field.wait_for(state="visible", timeout=3000)
                        user_field.fill(self.creds.get("username", ""))
                        pass_field.wait_for(state="visible", timeout=3000)
                        pass_field.fill(self.creds.get("password", ""))
                    except: pass
                    return
                raise Exception("refresh icon not found via JS")
            except Exception as e:
                self.log(f"Captcha JS click failed ({e}), falling back to page reload...")
                try:
                    page.reload(wait_until="domcontentloaded", timeout=8000)
                    time.sleep(1)
                    try: page.get_by_role("link", name="English Version").click(timeout=2000)
                    except: pass
                    try: page.get_by_role("button", name="Citizen Login").click(timeout=2000)
                    except: pass
                    try:
                        user_field = page.get_by_role("textbox", name="User Name")
                        user_field.wait_for(state="visible", timeout=3000)
                        user_field.fill(self.creds.get("username", ""))
                        pass_field = page.get_by_role("textbox", name="Password")
                        pass_field.wait_for(state="visible", timeout=3000)
                        pass_field.fill(self.creds.get("password", ""))
                    except: pass
                except Exception as e2:
                    self.log(f"Reload fallback also failed: {e2}")

        # Outer loop: re-screenshot and re-prompt after each refresh
        while True:
            captcha_b64 = _screenshot_captcha()
            self.ws_manager.latest_response = None
            self.ws_manager.send_event_sync({
                "type": "REQUEST_CAPTCHA",
                "message": "Please look at the captcha image and enter the code shown below.",
                "image": captcha_b64
            })

            # Inner loop: wait for USER_ANSWER or REFRESH_CAPTCHA
            elapsed = 0
            got_refresh = False
            while elapsed < timeout:
                response = self.ws_manager.latest_response
                if response is not None:
                    msg_type = response.get("type", "")
                    if msg_type == "REFRESH_CAPTCHA":
                        self.log("User requested captcha refresh...")
                        _click_captcha_refresh()
                        # Take new screenshot and push it to frontend immediately
                        new_b64 = _screenshot_captcha()
                        self.ws_manager.send_event_sync({
                            "type": "CAPTCHA_REFRESHED",
                            "image": new_b64
                        })
                        got_refresh = True
                        break  # break inner loop → outer loop re-prompts with new image
                    elif msg_type == "USER_ANSWER":
                        return str(response.get("data", ""))
                time.sleep(1)
                elapsed += 1

            if not got_refresh:
                raise TimeoutError("No captcha response received within timeout.")
            # got_refresh=True → outer while True loops back, re-screenshots and re-sends REQUEST_CAPTCHA

    def _ws_prompt_otp(self, page_form, timeout=300):
        """Prompt for OTP, handling GENERATE_OTP action messages in the loop."""
        self.ws_manager.latest_response = None
        self.ws_manager.send_event_sync({
            "type": "REQUEST_OTP",
            "message": "An OTP has been sent to your registered mobile number. Please enter the OTP below."
        })

        elapsed = 0
        while elapsed < timeout:
            response = self.ws_manager.latest_response
            if response is not None:
                msg_type = response.get("type", "")
                if msg_type == "GENERATE_OTP":
                    # User clicked Generate OTP — click the button on the portal
                    self.log("User requested new OTP generation...")
                    try:
                        page_form.get_by_role("button", name="Generate OTP").click()
                        time.sleep(2)
                    except: pass
                    self.ws_manager.latest_response = None
                    self.ws_manager.send_event_sync({
                        "type": "STATUS_MESSAGE",
                        "message": "A new OTP has been sent to your mobile number."
                    })
                    elapsed = 0
                    continue
                elif msg_type == "USER_ANSWER":
                    data = response.get("data", "")
                    return str(data)
            time.sleep(1)
            elapsed += 1

        raise TimeoutError("No OTP response received within timeout.")

    def format_date_for_injection(self, date_str, target_fmt="%d/%m/%Y"):
        if not date_str:
            return ""
        date_str = str(date_str).strip()
        input_formats = (
            "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%d-%b-%Y", "%d/%b/%Y", "%d %b %Y",
            "%d-%B-%Y", "%d/%B/%Y", "%d %B %Y",
            "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y", "%m-%d-%Y"
        )
        for fmt in input_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime(target_fmt)
            except ValueError:
                continue
        return date_str

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

    def _check_connectivity(self, max_retries=5, retry_delay=5):
        attempt = 0
        while True:
            attempt += 1
            try:
                self.log(f"Checking portal connectivity (attempt {attempt})...")
                req = urllib.request.Request(self.PORTAL_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                urllib.request.urlopen(req, timeout=10)
                self.log("✓ Portal is reachable!")
                return True
            except Exception as e:
                if attempt >= max_retries:
                    self.log(f"⚠ Could not verify portal connectivity after {attempt} attempts — proceeding anyway.")
                    return True   # don't block; let Playwright handle it
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
            self._check_connectivity()

            with sync_playwright() as playwright:
                self.log("Launching Browser...")
                launch_kwargs = {"headless": False, "slow_mo": 200}
                for chrome_path in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
                    if os.path.exists(chrome_path):
                        launch_kwargs["executable_path"] = chrome_path
                        break
                browser = playwright.chromium.launch(**launch_kwargs)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()

                # --- Login ---
                self._goto_with_retry(page, self.PORTAL_URL)
                page.get_by_role("link", name="English Version").click()
                page.get_by_role("button", name="Citizen Login").click()
                
                self.log("Entering Credentials...")
                page.get_by_role("textbox", name="User Name").fill(self.creds.get("username"))
                page.get_by_role("textbox", name="Password").fill(self.creds.get("password"))

                # --- Captcha Handling — retry loop ---
                import base64

                while True:
                    if self.ws_manager:
                        user_captcha = self._ws_prompt_captcha(page)
                    else:
                        captcha_img = page.locator("#captcha_image, img[src*='Captcha']").first
                        _bytes = captcha_img.screenshot(type="png")
                        user_captcha = input("Enter captcha: ")

                    page.get_by_role("textbox", name="Enter Captcha Code").fill(user_captcha)
                    self.log("Clicking Login...")
                    page.get_by_role("button", name="Login").click()
                    time.sleep(3)

                    # Check if login failed — inspect page HTML for known error strings
                    page_html = page.content().lower()
                    captcha_failed = (
                        "does not match the code in the image" in page_html
                        or "code you typed does not match" in page_html
                        or "invalid captcha" in page_html
                        or "captcha is incorrect" in page_html
                    )

                    if captcha_failed:
                        self.log("Wrong captcha entered. Please try again...")
                        if self.ws_manager:
                            self.ws_manager.send_event_sync({
                                "type": "STATUS_MESSAGE",
                                "message": "❌ Wrong captcha! A new captcha has been loaded — please try again."
                            })
                        # Re-fill credentials (page may have cleared them)
                        try:
                            page.get_by_role("textbox", name="User Name").fill(self.creds.get("username"))
                            page.get_by_role("textbox", name="Password").fill(self.creds.get("password"))
                        except: pass
                        continue  # retry loop
                    else:
                        # No error text found — login succeeded
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
                dob_val = (
                    self.applicant.get("dob")
                    or self.applicant.get("date_of_birth")
                    or self.applicant.get("applicant_dob")
                    or self.applicant.get("dateOfBirth")
                    or self.applicant.get("applicant_date_of_birth")
                    or self.applicant.get("DOB")
                )
                self.log(f"Raw Date of Birth from payload: '{dob_val}'")

                if dob_val:
                    fmt_dob_slash = self.format_date_for_injection(dob_val, "%d/%m/%Y")
                    fmt_dob_dash_mon = self.format_date_for_injection(dob_val, "%d-%b-%Y")
                    fmt_dob_dash_num = self.format_date_for_injection(dob_val, "%d-%m-%Y")
                    self.log(f"Formatted DOB candidates: '{fmt_dob_slash}', '{fmt_dob_dash_mon}', '{fmt_dob_dash_num}'")

                    # Step 1: Remove readonly attribute via JS immediately to prevent Playwright 30s timeouts
                    page_form.evaluate("""
                        (() => {
                            document.querySelectorAll('input[id*="citAapDOB"], input[id*="DOBInputDate"], input[id*="DOB"]').forEach(el => {
                                el.removeAttribute('readonly');
                                el.removeAttribute('disabled');
                            });
                        })()
                    """)

                    # Step 2: Instant JS evaluation + RichFaces Date object + popup collapse
                    js_res = page_form.evaluate(f"""
                        (() => {{
                            const formattedDates = ['{fmt_dob_slash}', '{fmt_dob_dash_mon}', '{fmt_dob_dash_num}', '{dob_val}'];
                            const dateToUse = formattedDates[0] || '';
                            const selectors = [
                                'statusform:citAapDOBInputDate',
                                'statusform:citAapDOB',
                                'statusform:dob',
                                'statusform:applicantDOB'
                            ];
                            let dobField = null;
                            for (const id of selectors) {{
                                const el = document.getElementById(id);
                                if (el) {{ dobField = el; break; }}
                            }}
                            if (!dobField) {{
                                dobField = document.querySelector('input[id*="citAapDOB"], input[id*="DOBInputDate"], input[id*="DOB"]');
                            }}
                            if (dobField) {{
                                dobField.removeAttribute('readonly');
                                dobField.removeAttribute('disabled');
                                dobField.value = dateToUse;
                                dobField.focus();
                                ['input', 'change', 'keydown', 'keyup', 'blur'].forEach(evtType => {{
                                    dobField.dispatchEvent(new Event(evtType, {{ bubbles: true }}));
                                }});

                                try {{
                                    const parts = dateToUse.split('/');
                                    let jsDate = null;
                                    if (parts.length === 3) {{
                                        const d = parseInt(parts[0], 10);
                                        const m = parseInt(parts[1], 10) - 1;
                                        const y = parseInt(parts[2], 10);
                                        if (!isNaN(d) && !isNaN(m) && !isNaN(y)) {{
                                            jsDate = new Date(y, m, d);
                                        }}
                                    }}

                                    if (window.RichFaces && RichFaces.$) {{
                                        const calComp = RichFaces.$('statusform:citAapDOB') || RichFaces.$('statusform:citAapDOBInputDate') || RichFaces.$(dobField.id);
                                        if (calComp) {{
                                            if (jsDate && typeof calComp.setValue === 'function') {{
                                                calComp.setValue(jsDate);
                                            }}
                                            if (typeof calComp.collapse === 'function') {{
                                                calComp.collapse();
                                            }}
                                        }}
                                    }}
                                }} catch(e) {{}}

                                // Collapse/hide any calendar popups
                                document.querySelectorAll('.rich-calendar-popup, iframe[id*="citAapDOB"]').forEach(el => {{
                                    try {{ el.style.display = 'none'; }} catch(_) {{}}
                                }});

                                return dobField.value;
                            }}
                            return null;
                        }})()
                    """)
                    self.log(f"DOB JS Injection Result: '{js_res}'")

                    # Step 3: Fast locator fallback with short 1s timeout
                    if not js_res:
                        dob_selectors = [
                            '[id="statusform:citAapDOBInputDate"]',
                            'input[id*="citAapDOBInputDate"]',
                            'input[id*="citAapDOB"]',
                        ]
                        for selector in dob_selectors:
                            try:
                                loc = page_form.locator(selector)
                                if loc.count() > 0:
                                    dob_el = loc.first
                                    dob_el.evaluate("el => { el.removeAttribute('readonly'); el.removeAttribute('disabled'); }")
                                    dob_el.fill(fmt_dob_slash, timeout=1000)
                                    dob_el.press("Escape")
                                    dob_el.press("Tab")
                                    self.log(f"Filled DOB via fallback locator: '{dob_el.input_value()}'")
                                    break
                            except Exception as e:
                                pass
                    time.sleep(1)
                else:
                    self.log("⚠ WARNING: No Date of Birth found in applicant details payload!")
                
                # --- OTP Flow — retry loop ---
                self.log("Requesting OTP from Server...")
                page_form.get_by_role("button", name="Generate OTP").click()
                time.sleep(3)

                while True:
                    if self.ws_manager:
                        user_otp = self._ws_prompt_otp(page_form)
                    else:
                        user_otp = input("Enter OTP: ")

                    page_form.locator('[id="statusform:otp_id"]').fill(user_otp)
                    page_form.get_by_role("button", name="Confirm OTP").click()
                    time.sleep(3)

                    # Check if OTP failed — inspect page HTML for known error strings
                    otp_page_html = page_form.content().lower()
                    otp_failed = (
                        "please enter valid otp" in otp_page_html
                        or "invalid otp" in otp_page_html
                        or "otp does not match" in otp_page_html
                        or "incorrect otp" in otp_page_html
                        or "otp expired" in otp_page_html
                        or "wrong otp" in otp_page_html
                    )

                    if otp_failed:
                        self.log("Wrong OTP entered. Generating a new OTP and asking user to retry...")
                        if self.ws_manager:
                            self.ws_manager.send_event_sync({
                                "type": "STATUS_MESSAGE",
                                "message": "❌ Wrong OTP! A new OTP is being sent to your mobile — please try again."
                            })
                        # Clear the OTP field and generate a fresh OTP
                        try:
                            page_form.locator('[id="statusform:otp_id"]').fill("")
                            page_form.get_by_role("button", name="Generate OTP").click()
                            time.sleep(3)
                        except: pass
                        continue  # retry loop
                    else:
                        # No error text — OTP accepted
                        break
                
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

                if self.address.get("from_date") or self.address.get("to_date"):
                    fmt_from = self.format_date_for_injection(self.address.get("from_date"), "%d/%m/%Y") if self.address.get("from_date") else ""
                    fmt_to = self.format_date_for_injection(self.address.get("to_date"), "%d/%m/%Y") if self.address.get("to_date") else ""
                    self.log(f"Injecting Address Dates: From='{fmt_from}', To='{fmt_to}'...")

                    page_form.evaluate(f"""
                        (() => {{
                            function setAddressDate(id, dateStr) {{
                                if (!dateStr) return;
                                const el = document.getElementById(id);
                                if (!el) return;
                                el.removeAttribute('readonly');
                                el.removeAttribute('disabled');
                                el.value = dateStr;
                                el.focus();
                                ['input', 'change', 'keydown', 'keyup', 'blur'].forEach(evt => {{
                                    el.dispatchEvent(new Event(evt, {{ bubbles: true }}));
                                }});
                                try {{
                                    const parts = dateStr.split('/');
                                    if (parts.length === 3) {{
                                        const d = parseInt(parts[0], 10);
                                        const m = parseInt(parts[1], 10) - 1;
                                        const y = parseInt(parts[2], 10);
                                        if (!isNaN(d) && !isNaN(m) && !isNaN(y)) {{
                                            const jsDate = new Date(y, m, d);
                                            const compId = id.replace('InputDate', '');
                                            if (window.RichFaces && RichFaces.$) {{
                                                const comp = RichFaces.$(compId) || RichFaces.$(id);
                                                if (comp && typeof comp.setValue === 'function') {{
                                                    comp.setValue(jsDate);
                                                }}
                                                if (comp && typeof comp.collapse === 'function') {{
                                                    comp.collapse();
                                                }}
                                            }}
                                        }}
                                    }}
                                }} catch(e) {{}}
                            }}

                            setAddressDate('residence:fromDateListInputDate', '{fmt_from}');
                            setAddressDate('residence:toDateListInputDate', '{fmt_to}');
                            document.querySelectorAll('.rich-calendar-popup').forEach(p => {{ try {{ p.style.display = 'none'; }} catch(_) {{}} }});
                        }})()
                    """)
                    time.sleep(1)

                if self.applicant.get("ration_card_no") and is_field_empty('[id="residence:rationCardId"]'):
                    page_form.locator('[id="residence:rationCardId"]').fill(self.applicant.get("ration_card_no"))
                    time.sleep(2) 

                self.log("Submitting Details Table...")
                page_form.get_by_role("button", name="Add").click()
                time.sleep(4)

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
                def process_document_upload(doc_label, file_source, doc_no=None):
                    if not file_source:
                        self.log(f"WARNING: No file source provided for {doc_label}. Skipping...")
                        return

                    temp_path = None
                    target_path = None

                    if isinstance(file_source, str) and (file_source.startswith("http://") or file_source.startswith("https://")):
                        try:
                            self.log(f"Fetching {doc_label} from Supabase Storage: {file_source}...")
                            req = urllib.request.Request(file_source, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                file_bytes = resp.read()

                            ext = ".pdf"
                            src_lower = file_source.lower()
                            if ".jpg" in src_lower or ".jpeg" in src_lower:
                                ext = ".jpg"
                            elif ".png" in src_lower:
                                ext = ".png"

                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
                                tf.write(file_bytes)
                                temp_path = tf.name
                            target_path = temp_path
                        except Exception as e:
                            self.log(f"WARNING: Failed to fetch {doc_label} from Supabase URL '{file_source}': {e}")
                            return
                    elif isinstance(file_source, str) and os.path.exists(file_source):
                        target_path = file_source
                    else:
                        self.log(f"WARNING: File not found or invalid source for '{doc_label}': {file_source}. Skipping...")
                        return

                    try:
                        self.log(f"Uploading {doc_label} to portal...")

                        # 1. Select document type — target exact document dropdown selectors
                        doc_type_selected = False
                        doc_selectors = [
                            'select[id*="docType"]',
                            'select[id*="DocType"]',
                            'select[name*="docType"]',
                            'select[id*="docTypeList"]',
                            '[id="statusform:docType"]',
                            '[id="statusform:docTypeList"]',
                            '[id="ss:dsctype"]',
                            '[id="ss:docType"]',
                            '[id="ss:documentType"]'
                        ]
                        for selector in doc_selectors:
                            try:
                                el = page_form.locator(selector)
                                if el.count() > 0 and el.first.is_visible():
                                    el.first.select_option(label=doc_label, timeout=2000)
                                    doc_type_selected = True
                                    self.log(f"Selected doc type '{doc_label}' via {selector}")
                                    break
                            except Exception:
                                pass

                        if not doc_type_selected:
                            # Search select elements inside upload container or page
                            try:
                                select_els = page_form.locator('select:not([disabled])').all()
                                for sel in select_els:
                                    sel_id = sel.get_attribute('id') or ''
                                    sel_name = sel.get_attribute('name') or ''
                                    if 'village' not in sel_id.lower() and 'village' not in sel_name.lower():
                                        try:
                                            sel.select_option(label=doc_label, timeout=2000)
                                            doc_type_selected = True
                                            self.log(f"Selected doc type '{doc_label}' via generic select ({sel_id})")
                                            break
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                            try:
                                enabled_combos = page_form.locator("select:not([disabled])")
                                enabled_combos.first.select_option(label=doc_label)
                                doc_type_selected = True
                                self.log("Selected doc type via first enabled combobox")
                            except Exception as e:
                                self.log(f"WARNING: Could not select doc type '{doc_label}': {e}")

                        time.sleep(5)

                        # 2. Fill document number BEFORE file upload (if needed)
                        if doc_no:
                            doc_input = page_form.locator('[id="ss:dscnum"]')
                            doc_input.click()
                            doc_input.fill(doc_no)
                            doc_input.press("Tab")
                            time.sleep(5)

                        # 3. Use set_input_files() to attach file WITHOUT opening file explorer
                        page_form.locator("input[type='file']").last.set_input_files(target_path)
                        time.sleep(8)

                        # 4. Click "Upload" button
                        self.log(f"Clicking Upload for {doc_label}...")
                        page_form.get_by_text("Upload", exact=True).click(force=True)
                        time.sleep(10)
                    finally:
                        if temp_path and os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except: pass

                # =============================================
                # STEP 1: UPLOAD PHOTO FIRST
                # =============================================
                self.log("Commencing Document Processing...")
                self.log("Step 1/3: Uploading Photo...")
                process_document_upload("Photo", self.docs.get("photo_path"))

                # =============================================
                # STEP 2: DOWNLOAD SELF DECLARATION → UPLOAD TO SUPABASE → USER SIGNS → UPLOAD
                # =============================================
                self.log("Step 2/3: Downloading Self Declaration Form...")
                self_decl_save_name = "Self_Declaration_Form_To_Sign.pdf"
                self_decl_supabase_url = ""

                try:
                    import tempfile
                    with page_form.expect_download(timeout=15000) as download_info:
                        page_form.get_by_role("link", name="Download Self declaration form").click(force=True)
                    download = download_info.value
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_decl:
                        download.save_as(tmp_decl.name)
                        tmp_decl_path = tmp_decl.name

                    try:
                        import sys
                        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                        if parent_dir not in sys.path: sys.path.append(parent_dir)
                        from supabase_db import upload_to_supabase_storage
                        with open(tmp_decl_path, "rb") as f_decl:
                            self_decl_supabase_url = upload_to_supabase_storage(f_decl.read(), self_decl_save_name, content_type="application/pdf")
                    except Exception as se:
                        self.log(f"Supabase upload error for Self-Declaration: {se}")

                    if os.path.exists(tmp_decl_path):
                        try: os.remove(tmp_decl_path)
                        except: pass

                    self.log(f"Self Declaration Form uploaded to Supabase: {self_decl_supabase_url}")
                except Exception as e:
                    self.log(f"Download failed: {e}. Proceeding.")

                # Send event to frontend to show SelfDeclarationModal with Supabase URL
                self.log("Sending Self Declaration to user for signing...")
                signed_decl_response = self._ws_prompt({
                    "type": "REQUEST_SIGNED_DECLARATION",
                    "message": "Please download the Self Declaration form, sign it, and upload the signed version.",
                    "download_path": self_decl_supabase_url or self_decl_save_name,
                    "file_path": self_decl_supabase_url or self_decl_save_name
                })

                # The response contains the file path or Supabase URL where the signed declaration was saved
                signed_decl_path = signed_decl_response.strip() if signed_decl_response else ""
                
                if signed_decl_path and signed_decl_path != "exit":
                    self.log(f"Received signed Self Declaration: {signed_decl_path}")
                    process_document_upload("Self-Declaration of Applicant", signed_decl_path)
                else:
                    self.log("WARNING: Signed Self Declaration not received. Skipping...")

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
                time.sleep(3)

                # Accept T&C and click Make Payment
                try:
                    page_form.scroll_into_view_if_needed = lambda: None  # no-op guard
                    # Scroll to bottom to reveal T&C and Make Payment button
                    page_form.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1.5)

                    # Accept Terms & Conditions checkbox
                    try:
                        tc_checkbox = page_form.locator(
                            "input[type='checkbox']"
                        ).last
                        if not tc_checkbox.is_checked():
                            tc_checkbox.check(force=True)
                            self.log("Terms & Conditions accepted.")
                        time.sleep(0.5)
                    except Exception as e:
                        self.log(f"T&C checkbox not found or already checked: {e}")

                    # Click Make Payment button
                    try:
                        page_form.get_by_role("button", name="Make Payment").click(force=True)
                        self.log("Make Payment clicked.")
                    except:
                        try:
                            page_form.locator("input[value='Make Payment'], button:has-text('Make Payment'), a:has-text('Make Payment')").first.click(force=True)
                            self.log("Make Payment clicked (fallback).")
                        except Exception as e:
                            self.log(f"Make Payment button not found: {e}")

                    time.sleep(3)

                    # Get the payment gateway URL and send to frontend to open in browser
                    try:
                        payment_url = page_form.url
                        self.log(f"Payment gateway URL: {payment_url}")
                        if self.ws_manager:
                            self.ws_manager.send_event_sync({
                                "type": "OPEN_PAYMENT_URL",
                                "url": payment_url
                            })
                    except Exception as e:
                        self.log(f"Could not get payment URL: {e}")
                except Exception as e:
                    self.log(f"Payment step error: {e}")

                self.log("User redirected to payment gateway. Backend job complete.")
                time.sleep(2)
                browser.close()

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")

if __name__ == "__main__":
    import argparse
    _defaults = {
        "credentials": {
            "username": "",
            "password": ""
        },
        "applicant_details": {
            "can_number": "",
            "aadhar_number": "",
            "dob": "",
            "ration_card_no": ""
        },
        "address_details": {
            "village": "",
            "building_no": "",
            "street_name": "",
            "pincode": "",
            "from_date": "",
            "to_date": ""
        },
        "documents": {
            "photo_path": "",
            "self_decl_path": "",
            "aadhaar_path": "",
            "address_proof_path": "",
            "address_doc_no": ""
        }
    }

    parser = argparse.ArgumentParser(description="Run TNeSevai automation")
    parser.add_argument("--payload", help="Path to JSON file")
    args = parser.parse_args()

    if args.payload and os.path.exists(args.payload):
        with open(args.payload, "r") as f: payload = json.load(f)
    else:
        try:
            import sys
            parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            if parent_dir not in sys.path: sys.path.append(parent_dir)
            from supabase_db import get_latest_application_payload
            db_payload = get_latest_application_payload()
            payload = db_payload if db_payload else _defaults
        except Exception:
            payload = _defaults

    bot = TNeSevaiBackendAgent(payload)
    bot.run()