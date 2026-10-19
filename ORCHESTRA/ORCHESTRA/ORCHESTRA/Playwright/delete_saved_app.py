import os
import time
import json
import base64
import urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None


class TNeSevaiSavedAppCleaner:
    """Headless agent that logs into TNeSevai, navigates to the e-District

    portal (tnedistrict.tn.gov.in/eda/common/saveapp.xhtml), and deletes pending
    saved applications.
    """

    PORTAL_URL = "https://www.tnesevai.tn.gov.in/"
    EDISTRICT_SAVEAPP_URL = "https://tnedistrict.tn.gov.in/eda/common/saveapp.xhtml?faces-redirect=true"
    NAV_TIMEOUT = 60_000

    def __init__(self, credentials: dict, ws_manager=None):
        self.creds = credentials or {}
        self.ws_manager = ws_manager
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.captcha_snapshot = os.path.join(self.base_dir, "captcha_delete_snapshot.png")
        self.screenshot_before = os.path.join(self.base_dir, "before_delete.png")
        self.screenshot_after = os.path.join(self.base_dir, "after_delete.png")

    def log(self, message: str, is_ui: bool = True):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [CLEANER] {message}", flush=True)
        if self.ws_manager and is_ui:
            try:
                self.ws_manager.send_event_sync({
                    "type": "CLEANER_STATUS",
                    "message": message
                })
            except Exception:
                pass

    def _prompt_captcha(self, page, timeout=180) -> str:
        """Prompt user via WebSocket or terminal for captcha."""
        def _get_captcha_b64():
            captcha_img = page.locator("#captcha_image, img[src*='Captcha'], img[src*='captcha']").first
            img_bytes = captcha_img.screenshot(type="png")
            return img_bytes, "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")

        def _click_refresh():
            try:
                page.evaluate("""() => {
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
                time.sleep(1.5)
                try:
                    page.get_by_role("textbox", name="User Name").fill(self.creds.get("username", ""))
                    page.get_by_role("textbox", name="Password").fill(self.creds.get("password", ""))
                except Exception:
                    pass
            except Exception:
                pass

        if not self.ws_manager:
            img_bytes, _ = _get_captcha_b64()
            with open(self.captcha_snapshot, "wb") as f:
                f.write(img_bytes)
            print(f"[CLEANER] Saved captcha to: {self.captcha_snapshot}")
            return input("ENTER CAPTCHA FOR CLEANER: ").strip()

        while True:
            img_bytes, captcha_b64 = _get_captcha_b64()
            self.ws_manager.latest_response = None
            self.ws_manager.send_event_sync({
                "type": "REQUEST_CAPTCHA",
                "message": "Enter the captcha code to delete the saved application.",
                "image": captcha_b64
            })

            elapsed = 0
            got_refresh = False
            while elapsed < timeout:
                resp = self.ws_manager.latest_response
                if resp is not None:
                    m_type = resp.get("type", "")
                    if m_type == "REFRESH_CAPTCHA":
                        self.log("Refreshing captcha on portal...", is_ui=False)
                        _click_refresh()
                        _, new_b64 = _get_captcha_b64()
                        self.ws_manager.send_event_sync({
                            "type": "CAPTCHA_REFRESHED",
                            "image": new_b64
                        })
                        got_refresh = True
                        break
                    elif m_type == "USER_ANSWER":
                        return str(resp.get("data", "")).strip()
                time.sleep(1)
                elapsed += 1

            if not got_refresh:
                raise TimeoutError("Captcha response timed out.")

    def run(self) -> dict:
        """Run the headless browser to navigate to e-District and delete saved applications."""
        username = self.creds.get("username")
        password = self.creds.get("password")

        if not username or not password:
            err = "Missing username or password for portal login."
            self.log(f"✗ {err}")
            return {"status": "error", "message": err}

        self.log("🚀 Starting headless browser to clear saved applications...")

        with sync_playwright() as playwright:
            launch_kwargs = {
                "headless": True,
                "slow_mo": 0,
                "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            }
            for chrome_path in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
                if os.path.exists(chrome_path):
                    launch_kwargs["executable_path"] = chrome_path
                    break

            browser = playwright.chromium.launch(**launch_kwargs)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            if stealth_sync:
                try:
                    stealth_sync(page)
                except Exception:
                    pass

            page_form = None

            try:
                # ── Step 1: Login to tnesevai.tn.gov.in ──
                self.log(f"Navigating to {self.PORTAL_URL}...")
                page.goto(self.PORTAL_URL, timeout=self.NAV_TIMEOUT, wait_until="domcontentloaded")

                try:
                    if page.locator("text=English Version").is_visible(timeout=3000):
                        page.locator("text=English Version").click()
                except Exception:
                    pass

                page.locator("button:has-text('Citizen Login')").click()
                time.sleep(1)

                page.get_by_role("textbox", name="User Name").fill(username)
                page.get_by_role("textbox", name="Password").fill(password)

                # Captcha retry loop
                while True:
                    captcha_code = self._prompt_captcha(page)
                    page.get_by_role("textbox", name="Enter Captcha Code").fill(captcha_code)
                    self.log("Submitting login credentials...", is_ui=False)
                    page.get_by_role("button", name="Login").click()
                    time.sleep(3)

                    page_html = page.content().lower()
                    if any(err in page_html for err in ["does not match", "invalid captcha", "captcha is incorrect", "code you typed"]):
                        self.log("❌ Incorrect captcha code. Retrying...", is_ui=True)
                        try:
                            page.get_by_role("textbox", name="User Name").fill(username)
                            page.get_by_role("textbox", name="Password").fill(password)
                        except Exception:
                            pass
                        continue
                    else:
                        break

                self.log("✓ Logged into citizen portal successfully!")
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                time.sleep(2)

                # ── Step 2: Open e-District service popup ──
                # Saved Application is hosted under tnedistrict.tn.gov.in (not tnesevai)
                # Opening REV-116 transfers the citizen SSO session to tnedistrict.
                self.log("Opening e-District service portal...")
                page.get_by_role("link", name="Revenue Department").click()
                time.sleep(2)

                try:
                    page.get_by_role("link", name="2", exact=True).click()
                    time.sleep(2)
                except Exception:
                    pass

                with page.expect_popup() as popup_info:
                    page.get_by_role("link", name="REV-116 Residence certificate").click()

                page_form = popup_info.value
                page_form.wait_for_load_state("domcontentloaded")
                time.sleep(3)
                self.log(f"✓ e-District popup opened: {page_form.url}")

                # ── Step 3: Navigate to Saved Application (saveapp.xhtml) ──
                self.log("Navigating to Saved Application tab...")
                try:
                    saved_app_link = page_form.locator("a:has-text('Saved Application'), a:has-text('SavedApplication')").first
                    if saved_app_link.count() > 0:
                        saved_app_link.click(timeout=5000)
                        time.sleep(3)
                    else:
                        page_form.goto(self.EDISTRICT_SAVEAPP_URL, wait_until="domcontentloaded")
                        time.sleep(3)
                except Exception:
                    page_form.goto(self.EDISTRICT_SAVEAPP_URL, wait_until="domcontentloaded")
                    time.sleep(3)

                if "saveapp" not in page_form.url:
                    page_form.goto(self.EDISTRICT_SAVEAPP_URL, wait_until="domcontentloaded")
                    time.sleep(3)

                self.log(f"Current page URL: {page_form.url}")
                page_form.wait_for_load_state("domcontentloaded")
                time.sleep(2)

                # Auto-accept any confirmation dialogs (e.g. 'Are you sure you want to delete?')
                page_form.on("dialog", lambda dialog: dialog.accept())

                # ── Step 4: Find and Delete Saved Applications ──
                total_deleted = 0
                max_iterations = 10

                for loop_idx in range(max_iterations):
                    radios = page_form.locator("table input[type='radio'], input[type='radio']")
                    radio_count = radios.count()

                    if radio_count == 0:
                        if loop_idx == 0:
                            self.log("ℹ No saved applications found to delete.")
                            if self.ws_manager:
                                self.ws_manager.send_event_sync({
                                    "type": "SAVED_APP_DELETED",
                                    "message": "No saved applications found on portal."
                                })
                            return {"status": "success", "message": "No saved applications found on portal.", "deleted": 0}
                        else:
                            break

                    self.log(f"Selecting saved application #{loop_idx + 1}...")
                    target_radio = radios.first
                    target_radio.scroll_into_view_if_needed()
                    target_radio.click()
                    time.sleep(2)  # Allow JSF / RichFaces AJAX to register row selection

                    # Also dispatch click via JS in case of styled components
                    try:
                        page_form.evaluate("""() => {
                            const r = document.querySelector('table input[type="radio"], input[type="radio"]');
                            if (r) {
                                r.checked = true;
                                ['click', 'change'].forEach(evt => r.dispatchEvent(new Event(evt, { bubbles: true })));
                            }
                        }""")
                    except Exception:
                        pass
                    time.sleep(1)

                    # Save screenshot before delete
                    try:
                        page_form.screenshot(path=self.screenshot_before)
                    except Exception:
                        pass

                    # Click Delete button
                    deleted_clicked = False
                    delete_selectors = [
                        "button:has-text('Delete')",
                        "input[value='Delete']",
                        "input[value*='Delete' i]",
                        "a:has-text('Delete')",
                        "button[id*='Delete']",
                        "button[id*='delete']",
                        "input[id*='Delete']",
                        "input[id*='delete']",
                        "[title*='Delete']",
                        "input[name*='delete' i]",
                        "button[name*='delete' i]"
                    ]

                    for sel in delete_selectors:
                        loc = page_form.locator(sel)
                        if loc.count() > 0 and loc.first.is_visible():
                            self.log(f"Found Delete button ({sel}), clicking...")
                            loc.first.scroll_into_view_if_needed()
                            loc.first.click()
                            deleted_clicked = True
                            break

                    if not deleted_clicked:
                        # JS evaluation fallback: search all clickable elements for 'delete'
                        deleted_clicked = page_form.evaluate("""() => {
                            const btns = Array.from(document.querySelectorAll('input[type="button"], input[type="submit"], button, a.rich-button, a'));
                            const delBtn = btns.find(b => {
                                const val = (b.value || b.innerText || b.getAttribute('title') || '').trim().toLowerCase();
                                return val === 'delete' || val.includes('delete');
                            });
                            if (delBtn) {
                                delBtn.scrollIntoView();
                                delBtn.click();
                                return true;
                            }
                            return false;
                        }""")
                        if deleted_clicked:
                            self.log("Clicked Delete button via JS evaluation fallback.")

                    if deleted_clicked:
                        time.sleep(4)
                        total_deleted += 1

                        # Save screenshot after delete
                        try:
                            page_form.screenshot(path=self.screenshot_after)
                        except Exception:
                            pass

                        page_text = page_form.content()
                        if "deleted successfully" in page_text.lower():
                            self.log(f"✓ Application #{total_deleted} deleted successfully from portal!")
                        else:
                            self.log(f"✓ Deletion executed for Application #{total_deleted}.")
                    else:
                        self.log("⚠ Could not locate a Delete button on the page.")
                        break

                msg = f"✓ Deleted {total_deleted} saved application(s) from portal."
                self.log(msg)

                if self.ws_manager:
                    self.ws_manager.send_event_sync({
                        "type": "SAVED_APP_DELETED",
                        "message": msg,
                        "deleted_count": total_deleted
                    })

                return {"status": "success", "message": msg, "deleted": total_deleted}

            except Exception as e:
                err_msg = f"Failed to delete saved application: {str(e)}"
                self.log(f"✗ {err_msg}")
                if self.ws_manager:
                    try:
                        self.ws_manager.send_event_sync({
                            "type": "CLEANER_ERROR",
                            "message": err_msg
                        })
                    except Exception:
                        pass
                return {"status": "error", "message": err_msg}

            finally:
                try:
                    if page_form:
                        page_form.close()
                except Exception:
                    pass
                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Delete saved applications on TNeSevai / e-District portal.")
    parser.add_argument("--username", default="lohithg", help="TNeSevai Username")
    parser.add_argument("--password", default="Lohith@2007", help="TNeSevai Password")
    args = parser.parse_args()

    cleaner = TNeSevaiSavedAppCleaner(credentials={"username": args.username, "password": args.password})
    cleaner.run()
