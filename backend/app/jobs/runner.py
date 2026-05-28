import asyncio
from app.db.supabase_client import supabase
from app.pipeline.ingest_pipeline import ingest_pipeline
from app.services.job_service import job_service
from app.core.logging import logger


async def run_pending_jobs_once(limit: int = 5) -> None:
    res = supabase.table("job_runs").select("*").eq("status", "pending").limit(limit).execute()
    for job in res.data or []:
        await run_job(job)


async def run_job(job: dict) -> None:
    job_id = job["id"]
    try:
        job_service.update_job(job_id, "processing")

        if job["job_type"] == "ingest_url":
            payload = job.get("payload") or {}
            result = await ingest_pipeline.ingest_url(
                payload["url"],
                job.get("company_code"),
                payload.get("run_deep_enrichment", True),
                crawler_backend=payload.get("crawler_backend"),
            )
            supabase.table("job_runs").update({"status": "completed", "result": result}).eq("id", job_id).execute()

        elif job["job_type"] == "crawl_all":
            result = await _do_crawl_all(job.get("company_code"))
            supabase.table("job_runs").update({"status": "completed", "result": result}).eq("id", job_id).execute()

        else:
            job_service.update_job(job_id, "failed", f"Unknown job_type: {job['job_type']}")

    except Exception as ex:
        logger.exception(f"Job {job_id} failed")
        job_service.update_job(job_id, "failed", str(ex))


async def _do_crawl_all(company_code: str | None = None) -> dict:
    """Re-ingest all active URL sources. Skips unchanged pages (content hash check in pipeline)."""
    query = supabase.table("knowledge_sources").select("*").eq("is_active", True).eq("source_type", "url")
    if company_code:
        query = query.eq("company_code", company_code)
    res = query.execute()
    sources = res.data or []

    ok, skipped, failed = 0, 0, 0
    for src in sources:
        url = src.get("source_url")
        if not url:
            skipped += 1
            continue
        try:
            await ingest_pipeline.ingest_url(url, src["company_code"], run_deep_enrichment=True)
            ok += 1
            logger.info(f"Crawled: {url}")
        except Exception as e:
            failed += 1
            logger.warning(f"Crawl failed for {url}: {e}")

    result = {"ok": ok, "skipped": skipped, "failed": failed, "total": len(sources)}
    logger.info(f"Crawl all done: {result}")
    return result


async def crawl_all_sources() -> None:
    """APScheduler entry point — daily crawl of all companies."""
    logger.info("Scheduled daily crawl starting…")
    try:
        result = await _do_crawl_all()
        logger.info(f"Daily crawl finished: {result}")
    except Exception as e:
        logger.error(f"Daily crawl error: {e}")


if __name__ == "__main__":
    asyncio.run(run_pending_jobs_once())
