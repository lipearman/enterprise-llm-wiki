"""
BotSettingsService — load/save per-company bot configuration from Supabase.

Settings stored in the `bot_settings` table:
  no_answer_phrases   : list[str]
  clarify_phrases     : list[str]
  ambiguous_keywords  : dict[str, list[str]]
  clear_question_words: list[str]

Values are cached in-memory and fall back to the hardcoded defaults when
the table row is missing (e.g. first run before 009_bot_settings.sql).
"""

from __future__ import annotations

import logging
from typing import Any

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)

# ── Hardcoded defaults (used as fallback if DB row is absent) ─────────────────
_DEFAULTS: dict[str, Any] = {
    "no_answer_phrases": [
        "ยังไม่มีข้อมูล",
        "ไม่มีข้อมูลส่วนนี้",
        "ไม่พบข้อมูล",
        "ไม่มีข้อมูลเกี่ยวกับ",
        "ไม่มีข้อมูลในระบบ",
        "ไม่มีในฐานข้อมูล",
    ],
    "clarify_phrases": [
        "หมายถึงอะไรครับ",
        "หมายถึงอะไรคะ",
        "ต้องการข้อมูลส่วนไหน",
        "ต้องการทราบข้อมูลส่วนไหน",
        "กรุณาระบุเพิ่มเติม",
        "ขอทราบเพิ่มเติม",
    ],
    "ambiguous_keywords": {
        "เบอร์":   ["เบอร์โทรศัพท์", "เบอร์กรมธรรม์", "เบอร์เคลม", "เบอร์มือถือ"],
        "รหัส":   ["รหัสกรมธรรม์", "รหัสอ้างอิง", "รหัสสาขา"],
        "ราคา":   ["ราคาเบี้ยประกัน", "ราคาซ่อม", "ราคาต่ออายุ"],
        "ติดต่อ": ["ช่องทางโทรศัพท์", "ช่องทางอีเมล", "ที่อยู่สำนักงาน"],
        "ที่อยู่": ["ที่อยู่สำนักงานใหญ่", "ที่อยู่สาขา"],
        "เอกสาร": ["เอกสารการเคลม", "เอกสารต่อกรมธรรม์", "เอกสารใบแจ้งหนี้"],
    },
    "clear_question_words": [
        "ที่ไหน", "อยู่ที่ไหน", "ได้ที่ไหน",
        "อย่างไร", "ยังไง",
        "คืออะไร", "หมายความว่าอะไร",
        "ทำอะไร", "ทำได้ไหม", "ทำยังไง",
        "เมื่อไหร่", "เท่าไหร่", "กี่บาท",
        "คือใคร", "มีไหม", "ใช่ไหม",
    ],
}

_ALL_KEYS = list(_DEFAULTS.keys())


class BotSettingsService:
    """Per-company bot configuration with in-memory cache."""

    def __init__(self) -> None:
        # cache: { company_code: { setting_key: value } }
        self._cache: dict[str, dict[str, Any]] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, company_code: str, key: str) -> Any:
        """Return the value for *key*, loading from DB if not yet cached."""
        if company_code not in self._cache:
            self._load(company_code)
        return self._cache[company_code].get(key, _DEFAULTS.get(key))

    def get_all(self, company_code: str) -> dict[str, Any]:
        """Return all settings for *company_code* as a dict."""
        if company_code not in self._cache:
            self._load(company_code)
        result: dict[str, Any] = {}
        for key in _ALL_KEYS:
            result[key] = self._cache[company_code].get(key, _DEFAULTS.get(key))
        return result

    def save(self, company_code: str, key: str, value: Any) -> None:
        """Persist *value* to Supabase and update the in-memory cache."""
        if key not in _ALL_KEYS:
            raise ValueError(f"Unknown setting key: {key!r}")
        supabase.table("bot_settings").upsert({
            "company_code": company_code,
            "setting_key":  key,
            "setting_value": value,
        }).execute()
        # Update cache
        if company_code not in self._cache:
            self._cache[company_code] = {}
        self._cache[company_code][key] = value
        logger.info("bot_settings_saved | company=%s | key=%s", company_code, key)

    def reload(self, company_code: str) -> None:
        """Force-reload all settings for *company_code* from DB."""
        self._cache.pop(company_code, None)
        self._load(company_code)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _load(self, company_code: str) -> None:
        """Load all rows for *company_code* into cache (falls back to defaults)."""
        self._cache[company_code] = {}
        try:
            res = (
                supabase.table("bot_settings")
                .select("setting_key, setting_value")
                .eq("company_code", company_code)
                .execute()
            )
            for row in (res.data or []):
                self._cache[company_code][row["setting_key"]] = row["setting_value"]
            logger.debug(
                "bot_settings_loaded | company=%s | keys=%s",
                company_code,
                list(self._cache[company_code].keys()),
            )
        except Exception as exc:
            logger.warning(
                "bot_settings_load_error | company=%s | %s: %s — using defaults",
                company_code, type(exc).__name__, exc,
            )


bot_settings_service = BotSettingsService()
