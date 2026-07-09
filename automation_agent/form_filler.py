"""Form filling functionality for PAN application."""

from typing import Dict
from playwright.sync_api import Page, expect
from browser_manager import BrowserManager
from config import PROOF_DOCUMENTS, VERIFIER_OPTIONS


class FormFiller:
    """Handles filling various sections of the PAN application form."""
    
    def __init__(self, page: Page, data: Dict):
        self.page = page
        self.data = data
    
    def _wait(self, ms: int = None) -> None:
        """Convenience method for waiting."""
        BrowserManager.wait(self.page, ms)

    def _fill_and_verify(self, selector: str, value: str, label: str = "") -> None:
        """
        Fill a text field and verify the value stuck.
        NSDL's JS can clear fields after .fill() if live validation or a
        re-render fires. Strategy:
          1. Wait for field to be visible and enabled
          2. Click to focus, triple-click to select all existing text
          3. Type character by character (triggers keydown/keypress/keyup)
          4. Verify — if still wrong, fall back to JS value injection
        """
        if not value:
            return
        locator = self.page.locator(selector)
        try:
            locator.wait_for(state="visible", timeout=5000)
        except Exception:
            print(f"[!] Field {label or selector} not visible — skipping")
            return

        for attempt in range(3):
            locator.click()
            self._wait(200)
            # Select all and clear before typing
            locator.press("Control+a")
            self._wait(100)
            locator.press("Backspace")
            self._wait(100)
            # Type character by character so all JS event handlers fire
            locator.type(value, delay=50)
            self._wait(500)
            actual = locator.input_value()
            if actual == value:
                return
            print(f"[!] Attempt {attempt+1}: {label or selector} = {actual!r}, expected {value!r} — retrying via JS")
            # JS fallback
            self.page.evaluate(
                """([el, v]) => {
                    el.focus();
                    el.value = v;
                    el.dispatchEvent(new Event('input',  {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    el.dispatchEvent(new Event('blur',   {bubbles:true}));
                }""",
                [locator.element_handle(), value]
            )
            self._wait(400)
            if locator.input_value() == value:
                return
        print(f"[!] Could not set {label or selector} to {value!r} after 3 attempts")

    def fill_registration_details(self) -> None:
        """Fill the initial registration form."""
        print("[*] Filling registration details...")
        
        # Select application type
        self.page.locator("#select2-type-container").click()
        self._wait(1000)
        self.page.wait_for_selector(".select2-results", state="visible", timeout=5000)
        self.page.get_by_role("option", name="New PAN - Form No. 93 (Indian").click()

        # Wait for the form to finish re-rendering after type selection.
        # The dropdown selection causes the name/DOB fields to re-render —
        # filling them before the render completes results in values being wiped.
        # Wait until the first name field is visible AND stable (not changing).
        self.page.wait_for_selector("#f_name_end", state="visible", timeout=10000)
        self._wait(1500)   # extra settle time for all JS handlers to complete

        # Fill personal details — type() triggers all JS keyboard events
        self._fill_and_verify("#f_name_end", self.data["first_name"], "first_name")
        self._wait(600)
        self._fill_and_verify("#l_name_end", self.data["last_name"], "last_name")
        self._wait(600)
        
        if self.data.get("middle_name"):
            self._fill_and_verify("#m_name_end", self.data["middle_name"], "middle_name")
            self._wait(600)
        
        # DOB — masked date input (DD/MM/YYYY).
        # The field uses a JS input mask that auto-inserts the "/" separators.
        # Strategy:
        #   1. Click to focus, clear existing value
        #   2. Type only the digits — mask inserts "/" automatically
        #      e.g. "23022007" → mask produces "23/02/2007"
        #   3. If that fails (value wrong/empty), fall back to JS direct set
        #      which bypasses the mask entirely
        dob_locator = self.page.locator("#date_of_birth_reg")
        dob_locator.wait_for(state="visible", timeout=5000)

        dob_value = self.data["dob"]  # expected: "DD/MM/YYYY"
        dob_digits = dob_value.replace("/", "").replace("-", "")  # "23022007"
        # Normalize to DD/MM/YYYY for comparison (stored value may use dashes)
        if len(dob_digits) == 8:
            dob_expected = f"{dob_digits[0:2]}/{dob_digits[2:4]}/{dob_digits[4:8]}"
        else:
            dob_expected = dob_value

        dob_locator.click()
        self._wait(300)
        # Clear field
        dob_locator.press("Control+a")
        self._wait(100)
        dob_locator.press("Delete")
        self._wait(100)
        # Type digits only — let the mask insert "/"
        dob_locator.type(dob_digits, delay=80)
        self._wait(600)
        # Press Tab to commit
        dob_locator.press("Tab")
        self._wait(800)

        # Verify — if mask produced a different format, fall back to JS set
        actual_dob = dob_locator.input_value()
        if actual_dob != dob_expected:
            print(f"[!] DOB mask produced {actual_dob!r}, expected {dob_expected!r} — using JS fallback")
            self.page.evaluate(
                """([el, v]) => {
                    el.removeAttribute('readonly');
                    el.value = v;
                    el.dispatchEvent(new Event('input',  {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    el.dispatchEvent(new Event('blur',   {bubbles:true}));
                }""",
                [dob_locator.element_handle(), dob_expected]
            )
            self._wait(500)
            dob_locator.press("Tab")
            self._wait(500)
            actual_dob = dob_locator.input_value()

        print(f"[*] DOB field value after fill: {actual_dob!r}")
        
        self._fill_and_verify("#email_id2", self.data["email"], "email")
        self._wait(600)
        self._fill_and_verify("#rvContactNo", self.data["phone"], "phone")
        self._wait(600)
        
        self.page.locator("#consent").check()
        self._wait(2000)
    
    def fill_applicant_details(self) -> None:
        """Fill applicant personal information."""
        print("[*] Filling applicant details...")
        
        self._fill_and_verify("#aadhaarNo_2", self.data["aadhaar_last_4"], "aadhaar_last_4")
        self._wait()
        self._fill_and_verify("#rvNameAadhaar_id", self.data["name_on_aadhaar"], "name_on_aadhaar")
        self._wait()
        
        # Gender — Select2 dropdown. Click the container span to open, then pick the option.
        # Try multiple selectors since Select2 renders different elements.
        gender_opened = False
        for selector in [
            "#select2-gender-container",
            "[id*='select2'][id*='gender']",
            ".select2-selection[aria-label*='ender']",
            "span.select2-selection",
        ]:
            try:
                loc = self.page.locator(selector).first
                if loc.is_visible(timeout=3000):
                    loc.click()
                    gender_opened = True
                    break
            except Exception:
                continue

        if not gender_opened:
            # Final fallback — the textbox placeholder approach
            try:
                self.page.get_by_role("combobox").filter(has_text="Please Select").first.click()
                gender_opened = True
            except Exception:
                pass

        if gender_opened:
            self._wait(500)
            try:
                self.page.get_by_role("option", name=self.data["gender"], exact=True).click(timeout=5000)
                print(f"[*] Gender set: {self.data['gender']}")
            except Exception:
                # Try listbox approach
                self.page.locator(f"li:has-text('{self.data['gender']}')").first.click()
        else:
            print(f"[!] Could not open gender dropdown — skipping")
        self._wait()
        
        # Parent details
        self._fill_and_verify("#faf_name", self.data["father_first_name"], "father_first_name")
        self._wait()
        self._fill_and_verify("#fal_name", self.data["father_last_name"], "father_last_name")
        self._wait()
        self._fill_and_verify("#mof_name", self.data["mother_first_name"], "mother_first_name")
        self._wait()
        self._fill_and_verify("#mom_name", self.data.get("mother_middle_name", ""), "mother_middle_name")
        self._wait()
        self._fill_and_verify("#mol_name", self.data["mother_last_name"], "mother_last_name")
        self._wait()
    
    def fill_contact_address(self) -> None:
        """Fill contact and address details."""
        print("[*] Filling contact and address...")
        
        self.page.get_by_role("radio", name=self.data.get("residential_status", "Resident"), exact=True).check()
        self._wait()

        # Source of income — use value from data, default to "No income"
        source = self.data.get("source_of_income", "No income").split("|")[0].strip()
        self.page.get_by_text(source, exact=True).click()
        self._wait()

        # Address for communication — use value from data, default to "Residence"
        addr_comm = self.data.get("address_for_comm", "Residence").split("|")[0].strip()
        self.page.get_by_text(addr_comm, exact=True).click()
        self._wait()
        
        # Address fields
        self._fill_and_verify("#rFlat", self.data.get("flat_room_door", ""), "flat_room_door")
        self._wait()
        self._fill_and_verify("#rName", self.data["building_village"], "building_village")
        self._wait()
        self._fill_and_verify("#rArea", self.data["road_street_post"], "road_street_post")
        self._wait()
        self._fill_and_verify("#rCountry", self.data["area_locality"], "area_locality")
        self._wait()
        
        # Country and state
        self.page.locator("select#country_name").select_option(label=self.data.get("country", "INDIA"))
        self._wait()
        state_select = self.page.locator("#state_div select")
        state_select.select_option(label=self.data.get("state", "PONDICHERRY"))
        self._wait()
        
        # Pin code (remove readonly attribute and set via JS so change events fire)
        self.page.once("dialog", lambda dialog: dialog.dismiss())
        pin = self.data["pin_code"]
        self.page.evaluate(f"""
            () => {{
                const el = document.getElementById('res_pin_code');
                if (el) {{
                    el.removeAttribute('readonly');
                    el.value = '{pin}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}
        """)
        self._wait()
        
        # ISD code
        self.page.locator("#tel_num_isdcode_div select").select_option(label=self.data.get("isd_label", "INDIA (91)"))
        self._wait()
    
    def upload_documents(self) -> None:
        """Upload required documents from the docs folder."""
        print("[*] Uploading documents...")
        
        # Photo
        with self.page.expect_file_chooser() as fc_info:
            self.page.locator("#image").click()
        fc_info.value.set_files(self.data.get("photo_file", "docs/jphoto.jpeg"))
        self.page.locator("#photoUpload").click()
        self._wait(5000)
        
        # Signature
        with self.page.expect_file_chooser() as fc_info:
            self.page.locator("#imageSign").click()
        fc_info.value.set_files(self.data.get("signature_file", "docs/jsign.jpeg"))
        self.page.locator("#signUpload").click()
        self._wait(5000)
        
        # Add document button
        self.page.get_by_role("button", name=" Add Document").click()
        self._wait(1000)
        
        # Aadhaar PDF
        with self.page.expect_file_chooser() as fc_info:
            self.page.locator("input[name=\"doc1_file\"]").click()
        fc_info.value.set_files(self.data.get("aadhaar_pdf", "docs/jaadhar (1).pdf"))
        self._wait(1000)
        
        # Birth certificate PDF
        with self.page.expect_file_chooser() as fc_info:
            self.page.locator("input[name=\"doc2_file\"]").click()
        fc_info.value.set_files(self.data.get("birth_cert_pdf", "docs/jbirthcert.pdf"))
        self._wait(1000)
        
        # Upload button
        self.page.locator("#docsUpload").click()
        self._wait(5000)
    
    def fill_declaration(self) -> None:
        """Fill declaration and select document types."""
        print("[*] Filling declaration...")
        
        # Select proof of identity
        self.page.locator("#select2-poidCode-container").click()
        self._wait()
        self.page.get_by_role("option", name=PROOF_DOCUMENTS['aadhaar']).click()
        self._wait()
        
        # Select proof of address
        self.page.locator("#poaCode_div").get_by_role("combobox").click()
        self._wait()
        self.page.get_by_role("option", name=PROOF_DOCUMENTS['aadhaar']).click()
        self._wait()
        
        # Select proof of date of birth
        self.page.locator("#select2-proof_dob_code-container").click()
        self._wait()
        self.page.get_by_role("option", name=PROOF_DOCUMENTS['birth_certificate']).click()
        self._wait()
        
        # Select verifier
        self.page.get_by_role("combobox", name="-------- Select --------").click()
        self._wait()
        self.page.get_by_role("option", name=VERIFIER_OPTIONS['self']).click()
        self._wait()
        
        # Verifier details
        self.page.locator("#verifierPlace").fill(self.data["verifier_place"])
        self._wait()
        self.page.locator("#designation").fill(self.data["verifier_designation"])
        self._wait()
