from pydantic import BaseModel, HttpUrl
from typing import Optional

class AddUrlRequest(BaseModel):
    url: HttpUrl
    company_code: Optional[str] = None
    source_name: Optional[str] = None
    run_deep_enrichment: bool = True

class SourceItem(BaseModel):
    id: str
    company_code: str
    source_type: str
    source_url: str | None = None
    source_name: str | None = None
    is_active: bool = True
