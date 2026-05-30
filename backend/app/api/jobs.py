from fastapi import APIRouter, BackgroundTasks, Request
from app.db.supabase_client import supabase
from app.jobs.runner import run_pending_jobs_once, crawl_all_sources
from app.services.job_service import job_service
from app.core.config import settings
from app.services.audit_service import audit_log

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    limit: int = 50,
    status: str | None = None,
    company_code: str | None = None,
):
    query = supabase.table("job_runs").select("*")
    if status:
        query = query.eq("status", status)
    if company_code:
        query = query.eq("company_code", company_code)
    res = query.order("created_at", desc=True).limit(limit).execute()
    return {"items": res.data or []}


@router.get("/{job_id}")
def get_job(job_id: str):
    res = supabase.table("job_runs").select("*").eq("id", job_id).single().execute()
    return res.data


@router.post("/run-pending")
async def run_pending(background_tasks: BackgroundTasks, request: Request):
    background_tasks.add_task(run_pending_jobs_once, 10)
    audit_log("job.run_pending", request=request)
    return {"ok": True, "message": "Running pending jobs in background"}


@router.post("/crawl-all")
async def trigger_crawl_all(background_tasks: BackgroundTasks, request: Request, company_code: str | None = None):
    """Manually trigger crawl of all active sources."""
    company_code = company_code or settings.DEFAULT_COMPANY_CODE
    job_id = job_service.create_job("crawl_all", {}, company_code)
    background_tasks.add_task(crawl_all_sources)
    audit_log("job.crawl_all", request=request, company_code=company_code, detail={"job_id": job_id})
    return {"ok": True, "job_id": job_id, "message": "Crawl started in background"}


@router.delete("/{job_id}")
def delete_job(job_id: str):
    supabase.table("job_runs").delete().eq("id", job_id).execute()
    return {"ok": True}
