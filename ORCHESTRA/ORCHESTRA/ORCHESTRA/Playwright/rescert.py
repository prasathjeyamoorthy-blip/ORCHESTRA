import os
import sys
import re
import time
import json
import asyncio
import urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright  # type: ignore


def is_deployed_environment() -> bool:
    """Check if code is running in a deployed/cloud environment (Render, Docker, AWS, etc.)."""
    return bool(
        os.getenv("RENDER")
        or os.getenv("IS_PULL_REQUEST")
        or os.getenv("AWS_EXECUTION_ENV")
        or os.getenv("ECS_CONTAINER_METADATA_URI")
        or os.getenv("ENVIRONMENT", "").lower() in ("production", "prod", "staging", "deployed")
        or os.getenv("NODE_ENV", "").lower() == "production"
        or os.path.exists("/.dockerenv")
    )


def has_gui_display() -> bool:
    """Check if a graphical display environment (X11, Wayland, Windows, macOS) is available."""
    if os.name == "nt" or getattr(sys, "platform", "") == "darwin":
        return True
    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


def should_run_headless() -> bool:
    """
    Decide whether browser automation should run headless or headed:
    1. Explicit HEADLESS environment variable takes precedence if set ('true'/'1' or 'false'/'0').
    2. Deployed environments (Render, Docker, AWS, production) run headless (True).
    3. Headless servers with no graphical display available run headless (True).
    4. Local development with display available runs headed (False) with visible UI.
    """
    headless_env = os.getenv("HEADLESS")
    if headless_env is not None and headless_env.strip() != "":
        return headless_env.strip().lower() in ("true", "1", "yes")

    if is_deployed_environment():
        return True

    if not has_gui_display():
        return True

    return False


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

    def _generate_auto_signed_declaration(self, base_pdf_path=None) -> str:
        """Stamp a digital signature onto the Self Declaration form for automated/dev flows."""
        out_dir = os.path.join(os.path.dirname(__file__), "uploaded_documents")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "Signed_Self_Declaration_Auto.jpg")
        out_pdf  = os.path.join(out_dir, "Signed_Self_Declaration_Auto.pdf")

        applicant_name = (
            self.applicant.get("applicant_name") or
            self.applicant.get("name") or
            self.data.get("applicant_details", {}).get("applicant_name") or
            self.data.get("applicant_details", {}).get("name") or
            "Applicant"
        )

        candidates = [
            base_pdf_path,
            os.path.join(os.path.dirname(__file__), "Self_Declaration_Form_To_Sign.pdf"),
            os.path.join(os.path.dirname(__file__), "Self_Declaration_Form_For_User.pdf")
        ]
        src_pdf = None
        for c in candidates:
            if c and os.path.exists(c):
                src_pdf = c
                break

        try:
            from PIL import Image, ImageDraw
            import pypdf, io

            im = None
            if src_pdf:
                try:
                    reader = pypdf.PdfReader(src_pdf)
                    if reader.pages and len(reader.pages[0].images) > 0:
                        img_data = reader.pages[0].images[0].data
                        im = Image.open(io.BytesIO(img_data)).convert("RGB")
                except Exception:
                    pass

            if im is None:
                im = Image.new("RGB", (1191, 1611), color=(255, 255, 255))
                draw = ImageDraw.Draw(im)
                draw.text((100, 100), "GOVERNMENT OF TAMIL NADU - SELF DECLARATION", fill=(0, 0, 0))
                draw.text((100, 200), f"I, {applicant_name}, hereby declare that the particulars given are true.", fill=(0, 0, 0))
            else:
                draw = ImageDraw.Draw(im)

            sig_x = int(im.width * 0.68)
            sig_y = int(im.height * 0.88)
            draw.text((sig_x, sig_y), f"Digitally Signed: {applicant_name}", fill=(10, 20, 110))
            draw.line([(sig_x, sig_y + 25), (sig_x + 220, sig_y + 25)], fill=(10, 20, 110), width=2)

            # Save JPEG under 190 KB
            im.save(out_file, format="JPEG", quality=85, optimize=True)
            if os.path.getsize(out_file) > 190 * 1024:
                im.save(out_file, format="JPEG", quality=65, optimize=True)

            # Save PDF under 190 KB
            im.save(out_pdf, format="PDF", quality=85, optimize=True)
            if os.path.getsize(out_pdf) > 190 * 1024:
                im.save(out_pdf, format="PDF", quality=65, optimize=True)

            chosen_path = out_pdf if (os.path.exists(out_pdf) and os.path.getsize(out_pdf) <= 195 * 1024) else out_file
            self.log(f"✓ Created auto-signed Self Declaration ({os.path.getsize(chosen_path) / 1024:.1f} KB): {chosen_path}")
            return chosen_path
        except Exception as e:
            self.log(f"Auto-sign generation error: {e}")
            return src_pdf or out_file or ""

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
            dropdown.wait_for(state="visible", timeout=8000)
            
            try:
                dropdown.select_option(label=value, timeout=3000)
                time.sleep(0.5)
                self.log(f"✓ Selected {field_name}: {value}")
                return True
            except: pass
            
            try:
                options = dropdown.locator('option').all_text_contents()
                for option in options:
                    if option.strip().upper() == "SELECT": continue
                    if value.lower() in option.lower() or option.lower() in value.lower():
                        dropdown.select_option(label=option, timeout=3000)
                        time.sleep(0.5)
                        self.log(f"✓ Selected {field_name}: {option} (matched with {value})")
                        return True
            except: pass
            
            try:
                dropdown.select_option(value=value, timeout=3000)
                time.sleep(0.5)
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
                            dropdown.select_option(value=option_value, timeout=3000)
                            time.sleep(0.5)
                            self.log(f"✓ Selected {field_name}: {option_text} (first available option)")
                            return True
            except: pass
            
            self.log(f"✗ Note: Could not select {field_name} with value '{value}'")
            return False
        except Exception as e:
            self.log(f"✗ Note selecting {field_name}: {str(e)}")
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
                is_headless = should_run_headless()
                mode_label = "headless" if is_headless else "headed (visible UI)"
                self.log(f"Launching Browser ({mode_label})...")
                launch_kwargs = {
                    "headless": is_headless,
                    "slow_mo": 200 if not is_headless else 0,
                    "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                }
                for chrome_path in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
                    if os.path.exists(chrome_path):
                        launch_kwargs["executable_path"] = chrome_path
                        break
                try:
                    browser = playwright.chromium.launch(**launch_kwargs)
                except Exception as launch_err:
                    self.log(f"Headed browser launch failed ({launch_err}). Falling back to headless mode...")
                    launch_kwargs["headless"] = True
                    launch_kwargs["slow_mo"] = 0
                    browser = playwright.chromium.launch(**launch_kwargs)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()

                # Apply stealth patches — hides Playwright automation signals from bot-detection
                try:
                    from playwright_stealth import stealth_sync
                    stealth_sync(page)
                    self.log("Stealth applied to browser page.")
                except Exception as se:
                    self.log(f"Stealth not applied: {se}")

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
                
                # Wait for search results table and radio button
                try:
                    page_form.wait_for_selector('input[type="radio"], [id*="citRadio"], tr.rich-table-row', timeout=12000)
                    time.sleep(2)
                except Exception:
                    time.sleep(4)
                
                # Check radio button with multiple fallback selectors
                radio_checked = False
                for r_sel in [
                    'input[type="radio"]',
                    'input[name*="citRadio"]',
                    '[id*="citRadio"]',
                    'tr.rich-table-row input[type="radio"]',
                    'input[name="can_radio"]'
                ]:
                    try:
                        r_loc = page_form.locator(r_sel)
                        if r_loc.count() > 0:
                            r_loc.first.check(force=True)
                            self.log(f"✓ Checked CAN radio button via {r_sel}")
                            radio_checked = True
                            break
                    except Exception:
                        pass

                if not radio_checked:
                    try:
                        page_form.get_by_label("").first.check(force=True)
                        self.log("✓ Checked CAN radio button via empty label fallback")
                    except Exception:
                        pass

                time.sleep(2)
                
                self.log("Typing Aadhaar Number securely...")
                aadhar_input = page_form.locator('[id="statusform:citAadharNo"]')
                aadhar_input.click()
                
                try: aadhar_input.press_sequentially(self.applicant.get("aadhar_number"), delay=50)
                except AttributeError: aadhar_input.type(self.applicant.get("aadhar_number"), delay=50)
                
                aadhar_input.press("Tab")
                time.sleep(2)
                
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
                
                # Wait for navigation to residence certificate form page
                try:
                    page_form.wait_for_url(lambda u: "residence" in u.lower() or "rev" in u.lower(), timeout=25000)
                except Exception:
                    pass
                
                try:
                    page_form.wait_for_load_state("domcontentloaded", timeout=20000)
                    page_form.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                
                # Ensure residence form container is loaded
                try:
                    page_form.wait_for_selector('form[id*="residence"], [id*="residence"], [id*="buildForList"]', timeout=20000)
                    self.log("✓ Residence certificate form loaded.")
                except Exception:
                    self.log("Note: Proceeding to form fields...")
                
                time.sleep(3)

                # --- Fill Form Details ---
                self.log("Filling Form Details...")

                def is_valid_addr(val):
                    if not val: return False
                    v_s = str(val).strip().lower()
                    if not v_s: return False
                    app_n = (self.applicant.get("name") or "").strip().lower()
                    f_n = (self.applicant.get("father_name") or "").strip().lower()
                    if app_n and v_s == app_n: return False
                    if f_n and v_s == f_n: return False
                    if any(bad in v_s for bad in ["c/o", "s/o", "d/o", "w/o"]): return False
                    return True

                applicant_name = (self.applicant.get("name") or "").replace("'", "\\'")
                father_name = (self.applicant.get("father_name") or "").replace("'", "\\'")
                ration_card_no = (self.applicant.get("ration_card_no") or "").replace("'", "\\'")
                bldg_val = self.address.get("building_no") or self.address.get("door_no") or ""
                street_val = self.address.get("street_name") or self.address.get("area") or ""
                if not is_valid_addr(bldg_val): bldg_val = ""
                if not is_valid_addr(street_val): street_val = ""
                st_to_fill = street_val or bldg_val
                pincode_val = self.address.get("pincode") or ""
                revenue_village_value = (self.address.get("area") or self.address.get("village") or "").replace("'", "\\'")
                fmt_from = self.format_date_for_injection(self.address.get("from_date"), "%d/%m/%Y") if self.address.get("from_date") else ""
                fmt_to = self.format_date_for_injection(self.address.get("to_date"), "%d/%m/%Y") if self.address.get("to_date") else ""

                # Wait up to 6 seconds for village dropdown to initialize if present
                try:
                    page_form.wait_for_selector('[id="residence:cRvillageListId"]', timeout=6000)
                except Exception:
                    pass

                # Fast, non-blocking in-browser execution: skips CAN-locked readonly fields and fills editable address fields
                page_form.evaluate(f"""
                    (() => {{
                        function fillIfEditable(id, val) {{
                            if (!val) return;
                            const el = document.getElementById(id);
                            if (el && !el.disabled && !el.readOnly && !el.hasAttribute('readonly')) {{
                                if (!el.value || el.value.trim() === '') {{
                                    el.value = val;
                                    ['input', 'change', 'blur'].forEach(evt => el.dispatchEvent(new Event(evt, {{ bubbles: true }})));
                                }}
                            }}
                        }}

                        // Fill demographic fields if editable (unlocked)
                        fillIfEditable('residence:applicantName', '{applicant_name}');
                        fillIfEditable('residence:fatherName', '{father_name}');
                        fillIfEditable('residence:rationCardId', '{ration_card_no}');

                        // Fill address fields if editable and empty
                        fillIfEditable('residence:buildForList', '{bldg_val}');
                        fillIfEditable('residence:streetForList', '{st_to_fill}');
                        fillIfEditable('residence:pinForList', '{pincode_val}');

                        // Fast Revenue Village selection if dropdown is present and on "SELECT"
                        const vSel = document.getElementById('residence:cRvillageListId');
                        if (vSel && !vSel.disabled && vSel.options && vSel.options.length > 1) {{
                            const curVal = (vSel.value || '').trim();
                            const curText = (vSel.options[vSel.selectedIndex]?.text || '').trim().toUpperCase();
                            if (!curVal || curText === 'SELECT' || curVal === '0') {{
                                const target = '{revenue_village_value}'.toLowerCase();
                                let matched = false;
                                if (target) {{
                                    for (let i = 0; i < vSel.options.length; i++) {{
                                        const optText = (vSel.options[i].text || '').toLowerCase();
                                        if (optText.toUpperCase() !== 'SELECT' && (optText.includes(target) || target.includes(optText))) {{
                                            vSel.selectedIndex = i;
                                            matched = true;
                                            break;
                                        }}
                                    }}
                                }}
                                if (!matched && vSel.options.length > 1) {{
                                    for (let i = 1; i < vSel.options.length; i++) {{
                                        if ((vSel.options[i].text || '').trim().toUpperCase() !== 'SELECT') {{
                                            vSel.selectedIndex = i;
                                            break;
                                        }}
                                    }}
                                }}
                                vSel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}

                        // Inject Address Dates
                        function setAddressDate(id, dateStr) {{
                            if (!dateStr) return;
                            const el = document.getElementById(id);
                            if (!el) return;
                            el.removeAttribute('readonly');
                            el.removeAttribute('disabled');
                            el.value = dateStr;
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

                # Fallback: if ration card number is still empty, fill it via locator
                if self.applicant.get("ration_card_no"):
                    try:
                        rc_input = page_form.locator('[id="residence:rationCardId"]')
                        if rc_input.count() > 0 and rc_input.first.is_visible() and not rc_input.first.input_value():
                            rc_input.first.fill(str(self.applicant.get("ration_card_no")))
                            time.sleep(0.5)
                    except Exception:
                        pass

                self.log("Submitting Details Table (Adding residency period)...")
                add_clicked = False
                for add_sel in [
                    'button:has-text("Add")',
                    'input[value="Add"]',
                    '[id*="addBtn"]',
                    '[id*="Add"]'
                ]:
                    try:
                        btn = page_form.locator(add_sel).first
                        if btn.is_visible():
                            btn.click()
                            add_clicked = True
                            self.log(f"Clicked Add button via {add_sel}")
                            break
                    except Exception:
                        pass
                
                if not add_clicked:
                    try:
                        page_form.get_by_role("button", name="Add").click()
                        add_clicked = True
                    except Exception:
                        pass
                
                # Verify that residency row appears in table (wait up to 10s for RichFaces AJAX)
                table_row_added = False
                for _ in range(10):
                    time.sleep(1)
                    try:
                        row_count = page_form.evaluate("""() => {
                            const rows = document.querySelectorAll('tr.rich-table-row, table[id*="residence"] tbody tr, table.rich-table tbody tr');
                            return rows.length;
                        }""")
                        if row_count and row_count > 0:
                            table_row_added = True
                            self.log(f"✓ Residency details row verified in table ({row_count} rows).")
                            break
                    except Exception:
                        pass
                
                if not table_row_added:
                    self.log("Residency row not yet verified; retrying Add button click once...")
                    try:
                        page_form.locator('input[value="Add"], button:has-text("Add")').first.click(force=True)
                    except Exception:
                        pass
                    time.sleep(3)

                # Dialog Handler to catch and log any alert messages from portal
                def safe_dialog_handler(dialog):
                    try:
                        self.log(f"Portal dialog alert: {dialog.message}")
                        dialog.accept()
                    except Exception:
                        pass 
                page_form.on("dialog", safe_dialog_handler) 

                self.log("Submitting Form to navigate to Document Upload...")
                submit_clicked = False
                for sub_sel in [
                    'input[value="Submit"]',
                    'button:has-text("Submit")',
                    '[id*="submit"]',
                    '[id*="Submit"]'
                ]:
                    try:
                        s_btn = page_form.locator(sub_sel).first
                        if s_btn.is_visible():
                            s_btn.click()
                            submit_clicked = True
                            self.log(f"Clicked Submit button via {sub_sel}")
                            break
                    except Exception:
                        pass

                if not submit_clicked:
                    try:
                        page_form.get_by_role("button", name="Submit").click()
                    except Exception:
                        pass

                # CRITICAL: Wait for portal to actually navigate away from residence.xhtml to uploadDocs.xhtml
                self.log("Waiting for portal to navigate to Document Upload page...")
                navigated_to_upload = False
                try:
                    page_form.wait_for_url(lambda u: "upload" in u.lower() or "doc" in u.lower(), timeout=35000)
                    navigated_to_upload = True
                    self.log(f"✓ Navigated to Document Upload page: {page_form.url}")
                except Exception as ne:
                    self.log(f"Navigation to uploadDocs wait note: {ne}")

                try:
                    page_form.wait_for_load_state("domcontentloaded", timeout=15000)
                    page_form.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass

                # Wait for upload controls to be present
                try:
                    page_form.wait_for_selector("input[type='file'], [id*='dsctype'], [id*='upload'], select", timeout=25000)
                    self.log("✓ Document upload controls ready on page.")
                except Exception as se:
                    self.log(f"Upload controls wait note: {se}")

                time.sleep(3) 

                # --- TABLE PARSER HELPER ---
                def get_uploaded_docs_from_table():
                    """Extract uploaded document rows directly from the portal's uploaded documents table."""
                    try:
                        return page_form.evaluate("""() => {
                            const tables = Array.from(document.querySelectorAll('table'));
                            const docTable = tables.find(t => {
                                const text = (t.innerText || '').toLowerCase();
                                return text.includes('document name') && text.includes('file name');
                            });
                            if (!docTable) return [];
                            const rows = Array.from(docTable.querySelectorAll('tr'));
                            const headerIdx = rows.findIndex(r => {
                                const txt = (r.innerText || '').toLowerCase();
                                return txt.includes('document name') && txt.includes('file name');
                            });
                            if (headerIdx === -1) return [];
                            const dataRows = rows.slice(headerIdx + 1);
                            return dataRows.map(r => {
                                const cells = Array.from(r.querySelectorAll('td')).map(c => (c.innerText || '').trim());
                                return {
                                    serialNo: cells[0] || '',
                                    docName: cells[1] || '',
                                    docNo: cells[2] || '',
                                    fileName: cells[3] || '',
                                    raw: (r.innerText || '').trim()
                                };
                            }).filter(r => r.docName.length > 0 || r.fileName.length > 0);
                        }""")
                    except Exception as ge:
                        self.log(f"Table inspection note: {ge}")
                        return []

                # --- DOCUMENT UPLOAD HELPER ---
                def process_document_upload(doc_label, file_source, doc_no=None):
                    # Check for applicant's uploaded signed declaration if source not explicitly passed
                    if not file_source:
                        if "Self" in doc_label or "Declaration" in doc_label:
                            for p in [
                                os.path.join(os.path.dirname(__file__), "uploaded_documents", "Signed_Self_Declaration.pdf"),
                                os.path.join(os.path.dirname(__file__), "Signed_Self_Declaration.pdf"),
                            ]:
                                if os.path.exists(p):
                                    file_source = p
                                    break

                    if not file_source:
                        self.log(f"WARNING: No file source provided for {doc_label}. Skipping...")
                        return

                    temp_path = None
                    target_path = None

                    # ── Fetch file to local temp path ──────────────────────────────────────
                    if isinstance(file_source, str) and (file_source.startswith("http://") or file_source.startswith("https://")):
                        try:
                            self.log(f"Fetching {doc_label} from Supabase Storage: {file_source}...")
                            req = urllib.request.Request(file_source, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                file_bytes = resp.read()
                            ext = ".pdf"
                            src_lower = file_source.lower()
                            if ".jpg" in src_lower or ".jpeg" in src_lower: ext = ".jpg"
                            elif ".png" in src_lower: ext = ".png"
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
                                tf.write(file_bytes)
                                temp_path = tf.name
                            target_path = temp_path
                        except Exception as e:
                            self.log(f"WARNING: Failed to fetch {doc_label} from Supabase URL: {e}")
                            return
                    elif isinstance(file_source, str):
                        candidate_paths = [
                            file_source,
                            os.path.abspath(file_source),
                            os.path.join(os.path.dirname(__file__), "uploaded_documents", os.path.basename(file_source)),
                            os.path.join(os.path.dirname(__file__), "..", "..", "DocumentUploadAgent", "uploads", os.path.basename(file_source)),
                            os.path.join(os.path.dirname(__file__), "..", "..", "DocumentUploadAgent", file_source),
                            os.path.join(os.path.dirname(__file__), "uploads", os.path.basename(file_source)),
                            os.path.join(os.path.dirname(__file__), os.path.basename(file_source)),
                            os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "public", "dev_docs", os.path.basename(file_source)),
                            os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "dist", "dev_docs", os.path.basename(file_source)),
                        ]
                        for cp in candidate_paths:
                            if os.path.exists(cp):
                                target_path = os.path.abspath(cp)
                                break
                        if not target_path:
                            self.log(f"WARNING: File not found for '{doc_label}': {file_source}. Skipping...")
                            return
                    else:
                        self.log(f"WARNING: Invalid file source for '{doc_label}': {file_source}. Skipping...")
                        return

                    # Optimize file size to strictly comply with portal limits:
                    # - Photo <= 50 KB (JPEG)
                    # - Documents <= 200 KB (PDF / JPEG)
                    try:
                        file_sz = os.path.getsize(target_path)
                        is_pdf = target_path.lower().endswith(".pdf") or (os.path.exists(target_path) and open(target_path, "rb").read(5).startswith(b"%PDF-"))

                        if doc_label == "Photo" and (file_sz > 48 * 1024 or is_pdf or not target_path.lower().endswith((".jpg", ".jpeg"))):
                            self.log(f"Preparing photo ({file_sz / 1024:.1f} KB, is_pdf={is_pdf}) for portal...")
                            from PIL import Image
                            import tempfile
                            im = None
                            if is_pdf:
                                try:
                                    import pypdf
                                    from io import BytesIO
                                    with open(target_path, "rb") as pf:
                                        reader = pypdf.PdfReader(BytesIO(pf.read()))
                                        if reader.pages and len(reader.pages[0].images) > 0:
                                            im = Image.open(BytesIO(reader.pages[0].images[0].data))
                                except Exception:
                                    pass
                            else:
                                im = Image.open(target_path)

                            if im:
                                with im:
                                    im_rgb = im.convert("RGB")
                                    im_rgb.thumbnail((400, 500))
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf_opt:
                                        quality = 85
                                        while quality >= 20:
                                            tf_opt.seek(0)
                                            tf_opt.truncate()
                                            im_rgb.save(tf_opt, format="JPEG", quality=quality, optimize=True)
                                            if tf_opt.tell() <= 48 * 1024:
                                                break
                                            quality -= 10
                                        temp_path = tf_opt.name
                                        target_path = temp_path
                                self.log(f"✓ Photo prepared as JPEG ({os.path.getsize(target_path) / 1024:.1f} KB)")

                        elif doc_label != "Photo" and file_sz > 195 * 1024:
                            self.log(f"Compressing {doc_label} ({file_sz / 1024:.1f} KB) to comply with portal 200KB limit...")
                            from PIL import Image
                            import tempfile
                            im_doc = None
                            if is_pdf:
                                try:
                                    import pypdf
                                    from io import BytesIO
                                    with open(target_path, "rb") as pf:
                                        reader = pypdf.PdfReader(BytesIO(pf.read()))
                                        if reader.pages and len(reader.pages[0].images) > 0:
                                            im_doc = Image.open(BytesIO(reader.pages[0].images[0].data))
                                except Exception: pass
                            else:
                                try:
                                    im_doc = Image.open(target_path)
                                except Exception: pass

                            if im_doc:
                                with im_doc:
                                    im_rgb = im_doc.convert("RGB")
                                    im_rgb.thumbnail((1200, 1600))
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf_opt:
                                        q = 80
                                        while q >= 25:
                                            tf_opt.seek(0)
                                            tf_opt.truncate()
                                            im_rgb.save(tf_opt, format="JPEG", quality=q, optimize=True)
                                            if tf_opt.tell() <= 190 * 1024:
                                                break
                                            q -= 10
                                        temp_path = tf_opt.name
                                        target_path = temp_path
                                self.log(f"✓ {doc_label} compressed to {os.path.getsize(target_path) / 1024:.1f} KB")
                    except Exception as sz_err:
                        self.log(f"Document optimization note: {sz_err}")

                    try:
                        self.log(f"Uploading {doc_label} to portal...")

                        # STEP 1 — Select document type from dropdown
                        doc_type_selected = False
                        doc_selectors = [
                            '[id="ss:dsctype"]',
                            'select[id*="dsctype"]',
                            'select[id*="docType"]',
                            'select[id*="DocType"]',
                            'select[name*="docType"]',
                            'select[id*="docTypeList"]',
                            '[id="statusform:docType"]',
                            '[id="statusform:docTypeList"]',
                            '[id="ss:documentType"]'
                        ]
                        for selector in doc_selectors:
                            try:
                                el = page_form.locator(selector)
                                if el.count() > 0 and el.first.is_visible():
                                    try:
                                        res = el.first.evaluate("""(sel, targetLabel) => {
                                            const clean = s => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                                            const target = clean(targetLabel);
                                            const opts = Array.from(sel.options).map((o, i) => ({
                                                idx: i,
                                                text: (o.text || '').trim(),
                                                cleanText: clean(o.text),
                                                value: o.value
                                            }));

                                            // 1. Exact clean match
                                            for (const opt of opts) {
                                                if (opt.cleanText && opt.cleanText === target) return opt;
                                            }
                                            // 2. Substring match
                                            for (const opt of opts) {
                                                if (opt.cleanText && (opt.cleanText.includes(target) || target.includes(opt.cleanText))) return opt;
                                            }
                                            // 3. Keyword match
                                            if (target.includes('self') || target.includes('decl')) {
                                                for (const opt of opts) {
                                                    if (opt.cleanText.includes('self') || opt.cleanText.includes('decl')) return opt;
                                                }
                                                if (sel.options.length >= 4) return opts[3];
                                            }
                                            if (target.includes('photo')) {
                                                for (const opt of opts) {
                                                    if (opt.cleanText.includes('photo')) return opt;
                                                }
                                                if (sel.options.length >= 2) return opts[1];
                                            }
                                            if (target.includes('address') || target.includes('proof')) {
                                                for (const opt of opts) {
                                                    if (opt.cleanText.includes('address') || opt.cleanText.includes('proof')) return opt;
                                                }
                                                if (sel.options.length >= 3) return opts[2];
                                            }
                                            return null;
                                        }""", doc_label)

                                        if res and "idx" in res:
                                            matched_idx = res["idx"]
                                            matched_name = res.get("text", "")
                                            el.first.select_option(index=matched_idx)
                                            el.first.evaluate("""sel => {
                                                sel.dispatchEvent(new Event('input', { bubbles: true }));
                                                sel.dispatchEvent(new Event('change', { bubbles: true }));
                                                if (sel.onchange) {
                                                    try { sel.onchange(); } catch(e) {}
                                                }
                                            }""")
                                            doc_type_selected = True
                                            self.log(f"Selected doc type '{matched_name}' (idx {matched_idx}) via {selector}")
                                            break
                                    except Exception as sel_e:
                                        self.log(f"Select option note: {sel_e}")
                            except Exception:
                                pass

                        if not doc_type_selected:
                            # Generic fallback — find first non-address select
                            ignore_kw = ['village', 'district', 'state', 'taluk', 'community', 'religion', 'gender']
                            for sel in page_form.locator('select:not([disabled])').all():
                                sel_id = (sel.get_attribute('id') or '').lower()
                                sel_name = (sel.get_attribute('name') or '').lower()
                                if not any(kw in sel_id or kw in sel_name for kw in ignore_kw):
                                    try:
                                        sel.select_option(label=doc_label, timeout=2000)
                                        doc_type_selected = True
                                        self.log(f"Selected doc type '{doc_label}' via generic select ({sel_id})")
                                        break
                                    except Exception:
                                        pass

                        # Allow RichFaces AJAX to finish updating DOM after dropdown change
                        try:
                            page_form.wait_for_load_state("networkidle", timeout=3000)
                        except Exception:
                            pass
                        time.sleep(2.5)

                        # STEP 2 — Fill document number (if provided or required for Current Address Proof)
                        actual_doc_no = doc_no
                        if not actual_doc_no and "Address" in doc_label:
                            actual_doc_no = (
                                self.applicant.get("dl_number") or
                                self.applicant.get("driving_license_number") or
                                self.applicant.get("aadhaar_number") or
                                ""
                            )

                        if actual_doc_no:
                            try:
                                doc_input = page_form.locator('[id="ss:dscnum"]')
                                if doc_input.count() > 0 and doc_input.first.is_visible():
                                    doc_input.click()
                                    doc_input.fill(str(actual_doc_no))
                                    doc_input.press("Tab")
                                    time.sleep(1.5)
                                    self.log(f"Filled document number: {actual_doc_no}")
                            except Exception as de:
                                self.log(f"WARNING: Could not fill document number: {de}")
                        else:
                            # Clear document number field if not applicable to this document
                            try:
                                doc_input = page_form.locator('[id="ss:dscnum"]')
                                if doc_input.count() > 0 and doc_input.first.is_visible() and doc_input.first.input_value():
                                    doc_input.first.fill("")
                            except Exception:
                                pass

                        # STEP 3 — Use set_input_files() to attach file WITHOUT opening native file dialog
                        try:
                            self.log(f"Attaching file for {doc_label}: {target_path}...")
                            file_input = page_form.locator("input[type='file']")
                            file_input.wait_for(state="attached", timeout=10000)
                            file_input.last.set_input_files(target_path)
                            self.log(f"File attached for {doc_label}: {os.path.basename(target_path)}")
                            time.sleep(3.5)
                        except Exception as fe:
                            self.log(f"WARNING: Failed to attach file for {doc_label}: {fe}")

                        # STEP 4 — Click "Upload" button (RichFaces exact text / button / container)
                        self.log(f"Clicking Upload for {doc_label}...")
                        upload_done = False
                        try:
                            up_btn = page_form.get_by_text("Upload", exact=True)
                            if up_btn.count() > 0 and up_btn.first.is_visible():
                                up_btn.first.click(force=True)
                                upload_done = True
                                self.log(f"Clicked Upload exact text for {doc_label}")
                        except Exception:
                            pass

                        if not upload_done:
                            for sel in [
                                ".rich-fileupload-button-upload",
                                "a.rich-fileupload-btn-cnt",
                                "input[value='Upload']",
                                "button:has-text('Upload')",
                                "[id*='uploadControl'] [id*='upload']"
                            ]:
                                try:
                                    el = page_form.locator(sel)
                                    if el.count() > 0 and el.first.is_visible():
                                        el.first.click(force=True)
                                        upload_done = True
                                        self.log(f"Clicked Upload via {sel} for {doc_label}")
                                        break
                                except Exception:
                                    pass

                        if not upload_done:
                            try:
                                clicked = page_form.evaluate("""() => {
                                    const btns = Array.from(document.querySelectorAll('a, button, input[type="button"], div.rich-fileupload-button-upload, span.rich-fileupload-btn-cnt'));
                                    const b = btns.find(x => (x.innerText || x.value || '').trim().toLowerCase() === 'upload');
                                    if (b) { b.click(); return true; }
                                    return false;
                                }""")
                                if clicked:
                                    upload_done = True
                                    self.log(f"Clicked Upload via JS fallback for {doc_label}")
                            except Exception:
                                pass

                        # Poll uploaded documents table up to 15 seconds to verify document appeared
                        doc_in_table = False
                        target_kw = "photo" if "photo" in doc_label.lower() else ("self" if "self" in doc_label.lower() or "declaration" in doc_label.lower() else "address")
                        for poll_i in range(15):
                            time.sleep(1)
                            docs_in_table = get_uploaded_docs_from_table()
                            for r in docs_in_table:
                                r_text = (r.get("docName", "") + " " + r.get("fileName", "")).lower()
                                if target_kw in r_text:
                                    doc_in_table = True
                                    break
                            if doc_in_table:
                                break

                            if poll_i == 5 and not doc_in_table:
                                try:
                                    up_btn = page_form.locator(".rich-fileupload-button-upload, a.rich-fileupload-btn-cnt, input[value='Upload'], button:has-text('Upload'), text='Upload'").first
                                    if up_btn.is_visible():
                                        up_btn.click(force=True)
                                        self.log(f"Re-clicked Upload button for {doc_label}")
                                except Exception:
                                    pass

                        if doc_in_table:
                            self.log(f"✓ Confirmed {doc_label} is in the portal documents table!")
                        else:
                            self.log(f"⚠️ Note: {doc_label} upload completed, verifying rows...")

                    finally:
                        if temp_path and os.path.exists(temp_path):
                            try: os.remove(temp_path)
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
                local_self_decl_path = os.path.join(os.path.dirname(__file__), self_decl_save_name)
                self_decl_supabase_url = ""

                try:
                    download = None
                    try:
                        dl_link = page_form.locator("a:has-text('Download Self declaration form'), a:has-text('Self declaration'), [id*='selfDeclaration'], text='Download Self declaration form'").first
                        try:
                            dl_link.wait_for(state="visible", timeout=10000)
                        except Exception:
                            pass
                        with page_form.expect_download(timeout=12000) as download_info:
                            if dl_link.count() > 0:
                                dl_link.click(force=True)
                        download = download_info.value
                    except Exception as de:
                        self.log(f"Link click download note: {de}")

                    if download:
                        download.save_as(local_self_decl_path)
                        self.log(f"✓ Saved Self Declaration locally: {local_self_decl_path}")
                        try:
                            import sys
                            parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                            if parent_dir not in sys.path: sys.path.append(parent_dir)
                            from supabase_db import upload_to_supabase_storage
                            with open(local_self_decl_path, "rb") as f_decl:
                                self_decl_supabase_url = upload_to_supabase_storage(f_decl.read(), self_decl_save_name, content_type="application/pdf")
                        except Exception as se:
                            self.log(f"Supabase upload error for Self-Declaration: {se}")

                        self.log(f"Self Declaration Form uploaded to Supabase: {self_decl_supabase_url}")
                except Exception as e:
                    self.log(f"Download note: {e}. Proceeding.")

                # Send event to frontend to show SelfDeclarationModal and wait for manual user upload
                self.log("Waiting for applicant to download, sign, and upload Self-Declaration form...")
                if self.ws_manager:
                    self.ws_manager.send_event_sync({
                        "type": "STATUS_MESSAGE",
                        "message": "Self-Declaration form downloaded. Please sign and upload it in the modal."
                    })

                signed_decl_response = None
                try:
                    signed_decl_response = self._ws_prompt({
                        "type": "REQUEST_SIGNED_DECLARATION",
                        "message": "Please download the Self Declaration form, sign it, and upload the signed version.",
                        "download_path": self_decl_supabase_url or self_decl_save_name,
                        "file_path": self_decl_supabase_url or self_decl_save_name
                    }, timeout=300)
                except Exception as wse:
                    self.log(f"Self Declaration prompt wait ended: {wse}")

                signed_decl_path = str(signed_decl_response).strip() if signed_decl_response else ""

                if signed_decl_path.lower() in ("exit", "cancel"):
                    self.log("User cancelled Self Declaration upload. Aborting.")
                    raise RuntimeError("Self Declaration submission cancelled by user.")

                # If user explicitly opted for auto-sign in the modal
                if signed_decl_path.lower() in ("autosign", "auto-sign", "auto"):
                    self.log("Applicant explicitly requested Auto-Sign. Applying digital signature...")
                    signed_decl_path = self._generate_auto_signed_declaration(local_self_decl_path)
                elif not signed_decl_path:
                    self.log("WARNING: No signed declaration received within timeout. Cannot proceed without applicant's signed declaration.")
                    raise RuntimeError("Signed Self-Declaration form is required to proceed with submission.")
                else:
                    self.log(f"✓ Manual signed Self Declaration received from applicant: {signed_decl_path}")

                if signed_decl_path and (os.path.exists(signed_decl_path) or signed_decl_path.startswith("http")):
                    self.log(f"Uploading Self Declaration: {signed_decl_path}")
                    process_document_upload("Self-Declaration of Applicant", signed_decl_path)
                else:
                    self.log("WARNING: Could not prepare Self Declaration.")

                # =============================================
                # STEP 3: UPLOAD ADDRESS PROOF WITH DOC NUMBER
                # =============================================
                self.log("Step 3/3: Uploading Current Address Proof...")
                process_document_upload(
                    "Current Address Proof",
                    self.docs.get("address_proof_path"),
                    self.docs.get("address_doc_no")
                )

                # =============================================
                # POST-UPLOAD VERIFICATION LOOP
                # Verify that ALL 3 mandatory documents are in the portal's uploaded documents table.
                # If any mandatory document is missing, re-upload it immediately.
                # =============================================
                self.log("Verifying all mandatory documents in portal table...")
                time.sleep(3)
                try:
                    docs_in_table = get_uploaded_docs_from_table()
                    tbl_summary = [f"{r.get('serialNo')}: {r.get('docName')} ({r.get('fileName')})" for r in docs_in_table]
                    self.log(f"Current documents in table: {tbl_summary}")

                    has_photo = any("photo" in (r.get("docName", "") + " " + r.get("fileName", "")).lower() for r in docs_in_table)
                    has_decl = any(("self" in (r.get("docName", "") + " " + r.get("fileName", "")).lower() or "declaration" in (r.get("docName", "") + " " + r.get("fileName", "")).lower()) for r in docs_in_table)
                    has_addr = any(("address" in (r.get("docName", "") + " " + r.get("fileName", "")).lower() or "proof" in (r.get("docName", "") + " " + r.get("fileName", "")).lower()) for r in docs_in_table)

                    self.log(f"Document table status: Photo={has_photo}, AddressProof={has_addr}, SelfDeclaration={has_decl}")

                    if not has_decl:
                        self.log("Self-Declaration missing from table — re-uploading declaration...")
                        if signed_decl_path and (os.path.exists(signed_decl_path) or signed_decl_path.startswith("http")):
                            process_document_upload("Self-Declaration of Applicant", signed_decl_path)
                        else:
                            self.log("WARNING: Cannot re-upload Self-Declaration because no valid signed declaration is available.")

                    if not has_photo:
                        self.log("Photo missing from table — re-uploading Photo...")
                        process_document_upload("Photo", self.docs.get("photo_path"))

                    if not has_addr:
                        self.log("Current Address Proof missing from table — re-uploading...")
                        process_document_upload(
                            "Current Address Proof",
                            self.docs.get("address_proof_path"),
                            self.docs.get("address_doc_no")
                        )

                    # Tier-3 fallback: If Self-Declaration is still missing after verification, select index 3 directly
                    docs_in_table_recheck = get_uploaded_docs_from_table()
                    decl_still_missing = not any(("self" in (r.get("docName", "") + " " + r.get("fileName", "")).lower() or "declaration" in (r.get("docName", "") + " " + r.get("fileName", "")).lower()) for r in docs_in_table_recheck)
                    if decl_still_missing and signed_decl_path and (os.path.exists(signed_decl_path) or signed_decl_path.startswith("http")):
                        self.log("Direct fallback: Selecting Self-Declaration at index 3...")
                        for sel_id in ['[id="ss:dsctype"]', 'select[id*="dsctype"]']:
                            sel_el = page_form.locator(sel_id)
                            if sel_el.count() > 0 and sel_el.first.is_visible():
                                sel_el.first.select_option(index=3)
                                sel_el.first.evaluate("""sel => {
                                    sel.dispatchEvent(new Event('input', { bubbles: true }));
                                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                                    if (sel.onchange) { try { sel.onchange(); } catch(e) {} }
                                }""")
                                time.sleep(3)
                                break
                        page_form.locator("input[type='file']").last.set_input_files(signed_decl_path)
                        time.sleep(3)
                        try:
                            page_form.get_by_text("Upload", exact=True).click(force=True)
                        except Exception:
                            page_form.locator(".rich-fileupload-button-upload, a.rich-fileupload-btn-cnt, input[value='Upload']").first.click(force=True)
                        time.sleep(6)
                except Exception as t_err:
                    self.log(f"Table verification note: {t_err}")

                # --- FINAL STEP: Click Proceed to reach the Payment Details page ---
                self.log("All Documents Uploaded! Navigating to Payment...")
                time.sleep(4)

                # Take a screenshot to log what page we're on before clicking
                try:
                    page_form.screenshot(path=os.path.join(os.path.dirname(__file__), "before_payment_click.png"))
                    self.log("Screenshot saved: before_payment_click.png")
                except Exception:
                    pass

                # Log the current URL and page title for debugging
                self.log(f"Current URL before payment click: {page_form.url}")
                try:
                    self.log(f"Page title: {page_form.title()}")
                except Exception:
                    pass

                # Verify documents in table before clicking Make Payment
                try:
                    rows = page_form.locator("table tr").count()
                    self.log(f"Documents table row count: {rows}")
                except Exception:
                    pass

                # Auto-accept any confirmation dialogs (e.g. 'Are you sure you want to proceed to payment?')
                page_form.on("dialog", lambda dialog: dialog.accept())

                # Click ONLY "Make Payment" on uploadDocs.xhtml.
                # Crucial: NEVER search for generic "Submit" or "Proceed" on this page,
                # because the table row delete button (<input type="submit"> with red 'X') defaults
                # to accessible name "Submit" and will delete uploaded documents (e.g. Photo)!
                make_pay_clicked = False
                make_payment_selectors = [
                    "input[value='Make Payment']",
                    "input[value*='Payment']",
                    "button:has-text('Make Payment')",
                    "a:has-text('Make Payment')",
                    "[id*='payment']",
                    "[id*='Payment']"
                ]

                # First try exact get_by_role("button", name="Make Payment")
                try:
                    btn = page_form.get_by_role("button", name="Make Payment", exact=True)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        btn.first.click()
                        self.log("Clicked 'Make Payment' button via role")
                        make_pay_clicked = True
                except Exception as e:
                    self.log(f"Role click note: {e}")

                if not make_pay_clicked:
                    for sel in make_payment_selectors:
                        try:
                            el = page_form.locator(sel).first
                            if el.is_visible():
                                el.scroll_into_view_if_needed()
                                time.sleep(0.5)
                                el.click()
                                self.log(f"Clicked Make Payment via {sel}")
                                make_pay_clicked = True
                                break
                        except Exception:
                            continue

                if not make_pay_clicked:
                    try:
                        page_form.locator("input[value='Make Payment']").first.click(force=True)
                        self.log("Clicked 'Make Payment' via force click fallback")
                        make_pay_clicked = True
                    except Exception as e:
                        self.log(f"WARNING: Could not find or click Make Payment button: {e}")

                # Wait for navigation away from uploadDocs.xhtml
                navigated_away = False
                try:
                    self.log("Waiting for portal to navigate away from uploadDocs to payment...")
                    page_form.wait_for_url(lambda u: "uploaddocs" not in u.lower(), timeout=35000)
                    navigated_away = True
                    self.log(f"Navigated away from uploadDocs! New URL: {page_form.url}")
                except Exception as ne:
                    self.log(f"Navigation wait note: {ne}")

                try:
                    page_form.wait_for_load_state("domcontentloaded", timeout=15000)
                    page_form.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass

                time.sleep(3)

                # Check if we are on an intermediate Payment Confirmation / Challan page
                # If so, handle Terms & Conditions and the final confirmation button
                try:
                    page_form.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)

                    tc_checkboxes = page_form.locator("input[type='checkbox']")
                    for i in range(tc_checkboxes.count()):
                        try:
                            cb = tc_checkboxes.nth(i)
                            if cb.is_visible() and not cb.is_checked():
                                cb.check(force=True)
                                self.log("Terms & Conditions checkbox checked on payment confirmation page.")
                        except Exception:
                            pass

                    time.sleep(1)

                    for conf_sel in [
                        "input[value='Make Payment']",
                        "input[value='Proceed to Pay']",
                        "input[value='Pay']",
                        "input[value='Confirm Payment']",
                        "button:has-text('Make Payment')",
                        "button:has-text('Proceed to Pay')",
                        "button:has-text('Pay')",
                        "button:has-text('Confirm Payment')"
                    ]:
                        try:
                            c_btn = page_form.locator(conf_sel).first
                            if c_btn.is_visible():
                                self.log(f"Clicking final confirmation payment button via {conf_sel}...")
                                c_btn.scroll_into_view_if_needed()
                                c_btn.click()
                                time.sleep(3)
                                break
                        except Exception:
                            pass
                except Exception as e:
                    self.log(f"Confirmation page handling note: {e}")

                # Wait for final payment gateway URL (BillDesk or similar)
                try:
                    page_form.wait_for_load_state("domcontentloaded", timeout=15000)
                    page_form.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass

                time.sleep(3)

                # Save screenshot of the payment page
                try:
                    after_path = os.path.join(os.path.dirname(__file__), "after_payment_click.png")
                    page_form.screenshot(path=after_path)
                    self.log("Screenshot saved: after_payment_click.png")
                except Exception:
                    pass

                if not navigated_away or "uploaddocs" in page_form.url.lower():
                    err_msg = "Could not proceed to payment page from uploadDocs.xhtml — check if mandatory documents are missing or if portal rejected payment click."
                    self.log(f"CRITICAL ERROR: {err_msg}")
                    if self.ws_manager:
                        self.ws_manager.send_event_sync({
                            "type": "AUTOMATION_ERROR",
                            "message": err_msg
                        })
                    return {"status": "error", "message": err_msg}

                # Get the payment gateway URL and send to frontend
                try:
                    payment_url = page_form.url
                    self.log(f"Payment gateway URL: {payment_url}")
                    if self.ws_manager:
                        self.ws_manager.send_event_sync({
                            "type": "OPEN_PAYMENT_URL",
                            "url": payment_url
                        })
                        self.ws_manager.send_event_sync({
                            "type": "STATUS_MESSAGE",
                            "message": "Payment page reached! Please complete payment in the opened tab."
                        })
                except Exception as e:
                    self.log(f"Could not get payment URL: {e}")

                self.log("SUCCESS! User redirected to payment gateway. Keeping session alive for user to complete payment...")

                # ── BillDesk: Click UPI → Show QR → capture QR → send to frontend ──
                try:
                    # Wait for BillDesk payment methods page to fully load
                    try:
                        page_form.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        time.sleep(4)
                    self.log(f"BillDesk loaded. URL: {page_form.url}")

                    # BillDesk renders inside iframe[name="response-frame"]
                    import base64 as _b64
                    frame = None
                    try:
                        page_form.wait_for_selector('iframe[name="response-frame"]', timeout=15000)
                        frame = page_form.locator('iframe[name="response-frame"]').content_frame
                        self.log("Found response-frame iframe.")
                    except Exception as fe:
                        self.log(f"response-frame not found: {fe} — falling back to main page")

                    ctx = frame if frame else page_form
                    self.log(f"Using context: {'iframe' if frame else 'main page'}")

                    # Step 1: Click the UPI row (exact from Playwright recording)
                    self.log("Clicking UPI payment option...")
                    try:
                        ctx.get_by_role("button", name="upi").click()
                        self.log("Clicked UPI.")
                    except Exception as ue:
                        self.log(f"UPI click failed: {ue}")

                    # Wait for Show QR button to appear after UPI section expands
                    self.log("Waiting for Show QR button to appear...")
                    try:
                        ctx.get_by_role("button", name="Show QR").wait_for(state="visible", timeout=10000)
                        self.log("Show QR button is visible.")
                    except Exception as we:
                        self.log(f"Show QR not visible: {we}")

                    # Step 2: Click Show QR (exact from Playwright recording)
                    self.log("Clicking Show QR...")
                    try:
                        ctx.get_by_role("button", name="Show QR").click()
                        self.log("Clicked Show QR.")
                    except Exception as qe:
                        self.log(f"Show QR click failed: {qe}")

                    # Wait for QR image to appear
                    time.sleep(3)

                    # Step 3: Screenshot locator("img").nth(1) — exact from Playwright recording
                    self.log("Capturing QR image...")
                    qr_b64 = None
                    try:
                        qr_el = ctx.locator("img").nth(1)
                        qr_el.wait_for(state="visible", timeout=8000)
                        qr_bytes = qr_el.screenshot()
                        qr_b64 = _b64.b64encode(qr_bytes).decode()
                        self.log("QR captured via locator('img').nth(1)")
                    except Exception as qr_e:
                        self.log(f"QR element capture failed: {qr_e} — falling back to full page screenshot")
                        try:
                            qr_bytes = page_form.screenshot(full_page=False)
                            qr_b64 = _b64.b64encode(qr_bytes).decode()
                            self.log("Full page screenshot captured as QR fallback.")
                        except Exception as ss_e:
                            self.log(f"Full page screenshot also failed: {ss_e}")

                    # Step 4: Send QR to frontend via WebSocket
                    if self.ws_manager and qr_b64:
                        self.ws_manager.send_event_sync({
                            "type": "PAYMENT_QR",
                            "payment_url": page_form.url,
                            "qr_image": f"data:image/png;base64,{qr_b64}",
                        })
                        self.log("Payment QR sent to frontend.")

                except Exception as qr_e:
                    self.log(f"UPI/QR flow error: {qr_e}")

                # Step 5: Wait for user to click "I have paid" from the frontend
                # Frontend sends USER_ANSWER with data="paid" via WebSocket
                self.log("Waiting for user to confirm payment via frontend...")
                paid_timeout = 600  # 10 minutes
                paid_interval = 2
                elapsed = 0
                while elapsed < paid_timeout:
                    time.sleep(paid_interval)
                    elapsed += paid_interval
                    if self.ws_manager and getattr(self.ws_manager, "latest_response", None):
                        resp = self.ws_manager.latest_response
                        if isinstance(resp, dict) and resp.get("type") == "USER_ANSWER" and str(resp.get("data", "")).lower() in ("paid", "i have paid", "done"):
                            self.log("User confirmed payment via frontend.")
                            self.ws_manager.latest_response = None
                            break
                else:
                    self.log("Payment confirmation timeout — proceeding anyway.")

                # Step 6: Take screenshot of current page and send to frontend
                self.log("Taking confirmation screenshot...")
                try:
                    import base64 as _b64
                    conf_bytes = page_form.screenshot(full_page=True)
                    conf_b64 = _b64.b64encode(conf_bytes).decode()
                    if self.ws_manager:
                        self.ws_manager.send_event_sync({
                            "type": "PAYMENT_SUCCESS",
                            "screenshot": f"data:image/png;base64,{conf_b64}",
                            "url": page_form.url,
                        })
                    self.log("Confirmation screenshot sent to frontend.")
                except Exception as ss_e:
                    self.log(f"Confirmation screenshot failed: {ss_e}")

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