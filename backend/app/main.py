from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api.chat import router as chat_router
from app.api.sources import router as sources_router
from app.api.wiki import router as wiki_router
from app.api.jobs import router as jobs_router
from app.api.health import router as health_router
from app.api.companies import router as companies_router


def _start_scheduler():
    """Start APScheduler for daily crawl job."""
    if not settings.ENABLE_SCHEDULER:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER=false)")
        return None
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from app.jobs.runner import crawl_all_sources

        scheduler = AsyncIOScheduler(timezone="Asia/Bangkok")
        scheduler.add_job(
            crawl_all_sources,
            trigger="cron",
            hour=settings.DAILY_CRAWL_CRON_HOUR,
            minute=settings.DAILY_CRAWL_CRON_MINUTE,
            id="daily_crawl",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            f"Scheduler started — daily crawl at "
            f"{settings.DAILY_CRAWL_CRON_HOUR:02d}:{settings.DAILY_CRAWL_CRON_MINUTE:02d} BKK"
        )
        return scheduler
    except Exception as e:
        logger.error(f"Scheduler failed to start: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = _start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


app = FastAPI(title=settings.APP_NAME, version="0.2.0", lifespan=lifespan)

origins = ["*"] if settings.ALLOW_ORIGINS == "*" else [x.strip() for x in settings.ALLOW_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(sources_router)
app.include_router(wiki_router)
app.include_router(jobs_router)
app.include_router(companies_router)


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "version": "0.2.0", "docs": "/docs"}
