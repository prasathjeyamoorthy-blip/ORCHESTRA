"""Main workflow orchestration for PAN application."""

import datetime
from typing import Dict
from playwright.sync_api import Page
from browser_manager import BrowserManager
from captcha_solver import CaptchaSolver
from form_filler import FormFiller
from config import PAN_REGISTRATION_URL


class PANApplicationWorkflow:
    """Orchestrates the complete PAN application workflow."""
    
    def __init__(self, page: Page, data: Dict):
        self.page = page
        self.data = data
        self.form_filler = FormFiller(page, data)
    
    def execute(self) -> Dict:
        """Execute the complete application workflow."""
        print("\n[*] Starting PAN card application workflow...")
        
        # Step 1: Navigate and handle initial page
        self._navigate_to_registration()
        
        # Step 2: Fill registration form
        self.form_filler.fill_registration_details()
        
        # Step 3: Solve CAPTCHA
        self._handle_captcha()
        
        # Step 4: Submit registration
        self._submit_registration()
        
        # Step 5: Handle token page
        self._handle_token_page()
        
        # Step 6: Fill applicant details
        self.form_filler.fill_applicant_details()
        self._next_page()
        
        # Step 7: Fill contact and address
        self.form_filler.fill_contact_address()
        self._next_page()
        
        # Step 8: Skip AO code page
        self._next_page()
        
        # Step 9: Upload documents
        self.form_filler.upload_documents()
        
        # Step 10: Fill declaration
        self.form_filler.fill_declaration()
        
        # Step 11: Final submission
        self._final_submit()
        
        # Step 12: Aadhaar verification
        self._verify_aadhaar()
        
        # Step 13: Payment flow
        payment_info = self._handle_payment()
        
        print("\n[✓] Workflow completed successfully!")
        return payment_info
    
    def _navigate_to_registration(self) -> None:
        """Navigate to registration page and handle cookies."""
        print("[*] Navigating to registration page...")

        # Brief warm-up visit — establishes a real browsing history so
        # Google's reCAPTCHA risk engine treats this session as lower-risk.
        try:
            self.page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=15000)
            BrowserManager.wait(self.page, 1500)
            self.page.goto("https://www.incometax.gov.in", wait_until="domcontentloaded", timeout=15000)
            BrowserManager.wait(self.page, 1000)
        except Exception:
            pass  # warm-up is best-effort

        self.page.goto(PAN_REGISTRATION_URL)
        self.page.wait_for_load_state("networkidle")
        BrowserManager.wait(self.page, 2000)
        
        # Handle cookie banner
        try:
            allow_btn = self.page.get_by_role("button", name="Allow all")
            if allow_btn.is_visible(timeout=3000):
                allow_btn.click()
                BrowserManager.wait(self.page, 1000)
        except Exception as e:
            print(f"[+] Cookie banner not found or already dismissed: {e}")
        
        # Wait for form to be ready
        self.page.wait_for_selector("#select2-type-container", state="visible", timeout=10000)
        BrowserManager.wait(self.page, 1000)
    
    def _handle_captcha(self) -> None:
        """Solve reCAPTCHA if present."""
        print("[*] Handling CAPTCHA...")
        # Wait for reCAPTCHA iframes to load before handing off to the solver
        print("[*] Waiting for reCAPTCHA to load...")
        for _ in range(20):
            if any("recaptcha" in f.url for f in self.page.frames):
                print("[*] reCAPTCHA iframe detected")
                break
            BrowserManager.wait(self.page, 1000)
        else:
            print("[!] reCAPTCHA iframe not detected after 20s — attempting solve anyway")
        solver = CaptchaSolver(self.page)
        solver.solve()
    
    def _submit_registration(self) -> None:
        """Submit the registration form."""
        print("[*] Submitting registration...")
        self.page.keyboard.press("Escape")
        BrowserManager.wait(self.page, 1000)
        self.page.get_by_role("button", name="Submit").click(force=True)
        self.page.wait_for_load_state("networkidle")
    
    def _handle_token_page(self) -> None:
        """Handle token page and select application type."""
        print("[*] Handling token page...")
        BrowserManager.wait(self.page, 2000)
        
        try:
            continue_new = self.page.get_by_role("button", name="Continue with new Token")
            if continue_new.is_visible():
                continue_new.click()
                BrowserManager.wait(self.page, 1000)
            self.page.get_by_role("button", name="Continue").click()
            self.page.wait_for_load_state("networkidle")
        except Exception:
            pass
        
        # Select application method
        try:
            self.page.get_by_text("PAN Application with supporting documents (Scan, Upload and eSign)").click(timeout=3000)
            BrowserManager.wait(self.page)
        except Exception:
            pass
    
    def _next_page(self) -> None:
        """Navigate to next page in the form."""
        self.page.get_by_role("link", name="Next ").click()
        BrowserManager.wait(self.page, 1500)
    
    def _final_submit(self) -> None:
        """Submit the complete application form."""
        print("[*] Submitting application...")
        self.page.get_by_role("button", name="Submit ").click()
        self.page.wait_for_load_state("networkidle")
    
    def _verify_aadhaar(self) -> None:
        """Enter Aadhaar first 8 digits for verification."""
        print("[*] Verifying Aadhaar...")
        self.page.locator("#aadhaarNo_1").fill(self.data["aadhaar_first_8"])
        BrowserManager.wait(self.page)
        self.page.get_by_role("button", name="Proceed ").click()
        BrowserManager.wait(self.page, 5000)
    
    def _handle_payment(self) -> Dict:
        """Handle payment flow and capture details."""
        print("[*] Proceeding to payment...")
        
        # Agree to terms
        self.page.get_by_role("radio", name="I agree to the terms of").check()
        BrowserManager.wait(self.page)
        self.page.get_by_role("button", name="Proceed to Payment ").click()
        BrowserManager.wait(self.page, 15000)
        
        # Click Pay Confirm
        try:
            self.page.get_by_role("button", name="Pay Confirm ").click()
            print("[+] Clicked Pay Confirm, waiting for payment gateway...")
            BrowserManager.wait(self.page, 15000)
            
            # Try to select UPI payment
            self._select_upi_payment()
            
        except Exception as e:
            print(f"[!] Could not complete payment flow: {e}")
        
        # Capture payment information
        return self._capture_payment_info()
    
    def _select_upi_payment(self) -> None:
        """Attempt to select UPI payment method."""
        try:
            upi_selectors = [
                "text=UPI",
                "text=Pay by UPI",
                "[data-testid='upi']",
                ".payment-method:has-text('UPI')",
                "button:has-text('UPI')"
            ]
            
            for selector in upi_selectors:
                try:
                    if self.page.locator(selector).is_visible(timeout=2000):
                        self.page.locator(selector).click()
                        print("[+] Clicked UPI payment option")
                        BrowserManager.wait(self.page, 5000)
                        break
                except:
                    continue
        except Exception as e:
            print(f"[!] Could not interact with payment gateway: {e}")
    
    def _capture_payment_info(self) -> Dict:
        """Capture payment URL and screenshot."""
        print("[*] Capturing payment information...")
        
        payment_url = self.page.url
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"payment_page_{timestamp}.png"
        
        # Take screenshot
        self.page.screenshot(path=screenshot_path, full_page=True)
        
        print(f"\n{'='*80}")
        print(f"[+] PAYMENT LINK GENERATED")
        print(f"{'='*80}")
        print(f"\n{payment_url}\n")
        print(f"{'='*80}")
        print(f"[+] Payment page screenshot saved: {screenshot_path}")
        
        return {
            "url": payment_url,
            "screenshot": screenshot_path
        }
