from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.core.config import settings
from app.services.audit_service import audit_log

router = APIRouter(prefix="/api/auth", tags=["auth"])


class VerifyRequest(BaseModel):
    api_key: str


class VerifyResponse(BaseModel):
    ok: bool
    message: str


@router.post("/verify", response_model=VerifyResponse)
def verify_api_key(body: VerifyRequest, request: Request):
    """
    Validate an API key.  Returns {ok: true} on success.
    Called by the frontend login page before storing the key in sessionStorage.
    This endpoint is always public (no auth middleware checks it).
    """
    if not settings.API_KEY_ENABLED or not settings.API_KEY:
        audit_log("auth.login", request=request, detail={"result": "auth_disabled"})
        return VerifyResponse(ok=True, message="auth_disabled")

    if body.api_key == settings.API_KEY:
        audit_log("auth.login", request=request, detail={"result": "ok"})
        return VerifyResponse(ok=True, message="ok")

    audit_log(
        "auth.login",
        request=request,
        status="fail",
        status_code=401,
        detail={"result": "invalid_key"},
    )
    raise HTTPException(status_code=401, detail="Invalid API key")
