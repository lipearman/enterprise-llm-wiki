"""
crawler_service.py — thin façade over the crawler backends.

Usage:
    from app.services.crawler_service import crawler_service
    doc = await crawler_service.fetch_url(url)                        # uses .env default
    doc = await crawler_service.fetch_url(url, backend="playwright")  # explicit override

All calls go through BaseCrawler.fetch_with_retry() which handles:
  • Exponential back-off on transient network errors (1 s, 3 s)
  • Immediate re-raise on permanent errors (404, 403, invalid URL)
"""
from app.services.crawlers.factory import get_crawler


class CrawlerService:
    async def fetch_url(self, url: str, backend: str | None = None) -> dict:
        """
        Fetch a URL using the specified (or default) crawler backend.
        Retries automatically on transient network failures.

        Args:
            url     : Target URL to crawl.
            backend : "trafilatura" | "playwright" | "crawl4ai" | None
                      None → reads CRAWLER_BACKEND from .env

        Returns:
            dict with keys: url, title, content_markdown, backend

        Raises:
            CrawlerError if all retry attempts are exhausted or error is permanent.
        """
        crawler = get_crawler(backend)
        return await crawler.fetch_with_retry(url)


crawler_service = CrawlerService()
