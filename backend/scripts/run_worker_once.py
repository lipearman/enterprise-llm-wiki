import asyncio
from app.jobs.runner import run_pending_jobs_once

asyncio.run(run_pending_jobs_once(limit=10))
