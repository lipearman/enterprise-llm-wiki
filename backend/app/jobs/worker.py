"""
Background job worker — standalone entrypoint.

Polls the job_runs table every WORKER_POLL_SECONDS and executes any pending
jobs. Runs as its own long-lived process (the API process keeps its in-process
APScheduler separate). On Railway this is a second service that shares the
backend image but overrides the start command to `python -m app.jobs.worker`.

Locally (docker-compose) the same loop is defined inline in the compose file;
this module is the clean, importable equivalent.
"""

import asyncio
import os

from app.core.logging import logger
from app.jobs.runner import run_pending_jobs_once

POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "10"))
BATCH = int(os.getenv("WORKER_BATCH", "5"))


async def _loop() -> None:
    logger.info("Worker started — polling job_runs every %ss (batch=%s)", POLL_SECONDS, BATCH)
    while True:
        try:
            await run_pending_jobs_once(BATCH)
        except Exception as exc:  # never let one bad poll kill the worker
            logger.error("Worker poll error: %s", exc)
        await asyncio.sleep(POLL_SECONDS)


def main() -> None:
    try:
        asyncio.run(_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopped")


if __name__ == "__main__":
    main()
