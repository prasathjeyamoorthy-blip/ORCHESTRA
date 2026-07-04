"""Form filling functionality for PAN application."""

from typing import Dict
from playwright.sync_api import Page
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
    
    def fill_registration_details(self) -> None:
        """Fill the initial registration form."""
        print("[*] Filling registration details...")
        
        # Select application type
        self.page.locator("#select2-type-container").click()
        self._wait(1000)
        self.page.wait_for_selector(".select2-results", state="visible", timeout=5000)
        self.page.get_by_role("option", name="New PAN - Form No. 93 (Indian").click()
        self._wait(1000)
        
        # Fill personal details
        self.page.locator("#f_name_end").fill(self.data["first_name"])
        self._wait()
        self.page.locator("#l_name_end").fill(self.data["last_name"])
        self._wait()
        
        if self.data.get("middle_name"):
            self.page.locator("#m_name_end").fill(self.data["middle_name"])
            self._wait()
        
        self.page.locator("#date_of_birth_reg").fill(self.data["dob"])
        self._wait()
        self.page.locator("#date_of_birth_reg").click(position={"x": 400, "y": 0}, force=True)
        self._wait()
        
        self.page.locator("#email_id2").fill(self.data["email"])
        self._wait()
        self.page.locator("#rvContactNo").fill(self.data["phone"])
        self._wait()
        
        self.page.locator("#consent").check()
        self._wait(2000)
    
    def fill_applicant_details(self) -> None:
        """Fill applicant personal information."""
        print("[*] Filling applicant details...")
        
        self.page.locator("#aadhaarNo_2").fill(self.data["aadhaar_last_4"])
        self._wait()
        self.page.locator("#rvNameAadhaar_id").fill(self.data["name_on_aadhaar"])
        self._wait()
        
        self.page.get_by_role("textbox", name="Please Select").click()
        self._wait()
        self.page.get_by_role("option", name=self.data["gender"], exact=True).click()
        self._wait()
        
        # Parent details
        self.page.locator("#faf_name").fill(self.data["father_first_name"])
        self._wait()
        self.page.locator("#fal_name").fill(self.data["father_last_name"])
        self._wait()
        self.page.locator("#mof_name").fill(self.data["mother_first_name"])
        self._wait()
        self.page.locator("#mom_name").fill(self.data["mother_middle_name"])
        self._wait()
        self.page.locator("#mol_name").fill(self.data["mother_last_name"])
        self._wait()
    
    def fill_contact_address(self) -> None:
        """Fill contact and address details."""
        print("[*] Filling contact and address...")
        
        self.page.get_by_role("radio", name=self.data.get("residential_status", "Resident"), exact=True).check()
        self._wait()
        self.page.get_by_text("No income").click()
        self._wait()
        self.page.get_by_text("Residence", exact=True).click()
        self._wait()
        
        # Address fields
        self.page.locator("#rFlat").fill(self.data["flat_room_door"])
        self._wait()
        self.page.locator("#rName").fill(self.data["building_village"])
        self._wait()
        self.page.locator("#rArea").fill(self.data["road_street_post"])
        self._wait()
        self.page.locator("#rCountry").fill(self.data["area_locality"])
        self._wait()
        
        # Country and state
        self.page.locator("select#country_name").select_option(label=self.data.get("country", "INDIA"))
        self._wait()
        state_select = self.page.locator("#state_div select")
        state_select.select_option(label=self.data.get("state", "PONDICHERRY"))
        self._wait()
        
        # Pin code (remove readonly attribute)
        self.page.once("dialog", lambda dialog: dialog.dismiss())
        self.page.evaluate(f"""
            () => {{
                const el = document.getElementById('res_pin_code');
                if (el) {{
                    el.removeAttribute('readonly');
                    el.value = '{self.data["pin_code"]}';
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
