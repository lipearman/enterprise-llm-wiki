"""
ProviderService — DB-backed multi-provider AI routing with automatic failover.

Each *role* (answer_llm, canonical_qa, embed, …) maps to an ordered list of
provider+model assignments (``ai_role_assignments``). ``chat()`` / ``embed()``
try them by ascending priority and fail over to the next provider on a
rate-limit (429) or transient (5xx / timeout / empty) error.

Providers (``ai_providers``) are OpenAI-compatible endpoints for now
(sambanova, cerebras, nvidia, openrouter, ollama-via-/v1).

Config is cached in memory and refreshed every ``_TTL`` seconds (or on demand
via ``invalidate()`` after an edit). When a role has no active assignment,
callers fall back to their existing default client.
"""

from __future__ import annotations

import asyncio
import logging
import time
import httpx

from app.db.supabase_client import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Roles the system understands.
ROLES = (
    "answer_llm",
    "chat",
    "fact_extraction",
    "wiki_generation",
    "canonical_qa",
    "embed",
)

# Status codes / conditions that should trigger failover to the next provider.
_FAILOVER_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


class AllProvidersFailedError(RuntimeError):
    """Raised when every configured provider for a role failed."""


def mask_key(key: str) -> str:
    """Return a masked key for API responses — never expose the full secret."""
    if not key:
        return ""
    return f"…{key[-4:]}" if len(key) >= 4 else "…"


class ProviderService:
    _TTL = 30.0   # seconds — config cache lifetime

    def __init__(self) -> None:
        self._providers: dict[str, dict] = {}        # id → provider row
        self._by_role: dict[str, list[dict]] = {}    # role → [assignment+provider] sorted
        self._loaded_at: float = 0.0

    # ── Config loading ────────────────────────────────────────────────────────
    def _ensure_loaded(self) -> None:
        if self._providers and (time.monotonic() - self._loaded_at) < self._TTL:
            return
        self._reload()

    def _reload(self) -> None:
        try:
            provs = supabase.table("ai_providers").select("*").execute().data or []
            assigns = supabase.table("ai_role_assignments").select("*").execute().data or []
        except Exception as exc:
            logger.warning("provider_service_reload_failed | %s", exc)
            self._loaded_at = time.monotonic()   # avoid hammering on every call
            return

        self._providers = {p["id"]: p for p in provs}
        by_role: dict[str, list[dict]] = {}
        for a in assigns:
            if not a.get("is_active"):
                continue
            prov = self._providers.get(a.get("provider_id"))
            if not prov or not prov.get("is_active"):
                continue
            by_role.setdefault(a["role"], []).append({**a, "_provider": prov})
        for role in by_role:
            by_role[role].sort(key=lambda x: (x.get("priority") or 100))
        self._by_role = by_role
        self._loaded_at = time.monotonic()
        logger.info(
            "provider_service_loaded | providers=%d | roles=%s",
            len(provs), {r: len(v) for r, v in by_role.items()},
        )

    def invalidate(self) -> None:
        self._loaded_at = 0.0

    def is_configured(self, role: str) -> bool:
        self._ensure_loaded()
        return bool(self._by_role.get(role))

    # ── Chat with failover ────────────────────────────────────────────────────
    async def chat(
        self,
        role: str,
        messages: list[dict],
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a chat completion for *role*, failing over across providers.

        Raises AllProvidersFailedError if every provider fails. Callers that want
        a graceful fallback should check ``is_configured(role)`` first.
        """
        self._ensure_loaded()
        chain = self._by_role.get(role, [])
        if not chain:
            raise AllProvidersFailedError(f"no active provider for role={role}")

        last_exc: Exception | None = None
        for a in chain:
            prov = a["_provider"]
            try:
                content = await self._openai_chat(
                    prov["base_url"], prov["api_key"], a["model"],
                    messages, temperature, max_tokens,
                )
                if content and content.strip():
                    logger.info("provider_chat_ok | role=%s | provider=%s | model=%s",
                                role, prov["name"], a["model"])
                    return content
                raise ValueError("empty content")
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "provider_chat_failover | role=%s | provider=%s | %s: %s",
                    role, prov.get("name"), type(exc).__name__, str(exc)[:120],
                )
                continue
        raise AllProvidersFailedError(
            f"all providers failed for role={role}: {last_exc}"
        ) from last_exc

    @staticmethod
    async def _openai_chat(
        base_url: str, api_key: str, model: str,
        messages: list[dict], temperature: float, max_tokens: int,
    ) -> str:
        url = base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=20, read=120, write=20, pool=20)) as client:
            r = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            if r.status_code in _FAILOVER_STATUS:
                raise httpx.HTTPStatusError(f"status {r.status_code}", request=r.request, response=r)
            r.raise_for_status()
            data = r.json()
            # Reasoning models (gpt-oss) return {choices:[{message:{content, reasoning}}]}
            return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""

    # ── Embeddings (single provider + transient retry) ─────────────────────────
    _EMBED_RETRIES = 3          # attempts per provider on transient errors
    _EMBED_BACKOFF = 1.5        # seconds, exponential

    async def embed(self, role: str, text: str) -> list[float]:
        """Embed via the role's provider(s).

        Unlike chat, embedding does NOT fail over to a *different* model — each
        model has its own vector space, so a fallback embedder would corrupt
        retrieval. The ``embed`` role is restricted to one provider; on a
        transient rate-limit (429/5xx/timeout) we retry the same provider with
        exponential backoff instead of switching."""
        self._ensure_loaded()
        chain = self._by_role.get(role, [])
        if not chain:
            raise AllProvidersFailedError(f"no active provider for role={role}")
        # Match the DB vector column width. Dimension-capable providers (Gemini
        # gemini-embedding-001, OpenAI text-embedding-3) honour this; others
        # ignore it and return their native size.
        dims = settings.EMBEDDING_DIM or None
        last_exc: Exception | None = None
        for a in chain:
            prov = a["_provider"]
            for attempt in range(self._EMBED_RETRIES):
                try:
                    return await self._openai_embed(prov["base_url"], prov["api_key"], a["model"], text, dims)
                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    status = exc.response.status_code if exc.response is not None else None
                    if status in _FAILOVER_STATUS and attempt < self._EMBED_RETRIES - 1:
                        delay = self._EMBED_BACKOFF * (2 ** attempt)
                        logger.warning("provider_embed_retry | provider=%s | status=%s | retry in %.1fs",
                                       prov.get("name"), status, delay)
                        await asyncio.sleep(delay)
                        continue
                    break
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_exc = exc
                    if attempt < self._EMBED_RETRIES - 1:
                        delay = self._EMBED_BACKOFF * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    break
                except Exception as exc:           # non-transient → don't retry
                    last_exc = exc
                    break
            # Only reached when this provider exhausted its retries. The embed
            # role normally has a single provider, so we stop here rather than
            # fail over to a different (incompatible) model.
            logger.warning("provider_embed_failed | provider=%s | %s",
                           prov.get("name"), str(last_exc)[:120])
            break
        raise AllProvidersFailedError(f"embed failed for role={role}: {last_exc}") from last_exc

    @staticmethod
    async def _openai_embed(base_url: str, api_key: str, model: str, text: str,
                            dimensions: int | None = None) -> list[float]:
        url = base_url.rstrip("/") + "/embeddings"
        payload: dict = {"model": model, "input": text}
        if dimensions:
            payload["dimensions"] = dimensions
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if r.status_code in _FAILOVER_STATUS:
                raise httpx.HTTPStatusError(f"status {r.status_code}", request=r.request, response=r)
            r.raise_for_status()
            return r.json()["data"][0]["embedding"]


provider_service = ProviderService()
