from .base import BaseCrawler


class Crawl4aiCrawler(BaseCrawler):
    """
    crawl4ai-based crawler — LLM-aware web crawler built on Playwright.
    Produces high-quality, clean Markdown optimised for LLM consumption.
    Handles JS rendering, lazy-load images, and dynamic content.

    Pros : Best Markdown quality, LLM-optimised, JS rendering, fit_markdown.
    Cons : Heavier than trafilatura; requires Chromium.

    Install:
        pip install crawl4ai
        crawl4ai-setup          # downloads Chromium + models
        # or manually: playwright install chromium
    """

    async def fetch_url(self, url: str) -> dict:
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
        except ImportError:
            raise RuntimeError(
                "crawl4ai is not installed. Run: pip install crawl4ai && crawl4ai-setup"
            )

        browser_cfg = BrowserConfig(headless=True, verbose=False)
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            page_timeout=60_000,
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        # Extract markdown — handle different crawl4ai API versions
        content = self._extract_markdown(result)

        # Extract title
        title = self._extract_title(result) or url

        return {
            "url": url,
            "title": title,
            "content_markdown": content,
            "backend": "crawl4ai",
        }

    def _extract_markdown(self, result) -> str:
        """Handle crawl4ai markdown across different API versions."""
        # v0.4+ : result.markdown is a MarkdownGenerationResult object
        if hasattr(result, "markdown") and result.markdown:
            md = result.markdown
            if hasattr(md, "fit_markdown") and md.fit_markdown:
                return md.fit_markdown
            if hasattr(md, "raw_markdown") and md.raw_markdown:
                return md.raw_markdown
            if isinstance(md, str):
                return md

        # Older versions: result.markdown_v2
        if hasattr(result, "markdown_v2") and result.markdown_v2:
            md = result.markdown_v2
            if hasattr(md, "fit_markdown") and md.fit_markdown:
                return md.fit_markdown
            if hasattr(md, "raw_markdown") and md.raw_markdown:
                return md.raw_markdown

        # Final fallback: cleaned HTML
        if hasattr(result, "cleaned_html") and result.cleaned_html:
            return result.cleaned_html

        return ""

    def _extract_title(self, result) -> str:
        """Extract page title from crawl4ai result."""
        if hasattr(result, "metadata") and result.metadata:
            meta = result.metadata
            for key in ("title", "og:title", "twitter:title"):
                val = meta.get(key)
                if val:
                    return str(val).strip()
        return ""
