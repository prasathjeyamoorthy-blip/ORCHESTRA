import os
import json
import time
import getpass
import argparse
from playwright.sync_api import sync_playwright

class TNeGACertificateDownloader:
    def __init__(self):
        self.download_folder = os.path.join(os.getcwd(), "Downloaded_Certificates")
        self.captcha_path = os.path.join(os.getcwd(), "captcha_snapshot.png")
        self.error_shot = os.path.join(os.getcwd(), "error_debug.png")
        
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)

    def execute(self, config: dict):
        username = config.get("username")
        password = config.get("password")
        transaction_id = config.get("transaction_id")
        
        playwright = sync_playwright().start()
        launch_kwargs = {"headless": True}
        for chrome_path in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
            if os.path.exists(chrome_path):
                launch_kwargs["executable_path"] = chrome_path
                break
        browser = playwright.chromium.launch(**launch_kwargs) 
        context = browser.new_context()
        page = context.new_page()

        try:
            print("[Bot] Navigating...")
            page.goto("https://www.tnesevai.tn.gov.in/", timeout=60000)

            # --- STAGE 1: LOGIN ---
            if page.get_by_text("English Version").is_visible():
                page.get_by_text("English Version").click()
            
            page.get_by_role("button", name="Citizen Login").click()
            page.get_by_placeholder("User Name", exact=False).first.fill(username)
            page.get_by_placeholder("Password", exact=False).first.fill(password)

            # Captcha
            captcha_loc = page.locator("#captcha_image").first
            if not captcha_loc.is_visible():
                captcha_loc = page.locator("img[src*='Captcha']:visible").first
            captcha_loc.screenshot(path=self.captcha_path)

            print(f"\n>> ACTION: Open '{self.captcha_path}'")
            captcha_code = input(">> ENTER CAPTCHA CODE: ").strip()

            page.locator("input[name*='Captcha'], input[id*='Captcha']").first.fill(captcha_code)
            
            # Click Login
            page.get_by_role("button", name="Login").click()

            # --- FIX: WAIT FOR DASHBOARD ---
            print("[Bot] Waiting for Dashboard...")
            try:
                # Wait for the specific "CheckStatus" link to verify we are logged in
                # Selector based on your image
                page.wait_for_selector("a:has-text('CheckStatus')", timeout=30000)
            except:
                # If timeout, check if we are stuck on login error
                if page.locator("input[name*='Captcha']").is_visible():
                    page.screenshot(path=self.error_shot)
                    return {"status": "FAILED", "message": "Login Failed (Incorrect Captcha/Password)."}
                page.screenshot(path=self.error_shot)
                return {"status": "FAILED", "message": f"Login Timeout. See {self.error_shot}"}

            # --- STAGE 2: NAVIGATE TO STATUS ---
            print("[Bot] Clicking 'Check Status'...")
            # Selector from
            page.get_by_role('link', name='CheckStatus').click()
            
            # --- STAGE 3: SEARCH TRANSACTION ---
            print(f"[Bot] Searching: {transaction_id}")
            
            # Select 'Transaction No' Radio Button
            page.get_by_role('radio', name='Transaction No').click()
            
            # Fill Transaction ID using the specific ID selector
            page.locator('#txtAPPNo').fill(transaction_id)
            
            # Click Fetch
            page.get_by_role('button', name='Fetch').click()

            # --- STAGE 4: RESULT & DOWNLOAD ---
            print("[Bot] Waiting for results table...")
            
            # Wait for "Status:" text to ensure table loaded
            try:
                page.wait_for_selector("text=Status:", timeout=15000)
            except:
                return {"status": "FAILED", "message": "Search yielded no results (Table did not load)."}

            # Verify Approval
            if page.locator("text=Application Approved").count() == 0:
                 page.screenshot(path=self.error_shot)
                 return {"status": "FAILED", "message": "Application not Approved."}

            # Download Certificate
            print("[Bot] Application Approved. Downloading...")
            
            # Click the 'Certificate' link
            download_btn = page.get_by_role('link', name='Certificate')

            try:
                with page.expect_download(timeout=15000) as download_info:
                    download_btn.click()
                
                download = download_info.value
                save_path = os.path.join(self.download_folder, download.suggested_filename)
                download.save_as(save_path)
                
                return {"status": "SUCCESS", "file_path": save_path}

            except Exception as e:
                # Sometimes it opens in a new tab instead of downloading
                return {"status": "ERROR", "message": f"Download failed or opened in Popup: {str(e)}"}

        except Exception as e:
            page.screenshot(path=self.error_shot)
            return {"status": "ERROR", "message": f"{str(e)} - See {self.error_shot}"}

        finally:
            browser.close()
            playwright.stop()

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download TNeGA Residence Certificate")
    parser.add_argument("--payload", help="Path to JSON file with username, password, transaction_id")
    parser.add_argument("--username", help="TNeGA portal username")
    parser.add_argument("--transaction-id", dest="transaction_id", help="Transaction / Application number")
    args = parser.parse_args()

    if args.payload and os.path.exists(args.payload):
        with open(args.payload, "r") as f:
            user_input_json = json.load(f)
    else:
        user_input_json = {
            "username": args.username or input("Enter TNeGA username: ").strip(),
            "password": getpass.getpass("Enter TNeGA password: "),
            "transaction_id": args.transaction_id or input("Enter Transaction ID: ").strip()
        }

    bot = TNeGACertificateDownloader()
    result = bot.execute(user_input_json)

    print("\n--- JSON OUTPUT ---")
    print(json.dumps(result, indent=4))