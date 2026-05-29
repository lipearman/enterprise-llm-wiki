import asyncio
from .base import BaseCrawler, CrawlerError


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
        # or manually: patchright install chromium
    """

    async def fetch_url(self, url: str) -> dict:
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
        except ImportError:
            raise CrawlerError(
                "crawl4ai is not installed. Run: pip install crawl4ai && patchright install chromium",
                retryable=False,
            )

        try:
            browser_cfg = BrowserConfig(headless=True, verbose=False)
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_until="networkidle",
                page_timeout=60_000,
            )

            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)

        except asyncio.TimeoutError as exc:
            raise CrawlerError(f"crawl4ai timeout for {url}", retryable=True) from exc

        except CrawlerError:
            raise

        except Exception as exc:
            err_msg = str(exc).lower()
            retryable = any(kw in err_msg for kw in ("timeout", "connection", "network", "socket", "reset"))
            raise CrawlerError(
                f"crawl4ai error for {url}: {exc}",
                retryable=retryable,
            ) from exc

        # Validate result
        if result is None or not getattr(result, "success", True) is not False:
            # crawl4ai sets result.success = False on hard failures
            success = getattr(result, "success", True)
            if success is False:
                err = getattr(result, "error_message", "unknown crawl4ai error")
                raise CrawlerError(f"crawl4ai reported failure for {url}: {err}", retryable=True)

        content = self._extract_markdown(result)
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
