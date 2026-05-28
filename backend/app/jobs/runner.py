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
            )
            supabase.table("job_runs").update({"status": "completed", "result": result}).eq("id", job_id).execute()
        else:
            job_service.update_job(job_id, "failed", f"Unknown job_type: {job['job_type']}")
    except Exception as ex:
        logger.exception("job failed")
        job_service.update_job(job_id, "failed", str(ex))


if __name__ == "__main__":
    asyncio.run(run_pending_jobs_once())
