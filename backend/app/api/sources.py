import os
import tempfile
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, HTTPException
from app.schemas.source import AddUrlRequest, CrawlerBackend
from app.schemas.common import JobCreated
from app.services.job_service import job_service
from app.jobs.runner import run_pending_jobs_once
from app.db.supabase_client import supabase
from app.core.config import settings
from app.services.crawlers.factory import BACKENDS

router = APIRouter(prefix="/api/sources", tags=["sources"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xlsm", ".txt", ".md"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB hard cap — prevents OOM on large uploads


@router.get("")
def list_sources(company_code: str | None = None):
    company_code = company_code or settings.DEFAULT_COMPANY_CODE
    res = supabase.table("knowledge_sources").select(
        "id,company_code,source_type,source_url,source_name,is_active,created_at"
    ).eq("company_code", company_code).order("created_at", desc=True).execute()
    return {"items": res.data or []}


@router.get("/backends")
def list_backends():
    """List available crawler backends and the current default."""
    return {
        "default": settings.CRAWLER_BACKEND,
        "available": list(BACKENDS.keys()),
        "descriptions": {
            "trafilatura": "Fast, lightweight — static HTML only. No browser required.",
            "playwright":  "Headless Chromium — renders JavaScript. Requires: playwright install chromium",
            "crawl4ai":    "LLM-aware crawler on Playwright — best Markdown quality. Requires: crawl4ai-setup",
        },
    }


@router.get("/{source_id}/pages")
def list_source_pages(source_id: str):
    res = supabase.table("source_pages").select(
        "id,title,url,content_hash,created_at,updated_at"
    ).eq("source_id", source_id).order("created_at", desc=True).execute()
    return {"items": res.data or []}


@router.post("/fix-chunk-titles")
async def fix_chunk_titles(company_code: str | None = None):
    """
    Back-fill enriched titles on existing document_chunks.

    Reads every distinct source_url from document_chunks, applies the same
    URL-path enrichment logic used at ingest time, then bulk-updates chunks
    whose current title is still the generic page title (e.g. 'Deves').

    Safe to call multiple times — skips URLs where the title is already
    enriched (contains ' (').
    """
    from app.pipeline.ingest_pipeline import ingest_pipeline

    company_code = company_code or settings.DEFAULT_COMPANY_CODE

    # 1. Fetch all distinct (source_url, title) pairs for this company
    rows = (
        supabase.table("document_chunks")
        .select("source_url,title")
        .eq("company_code", company_code)
        .execute()
        .data or []
    )

    # Deduplicate by source_url, keep first title seen
    url_title: dict[str, str] = {}
    for r in rows:
        url = r.get("source_url") or ""
        if url and url not in url_title:
            url_title[url] = r.get("title") or ""

    updated_urls: list[str] = []
    skipped_urls: list[str] = []

    for url, current_title in url_title.items():
        # Skip if already enriched (has ' (' from a previous run or file:// URLs)
        if " (" in current_title or url.startswith("file://"):
            skipped_urls.append(url)
            continue

        enriched = ingest_pipeline._enrich_title(current_title, [url])
        if enriched == current_title:
            skipped_urls.append(url)
            continue

        # Bulk-update all chunks for this URL
        supabase.table("document_chunks").update(
            {"title": enriched}
        ).eq("company_code", company_code).eq("source_url", url).execute()
        updated_urls.append(url)

    return {
        "ok": True,
        "updated": len(updated_urls),
        "skipped": len(skipped_urls),
        "updated_urls": updated_urls,
    }


@router.post("/clean-chunk-content")
async def clean_chunk_content(company_code: str | None = None):
    """
    Strip soft hyphens, lone surrogates, and other invisible characters
    from existing document_chunks.content that were injected by websites
    during crawling and break Thai substring matching.

    Fetches chunks whose content contains the U+00AD soft hyphen (most
    common offender), cleans them with clean_text(), and writes back.
    Safe to run multiple times.
    """
    from app.core.text import clean_text

    company_code = company_code or settings.DEFAULT_COMPANY_CODE

    # Supabase REST doesn't support LIKE on binary content directly,
    # so we fetch all chunks and filter in Python.  For large datasets
    # this could be batched, but typical deployments are small.
    rows = (
        supabase.table("document_chunks")
        .select("id,content")
        .eq("company_code", company_code)
        .execute()
        .data or []
    )

    cleaned_count = 0
    for row in rows:
        original = row.get("content") or ""
        cleaned = clean_text(original)
        if cleaned != original:
            supabase.table("document_chunks").update(
                {"content": cleaned}
            ).eq("id", row["id"]).execute()
            cleaned_count += 1

    return {
        "ok": True,
        "total_checked": len(rows),
        "cleaned": cleaned_count,
    }


@router.delete("/{source_id}")
def delete_source(source_id: str):
    res = supabase.table("knowledge_sources").select("id").eq("id", source_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Source not found")
    supabase.table("knowledge_sources").update({"is_active": False}).eq("id", source_id).execute()
    return {"ok": True, "message": "Source deactivated"}


@router.post("/url", response_model=JobCreated)
async def add_url(req: AddUrlRequest, background_tasks: BackgroundTasks):
    """
    Ingest a URL into the knowledge base.

    - **crawler_backend**: override which crawler to use for this request.
      Options: `trafilatura` (default), `playwright`, `crawl4ai`
    """
    company_code = req.company_code or settings.DEFAULT_COMPANY_CODE
    backend = req.crawler_backend or settings.CRAWLER_BACKEND

    job_id = job_service.create_job(
        "ingest_url",
        {
            "url": str(req.url),
            "run_deep_enrichment": req.run_deep_enrichment,
            "crawler_backend": backend,
        },
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

    # Read with hard size cap — prevents OOM from huge uploads
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content) // (1024*1024)} MB). Maximum allowed: 50 MB",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
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
