"""
API Key authentication middleware.

Reads the key from:
  - Authorization: Bearer <key>   (preferred — works with apiFetch wrapper)
  - X-API-Key: <key>              (fallback)

Public paths (no token required):
  GET  /
  GET  /api/health
  GET  /docs
  GET  /openapi.json
  GET  /redoc
  POST /api/auth/verify           (login endpoint itself)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import settings

# Paths that never require authentication
_PUBLIC_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/public/",   # floating-chat widget — no auth required
)
_PUBLIC_EXACT = {"/", "/api/health", "/api/auth/verify"}


def _is_public(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    for prefix in _PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("X-API-Key", "").strip() or None


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Auth completely disabled or no key configured
        if not settings.API_KEY_ENABLED or not settings.API_KEY:
            return await call_next(request)

        # Let CORS preflight pass through — browsers send OPTIONS without auth headers
        if request.method == "OPTIONS":
            return await call_next(request)

        # Allow public routes without a token
        if _is_public(request.url.path):
            return await call_next(request)

        token = _extract_token(request)
        if token != settings.API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized — invalid or missing API key"},
            )

        return await call_next(request)
