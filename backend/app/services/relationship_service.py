import json
import logging
from app.core.config import settings
from app.db.supabase_client import supabase
from app.services.ollama_client import chat_llm

logger = logging.getLogger(__name__)

RELATIONSHIP_TYPES = [
    "has_coverage",    # A ครอบคลุม B
    "requires",        # A ต้องการ B
    "part_of",         # A เป็นส่วนหนึ่งของ B
    "related_to",      # A เกี่ยวข้องกับ B
    "applies_to",      # A ใช้กับ B
    "excludes",        # A ยกเว้น B
    "contacts",        # A ติดต่อผ่าน B
    "located_at",      # A อยู่ที่ B
    "replaces",        # A แทนที่ B
    "depends_on",      # A ขึ้นอยู่กับ B
]


class RelationshipService:

    async def extract_relationships(
        self,
        company_code: str,
        wiki_page_id: str | None,
        title: str,
        content: str,
    ) -> list[dict]:
        """Extract entity relationships from wiki page content using LLM."""

        prompt = f"""วิเคราะห์หน้า Wiki นี้และสกัด relationships ระหว่าง entities

กฎ:
1. ตอบเป็น JSON array เท่านั้น ห้ามมีข้อความอื่น
2. แต่ละ item มี: source, target, type, weight (0.1-1.0)
3. type ต้องเป็นหนึ่งใน: {", ".join(RELATIONSHIP_TYPES)}
4. สกัดอย่างน้อย 3 relationships อย่างมาก 10 relationships
5. ใช้ชื่อ entity เป็นภาษาไทยหรืออังกฤษตามที่ปรากฏในเนื้อหา

ตัวอย่าง output:
[
  {{"source": "ประกันรถยนต์ชั้น 1", "target": "ความเสียหายจากอุบัติเหตุ", "type": "has_coverage", "weight": 1.0}},
  {{"source": "การเรียกร้องสินไหม", "target": "เอกสารประกอบ", "type": "requires", "weight": 0.9}}
]

TITLE: {title}
CONTENT:
{content[:3000]}
"""

        try:
            raw = await chat_llm.chat(
                [
                    {"role": "system", "content": "You extract structured entity relationships from wiki content. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                model=settings.OLLAMA_CHAT_MODEL,
            )

            # Parse JSON — strip markdown code blocks if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:])
            if cleaned.endswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[:-1])

            relationships = json.loads(cleaned.strip())
            if not isinstance(relationships, list):
                raise ValueError("Expected a JSON array")

        except Exception as e:
            logger.warning(f"Relationship extraction failed for '{title}': {e}")
            return []

        return await self._save_relationships(company_code, wiki_page_id, relationships)

    async def _save_relationships(
        self,
        company_code: str,
        wiki_page_id: str | None,
        relationships: list[dict],
    ) -> list[dict]:
        """Persist relationships to wiki_relationships table."""
        saved = []
        for rel in relationships:
            source = str(rel.get("source", "")).strip()
            target = str(rel.get("target", "")).strip()
            rel_type = str(rel.get("type", "related_to")).strip()
            weight = float(rel.get("weight", 1.0))

            if not source or not target:
                continue
            if rel_type not in RELATIONSHIP_TYPES:
                rel_type = "related_to"

            try:
                res = supabase.table("wiki_relationships").insert({
                    "company_code": company_code,
                    "source_entity": source,
                    "target_entity": target,
                    "relationship_type": rel_type,
                    "weight": weight,
                    "metadata": {"wiki_page_id": wiki_page_id} if wiki_page_id else {},
                }).execute()
                if res.data:
                    saved.append(res.data[0])
            except Exception as e:
                logger.warning(f"Failed to save relationship {source} -> {target}: {e}")

        return saved

    def find_related_entities(self, company_code: str, entities: list[str], limit: int = 20) -> list[dict]:
        """Query wiki_relationships to find entities related to the given list."""
        if not entities:
            return []
        results = []
        for entity in entities[:5]:  # cap to avoid too many queries
            try:
                res = supabase.table("wiki_relationships").select(
                    "source_entity,target_entity,relationship_type,weight,metadata"
                ).eq("company_code", company_code).or_(
                    f"source_entity.ilike.%{entity}%,target_entity.ilike.%{entity}%"
                ).order("weight", desc=True).limit(limit).execute()
                results.extend(res.data or [])
            except Exception as e:
                logger.warning(f"Relationship query failed for entity '{entity}': {e}")
        return results


relationship_service = RelationshipService()
