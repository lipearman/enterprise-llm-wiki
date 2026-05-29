import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CrawlerError(Exception):
    """
    Raised by any crawler backend when fetching fails.

    Attributes:
        retryable  – True for transient errors (timeout, 5xx, connection reset).
                     False for permanent errors (404, 403, invalid URL).
        status_code – HTTP status code if available, otherwise None.
    """

    def __init__(self, message: str, retryable: bool = True, status_code: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class BaseCrawler(ABC):
    """Abstract base class for all crawler backends."""

    # Exponential back-off delays between retries (seconds)
    _RETRY_DELAYS: tuple[float, ...] = (1.0, 3.0)

    @abstractmethod
    async def fetch_url(self, url: str) -> dict:
        """
        Fetch a URL and return extracted content.

        Returns:
            dict with keys:
                url              : str — the fetched URL
                title            : str — page title
                content_markdown : str — extracted markdown text
                backend          : str — name of this crawler
        Raises:
            CrawlerError on any fetch failure.
        """
        ...

    async def fetch_with_retry(self, url: str) -> dict:
        """
        Call fetch_url() with automatic retry on transient (retryable) errors.

        Attempts: 1 initial + up to len(_RETRY_DELAYS) retries.
        Uses the delays in _RETRY_DELAYS between each attempt.
        Non-retryable errors are re-raised immediately (no retry).
        """
        max_attempts = 1 + len(self._RETRY_DELAYS)
        last_exc: CrawlerError | None = None

        for attempt in range(max_attempts):
            try:
                return await self.fetch_url(url)

            except CrawlerError as exc:
                last_exc = exc
                if not exc.retryable:
                    logger.warning(f"[{self.__class__.__name__}] Non-retryable error for {url}: {exc}")
                    raise

                if attempt < len(self._RETRY_DELAYS):
                    delay = self._RETRY_DELAYS[attempt]
                    logger.warning(
                        f"[{self.__class__.__name__}] Attempt {attempt + 1}/{max_attempts} failed "
                        f"for {url}: {exc} — retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{self.__class__.__name__}] All {max_attempts} attempts failed for {url}: {exc}")

        # All attempts exhausted
        raise last_exc  # type: ignore[misc]
