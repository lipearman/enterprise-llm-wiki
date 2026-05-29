import io
import re
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.db.supabase_client import supabase
from app.core.config import settings

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _safe_filename(slug: str) -> str:
    """Sanitize a slug into a safe cross-platform filename (no path separators, etc.)."""
    name = re.sub(r"[^\w\-]", "_", slug or "untitled")
    name = re.sub(r"_+", "_", name).strip("_")
    return (name[:120] or "untitled") + ".md"


def _build_md(page: dict) -> str:
    """Return full Markdown content with YAML frontmatter for a wiki page."""
    # --- YAML frontmatter ---
    lines = ["---"]
    lines.append(f"title: {page.get('title', '')!r}")
    lines.append(f"slug: {page.get('slug', '')}")
    lines.append(f"status: {page.get('status', 'draft')}")
    lines.append(f"version: {page.get('version', 1)}")

    sources = page.get("source_urls") or []
    if sources:
        lines.append("source_urls:")
        for url in sources:
            lines.append(f"  - {url}")

    created = page.get("created_at", "")
    updated = page.get("updated_at", "")
    if created:
        lines.append(f"created_at: {created}")
    if updated:
        lines.append(f"updated_at: {updated}")
    lines.append("---")
    lines.append("")

    # --- Summary ---
    summary = (page.get("summary") or "").strip()
    if summary:
        lines.append(f"> {summary}")
        lines.append("")

    # --- Body ---
    body = (page.get("content_markdown") or "").strip()
    if body:
        lines.append(body)
    else:
        lines.append("*(no content)*")

    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────
#  Wiki Pages
# ─────────────────────────────────────────────

@router.get("/pages")
def list_pages(company_code: str | None = None, status: str | None = None, q: str | None = None):
    company_code = company_code or settings.DEFAULT_COMPANY_CODE
    query = supabase.table("wiki_pages").select(
        "id,company_code,title,slug,summary,status,version,source_urls,created_at,updated_at"
    ).eq("company_code", company_code)
    if status:
        query = query.eq("status", status)
    if q:
        query = query.ilike("title", f"%{q}%")
    res = query.order("created_at", desc=True).execute()
    return {"items": res.data or [], "total": len(res.data or [])}


@router.get("/pages/{page_id}")
def get_page(page_id: str):
    res = supabase.table("wiki_pages").select("*").eq("id", page_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return res.data


@router.put("/pages/{page_id}")
def update_page(page_id: str, body: dict):
    allowed = {"title", "summary", "content_markdown", "status"}
    update_data = {k: v for k, v in body.items() if k in allowed}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    res = supabase.table("wiki_pages").update(update_data).eq("id", page_id).execute()
    return res.data[0] if res.data else {"ok": True}


@router.delete("/pages/{page_id}")
def delete_page(page_id: str):
    res = supabase.table("wiki_pages").select("id").eq("id", page_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    supabase.table("wiki_pages").delete().eq("id", page_id).execute()
    return {"ok": True, "message": "Wiki page deleted"}


@router.get("/export")
def export_pages(company_code: str | None = None, status: str | None = None):
    """
    Export all wiki pages for a company as Markdown files packed in a ZIP archive.

    Each page becomes ``<slug>.md`` with YAML frontmatter.
    An ``_index.md`` summary table is included at the root of the archive.
    """
    company_code = company_code or settings.DEFAULT_COMPANY_CODE

    query = supabase.table("wiki_pages").select(
        "id,company_code,title,slug,summary,status,version,source_urls,"
        "content_markdown,created_at,updated_at"
    ).eq("company_code", company_code)
    if status:
        query = query.eq("status", status)
    res = query.order("title").execute()
    pages: list[dict] = res.data or []

    # ── Build ZIP in memory ───────────────────────────────────────────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:

        # _index.md — summary table
        index_lines = [
            f"# Wiki Export — {company_code}",
            "",
            f"Exported **{len(pages)}** page(s) on "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "| Title | Slug | Status | Version | Updated |",
            "|-------|------|--------|---------|---------|",
        ]
        for p in pages:
            updated = (p.get("updated_at") or "")[:10]
            index_lines.append(
                f"| {p.get('title','')} "
                f"| {p.get('slug','')} "
                f"| {p.get('status','')} "
                f"| {p.get('version', 1)} "
                f"| {updated} |"
            )
        index_lines.append("")
        zf.writestr("_index.md", "\n".join(index_lines))

        # One .md per page
        seen: dict[str, int] = {}
        for page in pages:
            base = _safe_filename(page.get("slug") or page.get("id", "untitled"))
            # Deduplicate filenames (same slug but different id — rare, but safe)
            if base in seen:
                seen[base] += 1
                stem, ext = base.rsplit(".", 1)
                fname = f"{stem}_{seen[base]}.{ext}"
            else:
                seen[base] = 0
                fname = base

            zf.writestr(fname, _build_md(page))

    buf.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"wiki_{company_code}_{timestamp}.zip"

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────
#  Canonical QA
# ─────────────────────────────────────────────

class QACreate(BaseModel):
    company_code: str | None = None
    wiki_page_id: str | None = None
    question: str
    answer: str


class QAUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    is_active: bool | None = None


@router.get("/qa")
def list_qa(
    company_code: str | None = None,
    wiki_page_id: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    company_code = company_code or settings.DEFAULT_COMPANY_CODE
    query = supabase.table("canonical_qa").select(
        "id,company_code,wiki_page_id,question,answer,is_active,created_at"
    ).eq("company_code", company_code)
    if wiki_page_id:
        query = query.eq("wiki_page_id", wiki_page_id)
    if q:
        query = query.ilike("question", f"%{q}%")
    res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": len(res.data or [])}


@router.post("/qa")
async def create_qa(body: QACreate):
    from app.services.ollama_client import embed_llm
    from app.core.text import normalize_question

    company_code = body.company_code or settings.DEFAULT_COMPANY_CODE
    emb = await embed_llm.embed(normalize_question(body.question))
    res = supabase.table("canonical_qa").insert({
        "company_code": company_code,
        "wiki_page_id": body.wiki_page_id,
        "question": body.question,
        "answer": body.answer,
        "embedding": emb,
        "is_active": True,
    }).execute()
    return res.data[0] if res.data else {"ok": True}


@router.put("/qa/{qa_id}")
async def update_qa(qa_id: str, body: QAUpdate):
    from app.services.ollama_client import embed_llm
    from app.core.text import normalize_question

    update_data: dict = {}
    if body.question is not None:
        update_data["question"] = body.question
        emb = await embed_llm.embed(normalize_question(body.question))
        update_data["embedding"] = emb
    if body.answer is not None:
        update_data["answer"] = body.answer
    if body.is_active is not None:
        update_data["is_active"] = body.is_active

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    res = supabase.table("canonical_qa").update(update_data).eq("id", qa_id).execute()
    return res.data[0] if res.data else {"ok": True}


@router.delete("/qa/{qa_id}")
def delete_qa(qa_id: str):
    supabase.table("canonical_qa").delete().eq("id", qa_id).execute()
    return {"ok": True, "message": "QA deleted"}


# ─────────────────────────────────────────────
#  Relationships
# ─────────────────────────────────────────────

@router.get("/relationships")
def list_relationships(
    company_code: str | None = None,
    entity: str | None = None,
    rel_type: str | None = None,
    limit: int = 100,
):
    company_code = company_code or settings.DEFAULT_COMPANY_CODE
    query = supabase.table("wiki_relationships").select(
        "id,source_entity,target_entity,relationship_type,weight,metadata,created_at"
    ).eq("company_code", company_code)
    if entity:
        query = query.or_(f"source_entity.ilike.%{entity}%,target_entity.ilike.%{entity}%")
    if rel_type:
        query = query.eq("relationship_type", rel_type)
    res = query.order("weight", desc=True).limit(limit).execute()
    return {"items": res.data or [], "total": len(res.data or [])}


@router.delete("/relationships/{rel_id}")
def delete_relationship(rel_id: str):
    supabase.table("wiki_relationships").delete().eq("id", rel_id).execute()
    return {"ok": True}
