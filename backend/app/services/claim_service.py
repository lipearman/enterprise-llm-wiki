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

# ── per-field validators: return (ok, normalized_value, error_message) ──────────
_POLICY_RE = re.compile(r"^([A-Za-z]{2,8})-?(\d{6,8})$")
_DATE_RELATIVE = ("วันนี้", "เมื่อวาน", "เมื่อวานนี้", "วานนี้", "เมื่อเช้า", "เมื่อคืน")


def _validate_policy(value: str) -> tuple[bool, str, str]:
    t = re.sub(r"\s", "", (value or "").strip().upper())
    m = _POLICY_RE.match(t)
    if m:
        return True, f"{m.group(1)}-{m.group(2)}", ""        # normalize → DEVES-1234567
    return (False, value,
            "รูปแบบเลขกรมธรรม์ไม่ถูกต้องครับ 🙏 กรุณาพิมพ์เป็น **DEVES-1234567** "
            "(ตัวอักษร + ขีด + ตัวเลข 6-8 หลัก)")


def _validate_date(value: str) -> tuple[bool, str, str]:
    t = (value or "").strip()
    if t and (any(w in t for w in _DATE_RELATIVE) or re.search(r"\d", t)):
        return True, t, ""
    return (False, value,
            "ขอวันที่เกิดเหตุให้ชัดเจนหน่อยครับ (เช่น **1 มิ.ย. 2567**, 01/06/2567 หรือ 'วันนี้')")


def _validate_phone(value: str) -> tuple[bool, str, str]:
    t = re.sub(r"[\s\-().]", "", (value or "").strip())
    if re.match(r"^0\d{8,9}$", t):                           # Thai mobile/landline 9-10 digits
        return True, t, ""
    return (False, value,
            "เบอร์โทรไม่ถูกต้องครับ 🙏 กรุณาพิมพ์เบอร์ 9-10 หลัก (เช่น **081-234-5678**)")


# Ordered intake steps. Each: field, question, optional validate fn, optional
# special handler name. Order = the conversation flow.
STEPS: list[dict] = [
    {"field": "policy_number", "q": "ขอเลขกรมธรรม์ของคุณครับ (เช่น DEVES-1234567)", "validate": _validate_policy},
    {"field": "vehicle",       "q": "รบกวนแจ้งข้อมูลรถ — ยี่ห้อ/รุ่น และทะเบียนรถครับ", "special": "vehicle"},
    {"field": "incident",      "q": "เล่ารายละเอียดเหตุการณ์ที่เกิดขึ้นสั้น ๆ ครับ (เกิดอะไร ที่ไหน)"},
    {"field": "incident_date", "q": "เกิดเหตุวันที่เท่าไหร่ครับ (เช่น 1 มิ.ย. 2567 หรือ 'วันนี้')", "validate": _validate_date},
    {"field": "callback_phone", "q": "ขอเบอร์โทรศัพท์ที่ให้เจ้าหน้าที่ติดต่อกลับครับ (เช่น 081-234-5678)", "validate": _validate_phone},
]
_CLAIM_TRIGGERS = ("แจ้งเคลม", "เคลมประกัน", "ขอเคลม", "เปิดเคลม", "เคลมรถ", "file a claim", "make a claim")
# Markers that signal an INFORMATIONAL question ("how to file a claim?") rather
# than an intent to actually file one — these must NOT start the intake flow.
_INFO_MARKERS = ("วิธี", "อย่างไร", "ยังไง", "ไหม", "อะไร", "ทำไม", "กี่", "เท่าไหร่",
                 "หรือเปล่า", "ขั้นตอน", "เอกสาร", "how to", "how do", "what")

# Thai licence plate, e.g. "1กก1234", "กก1234", "2ขข5678". Consonants and digits
# must be ADJACENT (no spaces) — otherwise the trailing consonant of a label word
# like "ทะเบีย[น] 2ขข…" gets mis-captured as "น 2".
_PLATE_RE = re.compile(r"[0-9]{0,2}[ก-ฮ]{1,3}[0-9]{1,4}")


def _extract_plate(text: str) -> str | None:
    m = _PLATE_RE.search(text or "")
    return m.group(0) if m else None


# Label words users type around the plate/brand — stripped so they aren't
# mistaken for the brand/model itself (longest first for clean removal).
_VEHICLE_LABELS = ("เลขทะเบียน", "ป้ายทะเบียน", "ทะเบียนรถ", "ทะเบียน",
                   "ยี่ห้อ/รุ่น", "ยี่ห้อ", "รุ่น", "รถยี่ห้อ")


def _clean_brand(text: str) -> str | None:
    """Brand/model = the non-plate part with label words removed, if it still
    has ≥2 actual letters (so "ทะเบียน 1กก1234" yields no brand)."""
    t = text or ""
    for lbl in _VEHICLE_LABELS:
        t = t.replace(lbl, " ")
    t = re.sub(r"\s+", " ", t).strip(" ,.-/")
    letters = re.sub(r"[\s\d]", "", t)
    return t if len(letters) >= 2 else None


# In-memory fallback when the DB table is absent: {session_id: {step, data, status}}
_MEM: dict[str, dict] = {}


class ClaimService:
    # ── intent ────────────────────────────────────────────────────────────────
    @staticmethod
    def is_claim_intent(message: str) -> bool:
        m = (message or "").lower().strip()
        if not any(t in m for t in _CLAIM_TRIGGERS):
            return False
        # Don't hijack informational questions like "วิธีแจ้งเคลมทำอย่างไร" or
        # "เคลมชั้น 1 ได้ไหม" — those should be answered by RAG, not start intake.
        if any(k in m for k in _INFO_MARKERS):
            return False
        return True

    # ── persistence (DB with in-memory fallback) ──────────────────────────────
    def _load(self, session_id: str) -> dict | None:
        try:
            rows = (supabase.table("claim_intakes").select("*")
                    .eq("session_id", session_id).eq("status", "collecting")
                    .limit(1).execute().data)
            return rows[0] if rows else None
        except Exception:
            rec = _MEM.get(session_id)                       # only "collecting" is active
            return rec if rec and rec.get("status") == "collecting" else None

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
        return ("เริ่มขั้นตอนแจ้งเคลมนะครับ 📋 (พิมพ์ 'ยกเลิก' เพื่อหยุด)\n\n" + STEPS[0]["q"])

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
        cfg = STEPS[step]

        # Vehicle step needs BOTH brand/model AND licence plate — accumulate the
        # parts across messages and ask only for whatever is still missing.
        if cfg.get("special") == "vehicle":
            return self._handle_vehicle(session_id, company_code, step, data, message)

        # Field-level validation — re-ask (stay on step) on failure.
        validate = cfg.get("validate")
        if validate:
            ok, normalized, err = validate(message)
            if not ok:
                return f"{err}"
            data[cfg["field"]] = normalized
        else:
            data[cfg["field"]] = message.strip()

        return self._advance_or_finish(session_id, company_code, step, data)

    def _advance_or_finish(self, session_id: str, company_code: str, step: int, data: dict) -> str:
        """Move to the next step, or submit + summarize when the last step is done."""
        next_step = step + 1
        if next_step < len(STEPS):
            self._save(session_id, company_code, next_step, data, "collecting")
            return f"รับทราบครับ ✅ ({next_step}/{len(STEPS)})\n\n{STEPS[next_step]['q']}"
        ref = self._submit(session_id, company_code, data)
        return (
            "ได้รับข้อมูลครบแล้วครับ 🎉 สรุปการแจ้งเคลม:\n"
            f"• เลขกรมธรรม์: {data.get('policy_number')}\n"
            f"• รถ: {data.get('vehicle')}\n"
            f"• เหตุการณ์: {data.get('incident')}\n"
            f"• วันที่เกิดเหตุ: {data.get('incident_date')}\n"
            f"• เบอร์ติดต่อกลับ: {data.get('callback_phone')}\n\n"
            f"เลขอ้างอิง: {ref}\nเจ้าหน้าที่จะติดต่อกลับโดยเร็วครับ"
        )

    def _handle_vehicle(self, session_id: str, company_code: str, step: int, data: dict, message: str) -> str:
        """Collect ยี่ห้อ/รุ่น + ทะเบียน, accumulating across messages. Re-ask only
        for the part that's still missing; advance once both are present."""
        veh = dict(data.get("_vehicle") or {})
        plate = _extract_plate(message)
        remainder = message
        if plate:
            veh["plate"] = plate
            remainder = _PLATE_RE.sub(" ", message, count=1)
        brand = _clean_brand(remainder)
        if brand and not veh.get("brand_model"):
            veh["brand_model"] = brand

        if veh.get("brand_model") and veh.get("plate"):
            data["vehicle"] = f"{veh['brand_model']} ทะเบียน {veh['plate']}"
            data.pop("_vehicle", None)
            return self._advance_or_finish(session_id, company_code, step, data)

        # Still missing a part → stay on this step and ask only for what's missing.
        data["_vehicle"] = veh
        self._save(session_id, company_code, step, data, "collecting")
        if not veh.get("plate"):
            got = f" (บันทึกรถ: {veh['brand_model']} แล้ว)" if veh.get("brand_model") else ""
            return f"ขอบคุณครับ 🙏{got} รบกวนแจ้ง **ทะเบียนรถ** ด้วยครับ (เช่น 1กก1234)"
        return "ขอบคุณครับ 🙏 รบกวนแจ้ง **ยี่ห้อ/รุ่นรถ** ด้วยครับ (เช่น Toyota Vios)"

    def _submit(self, session_id: str, company_code: str, data: dict) -> str:
        ref = "CLM-" + re.sub(r"\D", "", session_id)[-6:].rjust(6, "0")
        data = {**data, "review_status": "received"}        # start the handling workflow
        try:
            supabase.table("claim_intakes").update(
                {"current_step": len(STEPS), "data": data, "status": "submitted", "reference": ref}
            ).eq("session_id", session_id).neq("status", "submitted").execute()
        except Exception:
            # In-memory fallback: keep the record as 'submitted' so staff can see
            # it in /claims (lost on restart — run sql/011 for durability).
            from datetime import datetime, timezone
            _MEM[session_id] = {"session_id": session_id, "company_code": company_code,
                                "current_step": len(STEPS), "data": data, "status": "submitted",
                                "reference": ref, "created_at": datetime.now(timezone.utc).isoformat()}
        logger.info("claim_submitted | ref=%s | session=%s", ref, session_id[:12])
        return ref

    # ── handling workflow: received → reviewing → approved | rejected ─────────
    REVIEW_STATUSES = ("received", "reviewing", "approved", "rejected")

    def update_status(self, reference: str, new_status: str) -> bool:
        """Update a claim's handling status (stored in data.review_status), keyed
        by its reference. Works against the DB or the in-memory fallback."""
        if new_status not in self.REVIEW_STATUSES:
            return False
        try:
            rows = (supabase.table("claim_intakes").select("id,data")
                    .eq("reference", reference).limit(1).execute().data)
            if rows:
                data = dict(rows[0].get("data") or {})
                data["review_status"] = new_status
                supabase.table("claim_intakes").update({"data": data}).eq("id", rows[0]["id"]).execute()
                logger.info("claim_status | ref=%s | %s", reference, new_status)
                return True
        except Exception:
            pass
        for r in _MEM.values():                              # in-memory fallback
            if r.get("reference") == reference:
                r.setdefault("data", {})["review_status"] = new_status
                logger.info("claim_status(mem) | ref=%s | %s", reference, new_status)
                return True
        return False

    # ── listing for the admin /claims page ────────────────────────────────────
    def list_claims(self, status: str = "submitted", company_code: str | None = None) -> list[dict]:
        try:
            q = (supabase.table("claim_intakes").select("*")
                 .eq("status", status).order("created_at", desc=True).limit(200))
            if company_code:
                q = q.eq("company_code", company_code)
            return q.execute().data or []
        except Exception:
            rows = [r for r in _MEM.values() if r.get("status") == status
                    and (not company_code or r.get("company_code") == company_code)]
            return sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)

    def _cancel(self, session_id: str) -> None:
        try:
            supabase.table("claim_intakes").update({"status": "cancelled"}).eq("session_id", session_id).eq("status", "collecting").execute()
        except Exception:
            pass
        self._clear_mem(session_id)


claim_service = ClaimService()
