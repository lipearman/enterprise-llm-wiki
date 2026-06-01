"""
Multi-step claim intake with checkpointing (Phase 7).

A guided, resumable conversation that collects claim details one step at a time.
State is persisted per session so a customer can drop off and return later and
continue where they left off — i.e. a durable, DB-backed "checkpoint".

Persistence: the ``claim_intakes`` table (run sql/011_claim_intakes.sql). If the
table is missing, the service degrades to an in-memory store so the flow still
works for demos/tests (state is then lost on restart).

Off by default — gated by ``ENABLE_CLAIM_INTAKE``.
"""

import logging
import re

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)

# Ordered intake steps: (field, question shown to the user).
STEPS: list[tuple[str, str]] = [
    ("policy_number", "ขอเลขกรมธรรม์ของคุณครับ (เช่น DEVES-1234567)"),
    ("vehicle",       "รบกวนแจ้งข้อมูลรถ — ยี่ห้อ/รุ่น และทะเบียนรถครับ"),
    ("incident",      "เล่ารายละเอียดเหตุการณ์ที่เกิดขึ้นสั้น ๆ ครับ (เกิดอะไร ที่ไหน เมื่อไหร่)"),
]
_CLAIM_TRIGGERS = ("แจ้งเคลม", "เคลมประกัน", "ขอเคลม", "เปิดเคลม", "เคลมรถ", "file a claim", "make a claim")

# In-memory fallback when the DB table is absent: {session_id: {step, data, status}}
_MEM: dict[str, dict] = {}


class ClaimService:
    # ── intent ────────────────────────────────────────────────────────────────
    @staticmethod
    def is_claim_intent(message: str) -> bool:
        m = (message or "").lower()
        return any(t in m for t in _CLAIM_TRIGGERS)

    # ── persistence (DB with in-memory fallback) ──────────────────────────────
    def _load(self, session_id: str) -> dict | None:
        try:
            rows = (supabase.table("claim_intakes").select("*")
                    .eq("session_id", session_id).eq("status", "collecting")
                    .limit(1).execute().data)
            return rows[0] if rows else None
        except Exception:
            return _MEM.get(session_id)

    def _save(self, session_id: str, company_code: str, step: int, data: dict, status: str) -> None:
        record = {"session_id": session_id, "company_code": company_code,
                  "current_step": step, "data": data, "status": status}
        try:
            existing = (supabase.table("claim_intakes").select("id")
                        .eq("session_id", session_id).neq("status", "submitted")
                        .limit(1).execute().data)
            if existing:
                supabase.table("claim_intakes").update(record).eq("id", existing[0]["id"]).execute()
            else:
                supabase.table("claim_intakes").insert(record).execute()
        except Exception:
            _MEM[session_id] = {**record}          # table missing → in-memory checkpoint

    def _clear_mem(self, session_id: str) -> None:
        _MEM.pop(session_id, None)

    # ── flow ──────────────────────────────────────────────────────────────────
    def active(self, session_id: str) -> bool:
        return self._load(session_id) is not None

    def start(self, session_id: str, company_code: str) -> str:
        self._save(session_id, company_code, 0, {}, "collecting")
        return ("เริ่มขั้นตอนแจ้งเคลมนะครับ 📋 (พิมพ์ 'ยกเลิก' เพื่อหยุด)\n\n" + STEPS[0][1])

    def advance(self, session_id: str, company_code: str, message: str) -> str:
        """Apply the user's message to the current step and return the next
        question, or a confirmation summary when all steps are done."""
        if message.strip() in ("ยกเลิก", "ยกเลิกการเคลม", "cancel"):
            self._cancel(session_id)
            return "ยกเลิกการแจ้งเคลมแล้วครับ หากต้องการเริ่มใหม่พิมพ์ 'แจ้งเคลม' ได้เลย"

        state = self._load(session_id)
        if not state:                                # no active intake → start one
            return self.start(session_id, company_code)

        step = int(state.get("current_step", 0))
        data = dict(state.get("data") or {})
        field, _ = STEPS[step]
        data[field] = message.strip()
        next_step = step + 1

        if next_step < len(STEPS):
            self._save(session_id, company_code, next_step, data, "collecting")
            done = next_step
            return f"รับทราบครับ ✅ ({done}/{len(STEPS)})\n\n{STEPS[next_step][1]}"

        # All steps collected → submit.
        ref = self._submit(session_id, company_code, data)
        self._clear_mem(session_id)
        return (
            "ได้รับข้อมูลครบแล้วครับ 🎉 สรุปการแจ้งเคลม:\n"
            f"• เลขกรมธรรม์: {data.get('policy_number')}\n"
            f"• รถ: {data.get('vehicle')}\n"
            f"• เหตุการณ์: {data.get('incident')}\n\n"
            f"เลขอ้างอิง: {ref}\nเจ้าหน้าที่จะติดต่อกลับโดยเร็วครับ"
        )

    def _submit(self, session_id: str, company_code: str, data: dict) -> str:
        ref = "CLM-" + re.sub(r"\D", "", session_id)[-6:].rjust(6, "0")
        try:
            supabase.table("claim_intakes").update(
                {"current_step": len(STEPS), "data": data, "status": "submitted", "reference": ref}
            ).eq("session_id", session_id).neq("status", "submitted").execute()
        except Exception:
            _MEM.pop(session_id, None)
        logger.info("claim_submitted | ref=%s | session=%s", ref, session_id[:12])
        return ref

    def _cancel(self, session_id: str) -> None:
        try:
            supabase.table("claim_intakes").update({"status": "cancelled"}).eq("session_id", session_id).eq("status", "collecting").execute()
        except Exception:
            pass
        self._clear_mem(session_id)


claim_service = ClaimService()
