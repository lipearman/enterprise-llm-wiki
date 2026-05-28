from fastapi import APIRouter, BackgroundTasks
from app.schemas.source import AddUrlRequest
from app.schemas.common import JobCreated
from app.services.job_service import job_service
from app.jobs.runner import run_pending_jobs_once
from app.core.config import settings

router = APIRouter(prefix="/api/sources", tags=["sources"])

@router.post("/url", response_model=JobCreated)
async def add_url(req: AddUrlRequest, background_tasks: BackgroundTasks):
    company_code = req.company_code or settings.DEFAULT_COMPANY_CODE
    job_id = job_service.create_job("ingest_url", {"url": str(req.url), "run_deep_enrichment": req.run_deep_enrichment}, company_code)
    background_tasks.add_task(run_pending_jobs_once, 1)
    return JobCreated(job_id=job_id, status="pending")
