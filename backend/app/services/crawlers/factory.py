import logging
from .base import BaseCrawler
from .trafilatura_crawler import TrafilaturaCrawler
from .playwright_crawler import PlaywrightCrawler
from .crawl4ai_crawler import Crawl4aiCrawler

logger = logging.getLogger(__name__)

# Registry of available backends
BACKENDS: dict[str, type[BaseCrawler]] = {
    "trafilatura": TrafilaturaCrawler,
    "playwright":  PlaywrightCrawler,
    "crawl4ai":    Crawl4aiCrawler,
}

DEFAULT_BACKEND = "trafilatura"


def get_crawler(backend: str | None = None) -> BaseCrawler:
    """
    Return a crawler instance for the given backend name.
    Falls back to trafilatura if the requested backend is unknown.

    Args:
        backend: "trafilatura" | "playwright" | "crawl4ai" | None
                 None → uses settings.CRAWLER_BACKEND from .env
    """
    from app.core.config import settings

    name = (backend or settings.CRAWLER_BACKEND or DEFAULT_BACKEND).lower().strip()

    if name not in BACKENDS:
        logger.warning(f"Unknown crawler backend '{name}', falling back to trafilatura")
        name = DEFAULT_BACKEND

    logger.debug(f"Using crawler backend: {name}")
    return BACKENDS[name]()
