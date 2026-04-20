# tools/web.py
import httpx
from duckduckgo_search import DDGS

try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

async def web_search(query: str, max_results: int = 10) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))

async def fetch_page(url: str) -> str:
    """Fetch rendered HTML page using headless Chromium. Falls back to raw HTTP if playwright missing."""
    if not _PLAYWRIGHT_AVAILABLE:
        return f"[WARNING: Playwright not installed. Falling back to raw HTTP fetch.]\n{await fetch_raw(url)}"
        
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=15000)
            text = await page.inner_text("body")
            await browser.close()
            return text
    except Exception as e:
        return f"Error fetching page: {e}"

async def fetch_raw(url: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=10, follow_redirects=True)
        return r.text
