import asyncio
from app.db.supabase_client import supabase
from app.pipeline.ingest_pipeline import ingest_pipeline
from app.services.job_service import job_service
from app.core.logging import logger

# A job is retried up to MAX_JOB_RETRIES times before being permanently failed.
# Delays between the worker's poll cycles already provide spacing; these delays
# are added on top when re-queuing a failed attempt.
MAX_JOB_RETRIES = 3
_RETRY_DELAYS = (5, 15, 30)   # seconds to sleep before re-queuing: attempt 1, 2, 3


async def run_pending_jobs_once(limit: int = 5) -> None:
    """Pick up to `limit` pending jobs and run them sequentially."""
    res = (
        supabase.table("job_runs")
        .select("*")
        .eq("status", "pending")
        .order("created_at")   # FIFO
        .limit(limit)
        .execute()
    )
    for job in res.data or []:
        await run_job(job)


async def run_job(job: dict) -> None:
    """Execute a single job with automatic retry on failure."""
    job_id = job["id"]
    retry_count: int = job.get("retry_count", 0)

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
            supabase.table("job_runs").update(
                {"status": "completed", "result": result}
            ).eq("id", job_id).execute()

        elif job["job_type"] == "crawl_all":
            result = await _do_crawl_all(job.get("company_code"))
            supabase.table("job_runs").update(
                {"status": "completed", "result": result}
            ).eq("id", job_id).execute()

        else:
            # Unknown job type — permanent failure, don't retry
            job_service.update_job(job_id, "failed", f"Unknown job_type: {job['job_type']}")

    except Exception as exc:
        logger.exception(f"Job {job_id} failed (attempt {retry_count + 1}/{MAX_JOB_RETRIES}): {exc}")

        new_retry_count = retry_count + 1

        if new_retry_count < MAX_JOB_RETRIES:
            # Schedule a retry: sleep briefly then reset to pending
            delay = _RETRY_DELAYS[min(retry_count, len(_RETRY_DELAYS) - 1)]
            logger.info(f"Job {job_id} will retry in {delay}s (attempt {new_retry_count + 1}/{MAX_JOB_RETRIES})")
            await asyncio.sleep(delay)
            supabase.table("job_runs").update(
                {
                    "status": "pending",
                    "retry_count": new_retry_count,
                    "message": f"Retry {new_retry_count}/{MAX_JOB_RETRIES}: {exc}",
                }
            ).eq("id", job_id).execute()
        else:
            # Exhausted all retries — mark permanently failed
            logger.error(f"Job {job_id} permanently failed after {MAX_JOB_RETRIES} attempts")
            supabase.table("job_runs").update(
                {
                    "status": "failed",
                    "retry_count": new_retry_count,
                    "message": str(exc),
                }
            ).eq("id", job_id).execute()


async def _do_crawl_all(company_code: str | None = None) -> dict:
    """Re-ingest all active URL sources. Skips unchanged pages (content hash check)."""
    query = (
        supabase.table("knowledge_sources")
        .select("*")
        .eq("is_active", True)
        .eq("source_type", "url")
    )
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
