from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["health"])

@router.get("/api/health")
def health():
    return {"ok": True, "app": settings.APP_NAME, "env": settings.APP_ENV}
