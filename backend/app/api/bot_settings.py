from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.core.config import settings
from app.services.bot_settings_service import bot_settings_service

router = APIRouter(prefix="/api/bot-settings", tags=["bot-settings"])


class SaveRequest(BaseModel):
    company_code: str
    key: str
    value: Any


@router.get("")
def get_all_settings(company_code: str | None = None):
    """Return all bot settings for the given company (defaults to DEFAULT_COMPANY_CODE)."""
    code = company_code or settings.DEFAULT_COMPANY_CODE
    return {"company_code": code, "settings": bot_settings_service.get_all(code)}


@router.put("")
def save_setting(body: SaveRequest):
    """Persist one setting and update the in-memory cache."""
    try:
        bot_settings_service.save(body.company_code, body.key, body.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "key": body.key}


@router.post("/reload")
def reload_settings(company_code: str | None = None):
    """Force-reload settings from DB (useful after direct DB edits)."""
    code = company_code or settings.DEFAULT_COMPANY_CODE
    bot_settings_service.reload(code)
    return {"ok": True, "company_code": code}
