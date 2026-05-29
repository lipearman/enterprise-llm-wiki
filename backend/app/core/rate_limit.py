"""
Rate limiting middleware — sliding-window, in-memory, zero dependencies.

Per-IP limits (requests / window_seconds):

  Path prefix              Limit   Window   Reason
  ─────────────────────────────────────────────────────────────────────
  /api/chat                20      60 s     LLM call — most expensive
  /api/sources/url         10      60 s     triggers a crawl job
  /api/sources/file         5      60 s     file upload + ingest
  everything else          120     60 s     read-heavy endpoints

Works correctly with a single Uvicorn worker (asyncio — single-threaded).
For multi-worker deployments, replace _windows with a Redis-backed counter.
"""

from collections import defaultdict
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse

# (path_prefix, limit, window_seconds)
_RULES: list[tuple[str, int, float]] = [
    ("/api/chat",          20,  60.0),
    ("/api/sources/url",   10,  60.0),
    ("/api/sources/file",   5,  60.0),
]
_DEFAULT_LIMIT  = 120
_DEFAULT_WINDOW = 60.0


def _get_limit(path: str) -> tuple[int, float]:
    for prefix, lim, win in _RULES:
        if path.startswith(prefix):
            return lim, win
    return _DEFAULT_LIMIT, _DEFAULT_WINDOW


def _client_ip(request: Request) -> str:
    """Prefer X-Forwarded-For (set by reverse proxies) over direct peer address."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter.

    _windows maps  (ip, path_bucket) → [timestamp, ...]
    where path_bucket is the first 4 segments of the path so that
    e.g. /api/sources/url and /api/sources/url/extra share the same bucket.
    """

    def __init__(self, app):
        super().__init__(app)
        # { (ip, bucket): [monotonic timestamps inside current window] }
        self._windows: dict[tuple[str, str], list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip rate-limiting for auth and health endpoints
        path = request.url.path
        if path in ("/api/auth/verify", "/api/health", "/"):
            return await call_next(request)

        ip     = _client_ip(request)
        limit, window = _get_limit(path)

        # Bucket = first 4 path segments — groups sub-paths together
        bucket = "/".join(path.split("/")[:4])
        key    = (ip, bucket)

        now = monotonic()

        # Evict timestamps outside the sliding window
        timestamps = [t for t in self._windows[key] if now - t < window]
        self._windows[key] = timestamps

        if len(timestamps) >= limit:
            retry_after = int(window - (now - timestamps[0])) + 1
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "detail": (
                        f"Rate limit exceeded: {limit} requests per {int(window)}s. "
                        f"Retry after {retry_after}s."
                    )
                },
            )

        self._windows[key].append(now)
        return await call_next(request)
