from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    """
    Shallow health check used by Docker healthcheck and load-balancers.
    Tests Supabase connectivity — returns 503 if the DB is unreachable
    so that dependent containers (worker, frontend) don't start against a dead backend.
    """
    db_ok = _ping_db()
    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": db_ok,
            "db": db_ok,
            "app": settings.APP_NAME,
            "version": "0.2.0",
            "env": settings.APP_ENV,
        },
    )


def _ping_db() -> bool:
    """Quick row-count query against a small table — fails fast if Supabase is unreachable."""
    try:
        from app.db.supabase_client import supabase
        supabase.table("companies").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.warning(f"Health DB ping failed: {e}")
        return False
