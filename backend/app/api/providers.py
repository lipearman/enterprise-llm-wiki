"""
AI provider management endpoints (admin — requires API key).

Manage OpenAI-compatible AI providers and per-role assignments used by the
multi-provider failover router (ProviderService).

  GET    /api/providers            — list providers (keys masked)
  POST   /api/providers            — create provider
  PUT    /api/providers/{id}       — update provider
  DELETE /api/providers/{id}       — delete provider
  POST   /api/providers/{id}/test  — quick connectivity test

  GET    /api/providers/roles      — list role assignments
  POST   /api/providers/roles      — create assignment
  PUT    /api/providers/roles/{id} — update assignment
  DELETE /api/providers/roles/{id} — delete assignment
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db.supabase_client import supabase
from app.services.provider_service import provider_service, mask_key, ROLES
from app.services.audit_service import audit_log
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/providers", tags=["providers"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProviderIn(BaseModel):
    name:     str
    base_url: str
    api_key:  str | None = None     # optional on update (keep existing)
    protocol: str = "openai"
    is_active: bool = True


class AssignmentIn(BaseModel):
    role:        str
    provider_id: str
    model:       str
    priority:    int = 100
    is_active:   bool = True


def _public_provider(row: dict) -> dict:
    """Strip the secret — return a masked key only."""
    return {
        "id": row["id"], "name": row["name"], "base_url": row["base_url"],
        "protocol": row.get("protocol", "openai"),
        "is_active": row.get("is_active", True),
        "api_key_masked": mask_key(row.get("api_key", "")),
        "has_key": bool(row.get("api_key")),
    }


# ── Providers ──────────────────────────────────────────────────────────────────

@router.get("")
def list_providers():
    rows = supabase.table("ai_providers").select("*").order("name").execute().data or []
    return {"items": [_public_provider(r) for r in rows], "roles": list(ROLES)}


@router.post("")
def create_provider(body: ProviderIn, request: Request):
    if not body.api_key:
        raise HTTPException(400, "api_key required when creating a provider")
    res = supabase.table("ai_providers").insert({
        "name": body.name, "base_url": body.base_url.rstrip("/"),
        "api_key": body.api_key, "protocol": body.protocol, "is_active": body.is_active,
    }).execute()
    provider_service.invalidate()
    audit_log("provider.create", request=request, detail={"name": body.name})
    return _public_provider(res.data[0])


@router.put("/{provider_id}")
def update_provider(provider_id: str, body: ProviderIn, request: Request):
    patch: dict = {
        "name": body.name, "base_url": body.base_url.rstrip("/"),
        "protocol": body.protocol, "is_active": body.is_active,
    }
    if body.api_key:                       # only overwrite key when a new one is given
        patch["api_key"] = body.api_key
    res = supabase.table("ai_providers").update(patch).eq("id", provider_id).execute()
    if not res.data:
        raise HTTPException(404, "Provider not found")
    provider_service.invalidate()
    audit_log("provider.update", request=request, detail={"id": provider_id, "name": body.name})
    return _public_provider(res.data[0])


@router.delete("/{provider_id}")
def delete_provider(provider_id: str, request: Request):
    supabase.table("ai_providers").delete().eq("id", provider_id).execute()
    provider_service.invalidate()
    audit_log("provider.delete", request=request, detail={"id": provider_id})
    return {"ok": True}


def _model_is_free(m: dict) -> bool:
    """A single model is explicitly free if its id ends with ':free' or its
    pricing is zero."""
    if (m.get("id") or "").endswith(":free"):
        return True
    pricing = m.get("pricing")
    if isinstance(pricing, dict):
        prompt = str(pricing.get("prompt", "")).strip()
        completion = str(pricing.get("completion", "")).strip()
        return prompt in ("0", "0.0", "0.00") and completion in ("0", "0.0", "0.00")
    return False


# Preferred keywords for auto-picking a fast, reliable model to test with
# (avoids huge reasoning models / vision-only / broken alpha endpoints).
_TEST_MODEL_PREF = (
    "gpt-oss-120b", "gpt-oss", "llama-3.3-70b", "llama-3.1-8b", "8b-instruct",
    "llama-3", "gemma", "mini", "flash", "qwen", "instruct",
)


def _fetch_models(prov: dict) -> tuple[list[dict], dict]:
    """Return (raw_model_objects, meta). Raises on HTTP/connection error."""
    url = prov["base_url"].rstrip("/") + "/models"
    r = httpx.get(url, headers={"Authorization": f"Bearer {prov['api_key']}"}, timeout=20)
    r.raise_for_status()
    payload = r.json()
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    return (data if isinstance(data, list) else []), {}


# Substrings that mark a model as an embedding model, or as a clearly
# non-chat model (so chat roles don't offer TTS / audio / image / guard / …).
_EMBED_HINTS = ("embed", "embedding")
_NON_CHAT_HINTS = (
    "embed", "embedding", "tts", "whisper", "audio", "speech", "image", "imagen",
    "guard", "rerank", "reranker", "moderation", "aqa", "veo", "lyria", "orpheus",
)


def _classify_model(mid: str) -> str:
    """'embed' | 'chat' — best-effort classification from the model id."""
    low = mid.lower()
    if any(h in low for h in _EMBED_HINTS):
        return "embed"
    return "chat"


def _normalize_models(raw: list[dict], free_only: bool, kind: str = "all") -> list[dict]:
    """Mark each model free/paid and (optionally) filter by kind.

    If the provider exposes NO explicitly-free model (a flat free-tier dev
    provider like sambanova/nvidia/cerebras/ollama), treat every model as free
    so free_only doesn't empty the list.

    kind: 'embed' → embedding models only; 'chat' → exclude embedding & other
    non-chat (tts/audio/image/guard/…); 'all' → no kind filter."""
    valid = [m for m in raw if isinstance(m, dict) and m.get("id")]
    has_free_marker = any(_model_is_free(m) for m in valid)
    items = []
    for m in valid:
        mid = m["id"]
        low = mid.lower()
        if kind == "embed" and _classify_model(mid) != "embed":
            continue
        if kind == "chat" and any(h in low for h in _NON_CHAT_HINTS):
            continue
        free = _model_is_free(m) if has_free_marker else True
        if free_only and not free:
            continue
        items.append({"id": mid, "name": m.get("name") or mid, "free": free})
    items.sort(key=lambda x: x["id"].lower())
    return items


@router.get("/{provider_id}/models")
async def list_provider_models(provider_id: str, free_only: bool = True, kind: str = "all"):
    """List models the provider exposes via GET {base_url}/models.

    free_only=true (default) keeps only free models. Providers with no explicit
    free/paid split are treated as entirely free.
    kind: 'embed' (embedding models only), 'chat' (exclude embed/tts/audio/…),
    or 'all' (default, no kind filter)."""
    res = supabase.table("ai_providers").select("*").eq("id", provider_id).single().execute()
    prov = res.data
    if not prov:
        raise HTTPException(404, "Provider not found")
    try:
        raw, _ = _fetch_models(prov)
        items = _normalize_models(raw, free_only, kind)
        return {"ok": True, "items": items, "total": len(items)}
    except httpx.HTTPStatusError as exc:
        return {"ok": False, "status": exc.response.status_code, "detail": exc.response.text[:200], "items": []}
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}", "items": []}


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str, model: str | None = None):
    """Quick connectivity test — sends a trivial prompt to the provider."""
    res = supabase.table("ai_providers").select("*").eq("id", provider_id).single().execute()
    prov = res.data
    if not prov:
        raise HTTPException(404, "Provider not found")
    base = prov["base_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {prov['api_key']}"}
    try:
        import time
        # Pick a real model when none supplied: prefer a fast, reliable free one.
        test_model = model
        if not test_model:
            try:
                raw, _ = _fetch_models(prov)
                free_ids = [m["id"] for m in _normalize_models(raw, free_only=True)]
            except Exception:
                free_ids = []
            if free_ids:
                test_model = next(
                    (mid for kw in _TEST_MODEL_PREF for mid in free_ids if kw in mid.lower()),
                    free_ids[0],
                )
            else:
                test_model = "gpt-oss-120b"
        t0 = time.time()
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(
                base + "/chat/completions",
                json={"model": test_model, "messages": [{"role": "user", "content": "reply OK"}],
                      "max_tokens": 200, "stream": False},
                headers=headers,
            )
        latency = round(time.time() - t0, 2)
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code, "model": test_model, "detail": r.text[:200], "latency": latency}
        content = (r.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
        return {"ok": bool(content), "latency": latency, "model": test_model, "sample": content[:60]}
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}


# ── Role assignments ───────────────────────────────────────────────────────────

# Roles that accept exactly ONE provider. Embedding failover across different
# models is unsafe — each model has its own vector space, so a fallback embedder
# would silently corrupt retrieval (query vs stored docs in different spaces).
_SINGLE_ASSIGNMENT_ROLES = {"embed"}


@router.get("/roles")
def list_assignments():
    rows = (
        supabase.table("ai_role_assignments")
        .select("*").order("role").order("priority").execute().data or []
    )
    provs = {p["id"]: p["name"] for p in (supabase.table("ai_providers").select("id,name").execute().data or [])}
    for r in rows:
        r["provider_name"] = provs.get(r.get("provider_id"), "?")
    # embedding_dim is the fixed width of the DB vector columns — surfaced so the
    # UI can display it on the Embeddings role (read-only).
    return {"items": rows, "roles": list(ROLES), "embedding_dim": settings.EMBEDDING_DIM}


@router.post("/roles")
def create_assignment(body: AssignmentIn, request: Request):
    if body.role not in ROLES:
        raise HTTPException(400, f"unknown role; allowed: {list(ROLES)}")
    if body.role in _SINGLE_ASSIGNMENT_ROLES:
        existing = (supabase.table("ai_role_assignments").select("id")
                    .eq("role", body.role).execute().data or [])
        if existing:
            raise HTTPException(
                409,
                f"role '{body.role}' accepts only one provider (embedding failover "
                "across models would corrupt retrieval). Remove the existing one first.",
            )
    res = supabase.table("ai_role_assignments").insert({
        "role": body.role, "provider_id": body.provider_id, "model": body.model,
        "priority": body.priority, "is_active": body.is_active,
    }).execute()
    provider_service.invalidate()
    audit_log("provider.assign", request=request, detail={"role": body.role, "model": body.model})
    return res.data[0]


@router.put("/roles/{assignment_id}")
def update_assignment(assignment_id: str, body: AssignmentIn, request: Request):
    res = supabase.table("ai_role_assignments").update({
        "role": body.role, "provider_id": body.provider_id, "model": body.model,
        "priority": body.priority, "is_active": body.is_active,
    }).eq("id", assignment_id).execute()
    if not res.data:
        raise HTTPException(404, "Assignment not found")
    provider_service.invalidate()
    audit_log("provider.assign_update", request=request, detail={"id": assignment_id})
    return res.data[0]


@router.delete("/roles/{assignment_id}")
def delete_assignment(assignment_id: str, request: Request):
    supabase.table("ai_role_assignments").delete().eq("id", assignment_id).execute()
    provider_service.invalidate()
    audit_log("provider.assign_delete", request=request, detail={"id": assignment_id})
    return {"ok": True}
