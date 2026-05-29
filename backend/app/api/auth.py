from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class VerifyRequest(BaseModel):
    api_key: str


class VerifyResponse(BaseModel):
    ok: bool
    message: str


@router.post("/verify", response_model=VerifyResponse)
def verify_api_key(body: VerifyRequest):
    """
    Validate an API key.  Returns {ok: true} on success.
    Called by the frontend login page before storing the key in sessionStorage.
    This endpoint is always public (no auth middleware checks it).
    """
    if not settings.API_KEY_ENABLED or not settings.API_KEY:
        # Auth is disabled — any key (even empty) is accepted
        return VerifyResponse(ok=True, message="auth_disabled")

    if body.api_key == settings.API_KEY:
        return VerifyResponse(ok=True, message="ok")

    raise HTTPException(status_code=401, detail="Invalid API key")
