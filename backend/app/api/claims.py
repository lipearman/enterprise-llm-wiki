"""
Claim intake admin view (admin — requires API key). Phase 7.

Lists claims customers have filed via the multi-step intake flow so staff can
follow up. Reads the claim_intakes table (in-memory fallback when not migrated).

  GET /api/claims?status=submitted   — list claims (submitted | collecting | cancelled)
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from app.services.claim_service import claim_service
from app.services.audit_service import audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/claims", tags=["claims"])


class StatusIn(BaseModel):
    status: str          # received | reviewing | approved | rejected


@router.get("")
def list_claims(status: str = Query("submitted"), company_code: str | None = Query(None)):
    rows = claim_service.list_claims(status=status, company_code=company_code)
    items = []
    for r in rows:
        d = r.get("data") or {}
        items.append({
            "reference":     r.get("reference"),
            "company_code":  r.get("company_code"),
            "policy_number": d.get("policy_number"),
            "vehicle":       d.get("vehicle"),
            "incident":      d.get("incident"),
            "incident_date": d.get("incident_date"),
            "callback_phone": d.get("callback_phone") or d.get("documents"),  # documents = legacy
            "review_status": d.get("review_status") or "received",
            "created_at":    r.get("created_at"),
        })
    return {"status": status, "count": len(items), "items": items}


@router.get("/counts")
def claim_counts(company_code: str | None = Query(None)):
    """Per-status counts for the filter tabs."""
    return {s: len(claim_service.list_claims(status=s, company_code=company_code))
            for s in ("submitted", "collecting", "cancelled")}


@router.post("/{reference}/status")
def update_status(reference: str, body: StatusIn, request: Request):
    if body.status not in claim_service.REVIEW_STATUSES:
        raise HTTPException(400, f"invalid status; allowed: {list(claim_service.REVIEW_STATUSES)}")
    if not claim_service.update_status(reference, body.status):
        raise HTTPException(404, "Claim not found")
    audit_log("claim.status", request=request, detail={"reference": reference, "status": body.status})
    return {"ok": True, "reference": reference, "review_status": body.status}
