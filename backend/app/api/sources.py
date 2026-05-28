import os
import tempfile
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, HTTPException
from app.schemas.source import AddUrlRequest
from app.schemas.common import JobCreated
from app.services.job_service import job_service
from app.jobs.runner import run_pending_jobs_once
from app.db.supabase_client import supabase
from app.core.config import settings

router = APIRouter(prefix="/api/sources", tags=["sources"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xlsm", ".txt", ".md"}


@router.get("")
def list_sources(company_code: str | None = None):
    company_code = company_code or settings.DEFAULT_COMPANY_CODE
    res = supabase.table("knowledge_sources").select(
        "id,company_code,source_type,source_url,source_name,is_active,created_at"
    ).eq("company_code", company_code).order("created_at", desc=True).execute()
    return {"items": res.data or []}


@router.get("/{source_id}/pages")
def list_source_pages(source_id: str):
    res = supabase.table("source_pages").select(
        "id,title,url,content_hash,created_at,updated_at"
    ).eq("source_id", source_id).order("created_at", desc=True).execute()
    return {"items": res.data or []}


@router.delete("/{source_id}")
def delete_source(source_id: str):
    res = supabase.table("knowledge_sources").select("id").eq("id", source_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Source not found")
    supabase.table("knowledge_sources").update({"is_active": False}).eq("id", source_id).execute()
    return {"ok": True, "message": "Source deactivated"}


@router.post("/url", response_model=JobCreated)
async def add_url(req: AddUrlRequest, background_tasks: BackgroundTasks):
    company_code = req.company_code or settings.DEFAULT_COMPANY_CODE
    job_id = job_service.create_job(
        "ingest_url",
        {"url": str(req.url), "run_deep_enrichment": req.run_deep_enrichment},
        company_code,
    )
    background_tasks.add_task(run_pending_jobs_once, 1)
    return JobCreated(job_id=job_id, status="pending")


@router.post("/file", response_model=JobCreated)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_code: str = Form(default=None),
    run_deep_enrichment: bool = Form(default=True),
):
    """Upload a file (PDF, DOCX, XLSX, TXT, MD) for ingestion."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    company_code = company_code or settings.DEFAULT_COMPANY_CODE

    # Save uploaded content to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    job_id = job_service.create_job(
        "ingest_url",
        {"url": f"file://{tmp_path}", "run_deep_enrichment": run_deep_enrichment, "_filename": file.filename},
        company_code,
    )
    background_tasks.add_task(_run_file_ingest, tmp_path, company_code, run_deep_enrichment, job_id)
    return JobCreated(job_id=job_id, status="pending")


async def _run_file_ingest(tmp_path: str, company_code: str, run_deep_enrichment: bool, job_id: str) -> None:
    from app.pipeline.ingest_pipeline import ingest_pipeline
    try:
        supabase.table("job_runs").update({"status": "processing"}).eq("id", job_id).execute()
        result = await ingest_pipeline.ingest_file(tmp_path, company_code, run_deep_enrichment)
        supabase.table("job_runs").update({"status": "completed", "result": result}).eq("id", job_id).execute()
    except Exception as e:
        supabase.table("job_runs").update({"status": "failed", "message": str(e)}).eq("id", job_id).execute()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
