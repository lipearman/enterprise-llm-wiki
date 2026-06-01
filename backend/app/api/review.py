"""
Human-in-the-loop content review (admin — requires API key). Phase 7.

Auto-generated wiki pages (status=pending_review) and canonical QA (is_active=
false) wait here for an editor to approve (→ live) or reject (→ deleted).
Retrieval never serves pending content, so nothing reaches users until approved.

  GET    /api/review/pending                  — list pending wiki + QA
  POST   /api/review/wiki/{id}/{approve|reject}
  POST   /api/review/qa/{id}/{approve|reject}
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Query

from app.db.supabase_client import supabase
from app.services.audit_service import audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/pending")
def list_pending(company_code: str | None = Query(None)):
    wiki_q = (supabase.table("wiki_pages")
              .select("id,title,slug,summary,content_markdown,created_at,company_code")
              .eq("status", "pending_review").order("created_at", desc=True).limit(100))
    qa_q = (supabase.table("canonical_qa")
            .select("id,question,answer,priority,created_at,company_code")
            .eq("is_active", False).order("created_at", desc=True).limit(200))
    if company_code:
        wiki_q = wiki_q.eq("company_code", company_code)
        qa_q = qa_q.eq("company_code", company_code)
    wiki = wiki_q.execute().data or []
    qa = qa_q.execute().data or []
    return {"wiki": wiki, "qa": qa, "counts": {"wiki": len(wiki), "qa": len(qa)}}


@router.post("/wiki/{page_id}/approve")
def approve_wiki(page_id: str, request: Request):
    res = supabase.table("wiki_pages").update({"status": "published"}).eq("id", page_id).eq("status", "pending_review").execute()
    if not res.data:
        raise HTTPException(404, "Pending wiki page not found")
    audit_log("review.wiki.approve", request=request, detail={"id": page_id, "title": res.data[0].get("title")})
    return {"ok": True, "status": "published"}


@router.post("/wiki/{page_id}/reject")
def reject_wiki(page_id: str, request: Request):
    res = supabase.table("wiki_pages").delete().eq("id", page_id).eq("status", "pending_review").execute()
    audit_log("review.wiki.reject", request=request, detail={"id": page_id})
    return {"ok": True, "deleted": bool(res.data)}


@router.post("/qa/{qa_id}/approve")
def approve_qa(qa_id: str, request: Request):
    res = supabase.table("canonical_qa").update({"is_active": True}).eq("id", qa_id).eq("is_active", False).execute()
    if not res.data:
        raise HTTPException(404, "Pending QA not found")
    audit_log("review.qa.approve", request=request, detail={"id": qa_id, "question": res.data[0].get("question")})
    return {"ok": True, "is_active": True}


@router.post("/qa/{qa_id}/reject")
def reject_qa(qa_id: str, request: Request):
    res = supabase.table("canonical_qa").delete().eq("id", qa_id).eq("is_active", False).execute()
    audit_log("review.qa.reject", request=request, detail={"id": qa_id})
    return {"ok": True, "deleted": bool(res.data)}


@router.post("/wiki/approve-all")
def approve_all_wiki(request: Request, company_code: str | None = Query(None)):
    q = supabase.table("wiki_pages").update({"status": "published"}).eq("status", "pending_review")
    if company_code:
        q = q.eq("company_code", company_code)
    res = q.execute()
    n = len(res.data or [])
    audit_log("review.wiki.approve_all", request=request, detail={"count": n})
    return {"ok": True, "approved": n}
