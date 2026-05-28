from pydantic import BaseModel

class WikiPage(BaseModel):
    id: str
    company_code: str
    title: str
    slug: str
    summary: str | None = None
    content_markdown: str
    status: str = "draft"
    version: int = 1
