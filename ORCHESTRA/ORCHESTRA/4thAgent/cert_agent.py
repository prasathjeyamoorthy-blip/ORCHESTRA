import os,json,time,getpass
from playwright.sync_api import sync_playwright

class TNeGACertificateDownloader:
    def __init__(self):
        self.base=os.getcwd()
        self.download_folder=os.path.join(self.base,"Downloaded_Certificates")
        self.captcha_path=os.path.join(self.base,"captcha_snapshot.png")
        self.error_shot=os.path.join(self.base,"error_debug.png")
        os.makedirs(self.download_folder,exist_ok=True)

    def execute(self,config:dict):
        username=config["username"]
        password=config["password"]
        transaction_id=config["transaction_id"]

        playwright=sync_playwright().start()
        launch_kwargs = {"headless": False, "slow_mo": 50}
        for chrome_path in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
            if os.path.exists(chrome_path):
                launch_kwargs["executable_path"] = chrome_path
                break
        browser=playwright.chromium.launch(**launch_kwargs)
        context=browser.new_context(accept_downloads=True)
        page=context.new_page()

        try:
            print("[Bot] Opening TN eSevai...")
            page.goto("https://www.tnesevai.tn.gov.in/",timeout=60000)

            if page.locator("text=English Version").is_visible():
                page.locator("text=English Version").click()

            page.locator("button:has-text('Citizen Login')").click()
            page.locator("input[placeholder*='User']").fill(username)
            page.locator("input[placeholder*='Password']").fill(password)

            captcha_img=page.locator("img[src*='Captcha']").first
            captcha_img.screenshot(path=self.captcha_path)

            print(f"\nOPEN CAPTCHA IMAGE: {self.captcha_path}")
            captcha=input("ENTER CAPTCHA: ").strip()

            page.locator("input[name*='Captcha'],input[id*='Captcha']").fill(captcha)

            captcha_input = page.locator("input[name*='Captcha'],input[id*='Captcha']")
            captcha_input.fill(captcha)

            page.wait_for_timeout(800)

            # 🔥 REAL HUMAN ACTION
            captcha_input.press("Enter")

            print("[Bot] Submitted login, waiting...")

            page.wait_for_timeout(3000)

            page.wait_for_selector(
                "a:has-text('Check Status'), a:has-text('CheckStatus')",
                timeout=30000
            )

            print("[Bot] Waiting for dashboard...")
            page.wait_for_selector("a:has-text('Check Status'),a:has-text('CheckStatus')",timeout=30000)

            print("[Bot] Opening Check Status...")
            page.locator("a:has-text('Check Status'),a:has-text('CheckStatus')").first.click(force=True)

            print("[Bot] Searching Transaction...")
            page.wait_for_timeout(1500)
            page.locator("input[type='radio']").nth(0).check()
            page.locator("#txtAPPNo").fill(transaction_id)
            page.locator("button:has-text('Fetch')").click()

            print("[Bot] Waiting for result...")
            page.wait_for_selector("text=Application",timeout=20000)

            if page.locator("text=Application Approved").count()==0:
                page.screenshot(path=self.error_shot)
                return {"status":"FAILED","message":"Application not approved"}

            print("[Bot] Approved. Downloading certificate...")

            pages_before=context.pages
            page.locator("a:has-text('Certificate')").click(force=True)
            time.sleep(4)

            pages_after=context.pages
            if len(pages_after)>len(pages_before):
                cert_page=pages_after[-1]
                cert_page.wait_for_load_state()
                pdf_path=os.path.join(self.download_folder,f"{transaction_id}.pdf")
                cert_page.pdf(path=pdf_path)
                return {"status":"SUCCESS","file_path":pdf_path}

            with page.expect_download(timeout=15000) as d:
                page.locator("a:has-text('Certificate')").click(force=True)
            download=d.value
            save_path=os.path.join(self.download_folder,download.suggested_filename)
            download.save_as(save_path)
            return {"status":"SUCCESS","file_path":save_path}

        except Exception as e:
            page.screenshot(path=self.error_shot)
            return {"status":"ERROR","message":str(e)}

        finally:
            browser.close()
            playwright.stop()

if __name__=="__main__":
    config={
        "username":"lohithg",
        "password":getpass.getpass("Password: "),
        "transaction_id":"TNCIT000000012997009"
    }
    bot=TNeGACertificateDownloader()
    print(json.dumps(bot.execute(config),indent=4))
