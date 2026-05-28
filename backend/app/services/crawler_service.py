import trafilatura
from bs4 import BeautifulSoup
import httpx


class CrawlerService:
    async def fetch_url(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text

        title = self._extract_title(html) or url
        text = trafilatura.extract(html, include_comments=False, include_tables=True, output_format="markdown")
        if not text:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text("\n")
        return {"url": url, "title": title, "content_markdown": text or ""}

    def _extract_title(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return None

crawler_service = CrawlerService()
