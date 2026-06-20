# scraper/scrape.py
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from urllib.parse import urlparse

BASE = "https://tinpan.proteantech.in"

SEED_URLS = [
    f"{BASE}/",
    f"{BASE}/about-us",
    f"{BASE}/services/pan/pan-index",
    f"{BASE}/services/pan/pan-introduction",
    f"{BASE}/online-pan-verification",
    f"{BASE}/services/online-pan-verification/pan-verification-overview",
    f"{BASE}/services/etds-etcs",
    f"{BASE}/services/tan/tan-introduction",
    f"{BASE}/services/tan/tan-downloads",
    f"{BASE}/Facilitation-center",
    f"{BASE}/pan-center",
    f"{BASE}/tin-facilities",
    f"{BASE}/faq.html",
    f"{BASE}/services/pan/pan-index#faqs",
    f"{BASE}/services/tan/tan-introduction#faqs",
    f"{BASE}/online-pan-verification#faqs",
    f"{BASE}/services/etds-etcs#faqs",
    f"{BASE}/faqs/form-24q-q4/faq-form-fourth.html",
    f"{BASE}/faqs/air/faqairgeneral.html",
    f"{BASE}/faqs/SFT/faq-SFT.html",
    f"{BASE}/downloads/pan/downloads-pan.html",
    f"{BASE}/downloads/tan/tan-downloads.html",
    f"{BASE}/downloads/e-tds/eTDS-download-regular.html",
    f"{BASE}/downloads/e-tds/eTDS-download-corr.html",
    f"{BASE}/downloads/form-24g/form24g-download.html",
    f"{BASE}/nsdl-addresses",
    f"{BASE}/customerfeedback",
    f"{BASE}/privacy-policy",
    f"{BASE}/terms-and-condition.html",
    f"{BASE}/sitemap.html",
    f"{BASE}/publication-itd-rbi.html",
    f"{BASE}/related-link.html",
    f"{BASE}/services/pan/new-do-donts.html",
    f"{BASE}/services/pan/pan-aocode.html",
    f"{BASE}/faqs/pan/pan-introduction.html",
    f"{BASE}/faqs/e-tds/duplicate-receipt.html",
    f"{BASE}/services/etds-etcs/faqetds.html",
    f"{BASE}/services/online-pan-verification/faq-pan-verify.html",
    f"{BASE}/services/tan/tan-index.html",
]

# Skip these file types — not web pages
SKIP_EXTENSIONS = {
    ".pdf", ".zip", ".docx", ".xlsx", ".xls",
    ".doc", ".txt", ".rtf", ".jpg", ".png",
    ".mp4", ".avi", ".csv", ".ppt", ".pptx"
}

# Skip URLs containing these — external or non-content links
SKIP_KEYWORDS = [
    "youtube.com", "incometax.gov", "proteantech.in/paam",
    "tin.tin.protean", "onlineservices", "egov",
    "mailto:", "tel:", "javascript:",
    "EnhancedQRcodeApp", "feedback-form",
    "Sample-file", "Request_Letter", "Filers%20manual",
    "AIRDataStructure", "airrpu", "FMU", "duediligence",
    "link16", "link19",
]

# Max pages to crawl (safety limit)
MAX_PAGES = 80

OUTPUT_FILE = Path("scraper/scraped_data.json")


def is_valid_url(url: str) -> bool:
    if not url or not url.startswith(BASE):
        return False
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return False
    for keyword in SKIP_KEYWORDS:
        if keyword.lower() in url.lower():
            return False
    return True


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


async def dismiss_popup(page):
    try:
        btn = page.get_by_text("Continue", exact=True)
        if await btn.is_visible(timeout=4000):
            await btn.click()
            await asyncio.sleep(1)
    except:
        pass


async def expand_accordions(page):
    try:
        buttons = await page.locator(
            "button.flex.justify-between, button[class*='justify-between']"
        ).all()
        for btn in buttons:
            try:
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.3)
            except:
                pass
    except:
        pass


async def get_page_links(page) -> list[str]:
    try:
        links = await page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.href)"
        )
        valid = []
        for link in links:
            normalized = normalize_url(link)
            if is_valid_url(normalized):
                valid.append(normalized)
        return list(set(valid))
    except:
        return []


async def scrape_page(page, url: str) -> dict:
    print(f"  Scraping: {url}")
    try:
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await dismiss_popup(page)
        await expand_accordions(page)
        await asyncio.sleep(1)

      text = await page.eval_on_selector_all(
    "main, article, section, .content, #content, body",
    """
    els => {
        const el = els[0];
        if (!el) return '';
        ['nav','footer','header','script','style','noscript',
         'a[href]'].forEach(tag => {   // <-- also strip bare anchor-only elements
            el.querySelectorAll(tag).forEach(e => {
                // Replace anchor with its text content instead of removing
                if (tag === 'a[href]') {
                    e.replaceWith(document.createTextNode(e.innerText));
                } else {
                    e.remove();
                }
            });
        });
        return el.innerText.trim();
    }
    """
)

        body_text = text[0] if text else ""
        if len(body_text) < 100:
            body_text = await page.inner_text("body")

        links = await get_page_links(page)

        return {
            "url"  : url,
            "title": await page.title(),
            "text" : body_text,
            "chars": len(body_text),
            "links": links,
        }

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return {"url": url, "title": "", "text": "", "chars": 0, "links": []}


async def create_page(playwright):
    """Create a fresh browser and page."""
    browser = await playwright.firefox.launch(headless=False)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        viewport={"width": 1280, "height": 800},
    )
    page = await context.new_page()
    return browser, page


async def main():
    results = []
    visited = set()
    queue   = list(set([normalize_url(u) for u in SEED_URLS]))

    async with async_playwright() as p:
        browser, page = await create_page(p)

        # Warm up
        print("Warming up...")
        await page.goto(BASE, timeout=45000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await dismiss_popup(page)

        print(f"\nCrawling (max {MAX_PAGES} pages)...\n")

        while queue and len(visited) < MAX_PAGES:
            url = queue.pop(0)

            if url in visited:
                continue
            visited.add(url)

            # Try scraping — restart browser if it crashed
            try:
                result = await scrape_page(page, url)
            except Exception as e:
                print(f"  ⚠️  Browser crashed: {e}")
                print("  🔄 Restarting browser...")
                try:
                    await browser.close()
                except:
                    pass
                await asyncio.sleep(3)
                browser, page = await create_page(p)
                await page.goto(BASE, timeout=45000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                # Retry the same URL once
                try:
                    result = await scrape_page(page, url)
                except:
                    result = {"url": url, "title": "", "text": "", "chars": 0, "links": []}

            results.append(result)
            print(f"  ✅ {result['chars']} chars | {result['title'][:50]}")
            print(f"     Pages done: {len(visited)} | Queue: {len(queue)}")

            # Add new links to queue
            new_links = [l for l in result.get("links", []) if l not in visited]
            queue.extend(new_links)

            # Small pause between pages — prevents browser overload
            await asyncio.sleep(1)

        try:
            await browser.close()
        except:
            pass

    # Clean up and save
    for r in results:
        r.pop("links", None)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total  = sum(r["chars"] for r in results)
    failed = [r for r in results if r["chars"] < 100]

    print(f"\n{'='*50}")
    print(f"✅ Done — {len(results)} pages scraped")
    print(f"📝 Total chars: {total:,}")
    print(f"❌ Failed/empty: {len(failed)}")
    for f in failed:
        print(f"   - {f['url']}")
    print(f"💾 Saved to: {OUTPUT_FILE}")

asyncio.run(main())