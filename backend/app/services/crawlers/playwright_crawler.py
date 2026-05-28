import trafilatura
from bs4 import BeautifulSoup
from .base import BaseCrawler


class PlaywrightCrawler(BaseCrawler):
    """
    Playwright-based crawler — launches a headless Chromium browser.
    Waits for JavaScript to finish rendering before extracting content.

    Pros : Renders JS-heavy pages (React/Vue/Next.js SPAs).
    Cons : Slower, requires 'playwright install chromium' on first use.

    Install:
        pip install playwright
        playwright install chromium
    """

    async def fetch_url(self, url: str) -> dict:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (compatible; LLM-Wiki-Bot/1.0)",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=60_000)
            except Exception:
                # fallback: accept even if networkidle times out
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            html = await page.content()
            title = (await page.title()) or ""
            await browser.close()

        # Extract clean markdown from fully-rendered HTML
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            output_format="markdown",
        )
        if not text:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text("\n", strip=True)

        # Fallback title from HTML if page.title() was empty
        if not title:
            soup = BeautifulSoup(html, "html.parser")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

        return {
            "url": url,
            "title": title or url,
            "content_markdown": text or "",
            "backend": "playwright",
        }
