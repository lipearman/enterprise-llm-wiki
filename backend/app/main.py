from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import logger
from app.core.auth import ApiKeyMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.api.chat import router as chat_router
from app.api.sources import router as sources_router
from app.api.wiki import router as wiki_router
from app.api.jobs import router as jobs_router
from app.api.health import router as health_router
from app.api.companies import router as companies_router
from app.api.auth import router as auth_router
from app.api.public_chat import router as public_chat_router
from app.api.unanswered import router as unanswered_router


# ── Startup validation ────────────────────────────────────────────────────────

def _warn_insecure_config() -> None:
    """Log loud warnings for production-unsafe configuration."""
    issues = []

    if settings.API_KEY_ENABLED:
        if not settings.API_KEY:
            issues.append("API_KEY is empty — authentication is effectively disabled")
        elif settings.API_KEY.lower().startswith("changeme"):
            issues.append("API_KEY is still set to the default placeholder — change it before going to production")

    if settings.ALLOW_ORIGINS == "*":
        issues.append("ALLOW_ORIGINS=* permits requests from any origin — restrict to your frontend domain in production")

    if settings.DEBUG and settings.APP_ENV == "production":
        issues.append("DEBUG=true with APP_ENV=production — disable DEBUG in production")

    for issue in issues:
        logger.warning(f"⚠️  SECURITY: {issue}")


# ── Scheduler ─────────────────────────────────────────────────────────────────

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


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _warn_insecure_config()
    scheduler = _start_scheduler()
    logger.info(f"🚀 {settings.APP_NAME} v0.2.0 started (env={settings.APP_ENV})")
    yield
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title=settings.APP_NAME, version="0.2.0", lifespan=lifespan)

origins = ["*"] if settings.ALLOW_ORIGINS == "*" else [x.strip() for x in settings.ALLOW_ORIGINS.split(",")]

# Middleware execution order (Starlette runs last-added first):
#   RateLimitMiddleware  → enforced first, before auth or business logic
#   ApiKeyMiddleware     → auth check
#   CORSMiddleware       → CORS headers (innermost, wraps the actual route)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(RateLimitMiddleware)


# ── Global exception handler ──────────────────────────────────────────────────
# Catches any unhandled exception and returns a clean 500 JSON response.
# In DEBUG mode the error message is included; in production it is hidden
# to prevent leaking internal implementation details.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {request.method} {request.url.path} — {exc}")
    detail = str(exc) if settings.DEBUG else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(public_chat_router)   # public — no auth required
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(sources_router)
app.include_router(wiki_router)
app.include_router(jobs_router)
app.include_router(companies_router)
app.include_router(unanswered_router)


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "version": "0.2.0", "docs": "/docs"}
