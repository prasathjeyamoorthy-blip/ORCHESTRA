# debug.py — nav inspector using Firefox
import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print("Navigating...")
        await page.goto("https://www.protean-tinpan.com", timeout=60000, wait_until="networkidle")
        print(f"✅ Loaded | URL: {page.url} | Title: {await page.title()}")
        await asyncio.sleep(3)

        # Dismiss popup
        try:
            btn = page.get_by_text("Continue", exact=True)
            if await btn.is_visible(timeout=5000):
                await btn.click()
                print("✅ Popup dismissed")
                await asyncio.sleep(2)
        except:
            print("ℹ️  No popup")

        # All links
        links = await page.eval_on_selector_all(
            "a",
            "els => els.map(e => ({ href: e.href, text: e.innerText.trim() })).filter(e => e.text.length > 0)"
        )
        print(f"\n=== ALL LINKS ({len(links)}) ===")
        for l in links:
            print(f"  [{l['text'][:50]}]  →  {l['href']}")

        # All buttons
        buttons = await page.eval_on_selector_all(
            "button, [role='button']",
            "els => els.map(e => ({ text: e.innerText.trim(), cls: e.className })).filter(e => e.text.length > 0)"
        )
        print(f"\n=== BUTTONS ({len(buttons)}) ===")
        for b in buttons[:30]:
            print(f"  [{b['text'][:60]}]  class={b['cls'][:60]}")

        # Body text sample
        body = await page.inner_text("body")
        print(f"\n=== BODY ({len(body)} chars) ===")
        print(body[:800])

        await browser.close()

asyncio.run(debug())