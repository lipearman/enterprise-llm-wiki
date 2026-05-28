from abc import ABC, abstractmethod


class BaseCrawler(ABC):
    """Abstract base class for all crawler backends."""

    @abstractmethod
    async def fetch_url(self, url: str) -> dict:
        """
        Fetch a URL and return extracted content.

        Returns:
            dict with keys:
                - url: str
                - title: str
                - content_markdown: str
                - backend: str  (name of the crawler used)
        """
        ...
