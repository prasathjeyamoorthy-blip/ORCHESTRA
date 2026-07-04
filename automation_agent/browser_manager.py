"""Browser initialization and management."""

from playwright.sync_api import Browser, BrowserContext, Page, Playwright
from playwright_stealth import Stealth
from config import (
    BROWSER_ARGS, 
    BROWSER_VIEWPORT, 
    BROWSER_USER_AGENT, 
    BROWSER_CONTEXT_CONFIG,
    STEALTH_SCRIPT
)


class BrowserManager:
    """Manages browser lifecycle and configuration."""
    
    @staticmethod
    def create_browser(playwright: Playwright, headless: bool = True) -> Browser:
        """Create and configure browser instance."""
        return playwright.chromium.launch(
            headless=headless,
            args=BROWSER_ARGS
        )
    
    @staticmethod
    def create_context(browser: Browser) -> BrowserContext:
        """Create browser context with stealth configurations."""
        context = browser.new_context(
            viewport=BROWSER_VIEWPORT,
            user_agent=BROWSER_USER_AGENT,
            **BROWSER_CONTEXT_CONFIG
        )
        
        # Apply stealth scripts
        context.add_init_script(STEALTH_SCRIPT)
        Stealth().apply_stealth_sync(context)
        
        return context
    
    @staticmethod
    def create_page(context: BrowserContext) -> Page:
        """Create a new page with event listeners."""
        page = context.new_page()
        
        # Prevent page from closing unexpectedly
        page.on("close", lambda: print("[!] Page closed unexpectedly"))
        page.on("crash", lambda: print("[!] Page crashed"))
        
        return page
    
    @staticmethod
    def wait(page: Page, ms: int = None, default_delay: int = 600) -> None:
        """Wait for specified milliseconds or use default delay."""
        page.wait_for_timeout(ms or default_delay)
