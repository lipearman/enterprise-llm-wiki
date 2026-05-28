from pydantic import BaseModel, HttpUrl
from typing import Literal, Optional

CrawlerBackend = Literal["trafilatura", "playwright", "crawl4ai"]


class AddUrlRequest(BaseModel):
    url: HttpUrl
    company_code: Optional[str] = None
    source_name: Optional[str] = None
    run_deep_enrichment: bool = True
    crawler_backend: Optional[CrawlerBackend] = None  # None = use .env default


class SourceItem(BaseModel):
    id: str
    company_code: str
    source_type: str
    source_url: str | None = None
    source_name: str | None = None
    is_active: bool = True
