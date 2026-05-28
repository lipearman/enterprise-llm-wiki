import httpx
import trafilatura
from bs4 import BeautifulSoup
from .base import BaseCrawler


class TrafilaturaCrawler(BaseCrawler):
    """
    Default lightweight crawler.
    Uses httpx to fetch HTML, then trafilatura to extract clean markdown.
    Falls back to BeautifulSoup if trafilatura yields nothing.

    Pros : Fast, no browser required, low resource usage.
    Cons : Cannot render JavaScript — static HTML only.
    """

    async def fetch_url(self, url: str) -> dict:
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LLM-Wiki-Bot/1.0)"},
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text

        title = self._extract_title(html) or url
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

        return {
            "url": url,
            "title": title,
            "content_markdown": text or "",
            "backend": "trafilatura",
        }

    def _extract_title(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return og["content"].strip()
        return None
