from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase_client import supabase

router = APIRouter(prefix="/api/companies", tags=["companies"])


class CompanyCreate(BaseModel):
    company_code: str
    company_name: str
    description: str | None = None


@router.get("")
def list_companies():
    res = supabase.table("companies").select("*").order("company_code").execute()
    return {"items": res.data or []}


@router.post("")
def create_company(body: CompanyCreate):
    res = supabase.table("companies").upsert({
        "company_code": body.company_code.upper(),
        "company_name": body.company_name,
        "description": body.description,
        "is_active": True,
    }, on_conflict="company_code").execute()
    return res.data[0] if res.data else {"ok": True}


@router.delete("/{company_code}")
def deactivate_company(company_code: str):
    res = supabase.table("companies").select("company_code").eq("company_code", company_code.upper()).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Company not found")
    supabase.table("companies").update({"is_active": False}).eq("company_code", company_code.upper()).execute()
    return {"ok": True, "message": f"{company_code} deactivated"}
