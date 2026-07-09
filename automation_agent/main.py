"""Main entry point for PAN card application automation."""

from playwright.sync_api import sync_playwright
from browser_manager import BrowserManager
from data_handler import DataHandler, DataLoadError
from workflow import PANApplicationWorkflow


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("PAN CARD APPLICATION AUTOMATION")
    print("="*80 + "\n")
    
    # Load application data from INPUT.json
    try:
        data = DataHandler.load_from_json("INPUT.json")
    except DataLoadError as e:
        print(f"\n[ERROR] {e}")
        print("\n[INFO] Trying data.json as fallback...")
        try:
            data = DataHandler.load_from_json("data.json")
        except DataLoadError:
            print("\n[ERROR] Neither INPUT.json nor data.json found!")
            return 1

    if data is None:
        print("\n[!] Exiting. Please run finalize-application endpoint first to generate INPUT.json.")
        return 1
    
    # first_name is optional; fall back gracefully for display
    applicant_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    print(f"[*] Applicant: {applicant_name or 'N/A'}")
    print(f"[*] Email: {data.get('email', 'N/A')}\n")
    
    # Run automation with Playwright
    with sync_playwright() as playwright:
        # Initialize browser (headless=False to see the automation)
        browser = BrowserManager.create_browser(playwright, headless=False)
        context = BrowserManager.create_context(browser)
        page = BrowserManager.create_page(context)
        
        try:
            # Execute workflow
            workflow = PANApplicationWorkflow(page, data)
            payment_info = workflow.execute()
            
            # Save payment information
            DataHandler.save_payment_info(
                payment_url=payment_info["url"],
                screenshot_path=payment_info["screenshot"],
                data=data
            )
            
            print("\n[*] Use the payment link from payment_link.json in your browser")
            print("[*] After payment, you'll see the confirmation page with your acknowledgment number.")
            
        except Exception as e:
            print(f"\n[ERROR] Application failed: {e}")
            import traceback
            traceback.print_exc()
            # Take a screenshot so the failure state is visible
            try:
                import datetime
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"failure_{ts}.png"
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"[*] Failure screenshot saved: {screenshot_path}")
            except Exception:
                pass
            # Keep browser open for 60 seconds so the developer can inspect the state
            print("[*] Browser will stay open for 60 seconds for inspection...")
            try:
                page.wait_for_timeout(60_000)
            except Exception:
                pass
            return 1
        
        finally:
            # Cleanup — only runs after the 60s wait above on failure,
            # or immediately on success
            context.close()
            browser.close()
    
    print("\n[✓] Automation completed successfully!")
    print("="*80 + "\n")
    return 0


if __name__ == "__main__":
    exit(main())
