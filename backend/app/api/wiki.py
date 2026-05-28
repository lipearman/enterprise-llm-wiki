from fastapi import APIRouter
from app.db.supabase_client import supabase
from app.core.config import settings

router = APIRouter(prefix="/api/wiki", tags=["wiki"])

@router.get("/pages")
def list_pages(company_code: str | None = None):
    company_code = company_code or settings.DEFAULT_COMPANY_CODE
    res = supabase.table("wiki_pages").select("id,company_code,title,slug,summary,status,version,created_at").eq("company_code", company_code).order("created_at", desc=True).execute()
    return {"items": res.data or []}

@router.get("/pages/{page_id}")
def get_page(page_id: str):
    res = supabase.table("wiki_pages").select("*").eq("id", page_id).single().execute()
    return res.data
