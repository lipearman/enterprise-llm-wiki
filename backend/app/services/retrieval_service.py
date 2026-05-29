import logging
from app.core.config import settings
from app.core.text import normalize_question, sha256_text
from app.services.ollama_client import embed_llm, local_llm
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


class RetrievalService:
    async def query_embedding(self, question: str) -> list[float]:
        return await embed_llm.embed(normalize_question(question))

    async def match_answer_cache(self, question: str, company_code: str) -> dict | None:
        if not settings.ENABLE_ANSWER_CACHE:
            return None
        q_emb = await self.query_embedding(question)
        res = supabase.rpc("match_answer_cache", {
            "query_embedding": q_emb,
            "match_company_code": company_code,
            "match_threshold": settings.ANSWER_CACHE_THRESHOLD,
            "match_count": 1,
        }).execute()
        return res.data[0] if res.data else None

    async def match_canonical_qa(self, question: str, company_code: str) -> dict | None:
        """Match user question against canonical Q&A using Qwen2.5 LLM.

        Pre-filters candidates via substring text search (works for Thai),
        then asks the local Qwen2.5 model to determine the best semantic match.
        Falls back to top-priority entries when text search yields nothing.
        """
        if not settings.ENABLE_CANONICAL_QA:
            return None

        # ── Step 1: pre-filter via substring search ──────────────────────────
        # Step-3 sliding window so any keyword anywhere in the question is
        # covered (same approach as _text_search_chunks).
        candidates: list[dict] = []
        seen_ids: set = set()
        q = normalize_question(question)
        substrings = RetrievalService._make_search_windows(q, win_len=10, step=3)
        for substr in substrings:
            rows = (
                supabase.table("canonical_qa")
                .select("id,question,answer,priority")
                .eq("company_code", company_code)
                .eq("is_active", True)
                .ilike("question", f"%{substr}%")
                .limit(20)
                .execute()
                .data or []
            )
            for row in rows:
                if row["id"] not in seen_ids:
                    candidates.append(row)
                    seen_ids.add(row["id"])

        # No text-based candidates → question likely doesn't match any canonical Q&A.
        # Skip LLM call to avoid false positives from unrelated top-priority entries.
        if not candidates:
            logger.debug("canonical_qa_no_text_candidates | q=%r", question[:80])
            return None

        # Trim to max candidates
        candidates = candidates[: settings.CANONICAL_QA_MAX_CANDIDATES]

        # ── Step 2: LLM semantic matching via Qwen2.5 ───────────────────────
        qa_list = "\n".join(
            f"{i + 1}. {r['question']}" for i, r in enumerate(candidates)
        )
        prompt = (
            f"User question: \"{question}\"\n\n"
            f"Canonical questions:\n{qa_list}\n\n"
            "Task: find the canonical question that asks about THE SAME THING as the user's question.\n"
            "- If you find one, reply with ONLY its number (e.g. 2).\n"
            "- If none asks about the same thing, reply with ONLY 0.\n"
            "- Do NOT match on company name alone. Topic/intent must match.\n"
            "Number:"
        )
        try:
            raw = await local_llm.chat(
                [{"role": "user", "content": prompt}],
                model=settings.CANONICAL_QA_MODEL,
            )
            token = raw.strip().split()[0] if raw.strip() else "0"
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(candidates):
                    matched = candidates[idx]
                    matched["similarity"] = 1.0   # LLM match → treat as exact
                    logger.info(
                        "canonical_qa_llm_matched | q=%r | canonical=%r",
                        question[:80], matched.get("question", "")[:80],
                    )
                    return matched
            logger.debug(
                "canonical_qa_llm_no_match | q=%r | llm_response=%r",
                question[:80], raw[:40],
            )
        except Exception as e:
            logger.warning("canonical_qa_llm_error | q=%r | err=%s", question[:80], e)

        return None

    async def search_context(self, question: str, company_code: str) -> list[dict]:
        q_emb = await self.query_embedding(question)
        rows = []

        if settings.ENABLE_WIKI_SEARCH:
            res = supabase.rpc("match_wiki_pages", {
                "query_embedding": q_emb,
                "match_company_code": company_code,
                "match_threshold": settings.SIMILARITY_THRESHOLD,
                "match_count": settings.RETRIEVAL_TOP_K,
            }).execute()
            rows.extend([{**x, "source_type": "wiki"} for x in (res.data or [])])

        if settings.ENABLE_CHUNK_SEARCH:
            res = supabase.rpc("match_document_chunks", {
                "query_embedding": q_emb,
                "match_company_code": company_code,
                "match_threshold": settings.SIMILARITY_THRESHOLD,
                "match_count": settings.RETRIEVAL_TOP_K,
            }).execute()
            rows.extend([{**x, "source_type": "chunk"} for x in (res.data or [])])

        # ── Text search: compensates for Thai embedding limitations ──────────
        # mxbai-embed-large gives near-identical vectors for Thai text, so
        # cosine-similarity ranking is essentially random.  Sliding-window
        # ILIKE on titles (wiki) and content (chunks) surfaces the right docs.
        existing_ids = {r.get("id") for r in rows}

        # Wiki title search
        wiki_by_id = {r.get("id"): r for r in rows if r.get("source_type") == "wiki"}
        for r in await self._text_search_wiki(question, company_code):
            rid = r.get("id")
            if rid not in existing_ids:
                rows.append(r)
                existing_ids.add(rid)
            elif rid in wiki_by_id:
                wiki_by_id[rid]["similarity"] = (wiki_by_id[rid].get("similarity") or 0) + 0.3

        # Chunk content search
        chunk_by_id = {r.get("id"): r for r in rows if r.get("source_type") == "chunk"}
        for r in await self._text_search_chunks(question, company_code):
            rid = r.get("id")
            if rid not in existing_ids:
                rows.append(r)
                existing_ids.add(rid)
            elif rid in chunk_by_id:
                chunk_by_id[rid]["similarity"] = (chunk_by_id[rid].get("similarity") or 0) + 0.3

        # Metadata search: boost pages whose title/slug contains question keywords
        if settings.ENABLE_METADATA_SEARCH and rows:
            rows = self._apply_metadata_boost(rows, question)

        # Graph expansion: find related wiki pages via relationships
        if settings.ENABLE_RELATIONSHIP_SEARCH and rows:
            related = await self._expand_via_relationships(rows, company_code, q_emb)
            existing_ids = {r.get("id") for r in rows}
            for r in related:
                if r.get("id") not in existing_ids:
                    rows.append(r)
                    existing_ids.add(r.get("id"))

        rows.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return rows[: settings.RERANK_TOP_K]

    @staticmethod
    def _get_semantic_keywords(q: str) -> list[str]:
        """Return extra search keywords that cover Thai synonyms for common topics.

        Supabase text search is exact-string, so we must explicitly add synonym
        variants.  For example, the user may ask with "เบอร์โทร" but the wiki
        page uses "โทรศัพท์" — without expansion the page is never found.

        Only adds terms whose root word actually appears in the stripped query.
        """
        extra: list[str] = []

        # ── Phone / contact ───────────────────────────────────────────────
        if any(w in q for w in ("เบอร์โทร", "โทรศัพท์", "เบอร์ติดต่อ", "โทร", "phone", "tel")):
            for kw in ("โทรศัพท์", "เบอร์โทร", "ติดต่อ", "tel", "phone"):
                if kw not in q:
                    extra.append(kw)

        # ── Address / location ────────────────────────────────────────────
        if any(w in q for w in ("ที่อยู่", "address", "ที่ตั้ง", "สำนักงาน")):
            for kw in ("ที่อยู่", "ที่ตั้ง", "สำนักงาน", "ติดต่อ", "address"):
                if kw not in q:
                    extra.append(kw)

        # ── Email ─────────────────────────────────────────────────────────
        if any(w in q for w in ("อีเมล", "email", "อีเมล์", "e-mail", "mail")):
            for kw in ("อีเมล", "email", "e-mail"):
                if kw not in q:
                    extra.append(kw)

        # ── Website / social ──────────────────────────────────────────────
        if any(w in q for w in ("เว็บ", "website", "เว็บไซต์", "facebook", "line")):
            for kw in ("เว็บไซต์", "website", "เว็บ"):
                if kw not in q:
                    extra.append(kw)

        return list(dict.fromkeys(extra))   # deduplicate, preserve order

    @staticmethod
    def _strip_particles(q: str) -> str:
        """Strip common Thai polite/request particles so raw keywords remain.

        Examples
        --------
        "ขอที่อยู่หน่อย"       → "ที่อยู่"
        "ช่วยบอกเบอร์โทรด้วยครับ" → "บอกเบอร์โทร"
        "กรุณาระบุที่ตั้งสำนักงาน"  → "ระบุที่ตั้งสำนักงาน"
        """
        # Leading particles — try longest first so "กรุณา" beats "กร"
        for prefix in ("กรุณา", "ช่วย", "ขอ"):
            if q.startswith(prefix) and len(q) > len(prefix):
                q = q[len(prefix):]
                break
        # Trailing particles — longest first to avoid partial strip
        for suffix in (
            "หน่อยนะครับ", "หน่อยนะคะ", "หน่อยได้ไหม",
            "หน่อยครับ", "หน่อยค่ะ", "หน่อยนะ", "หน่อย",
            "ด้วยครับ", "ด้วยค่ะ", "ด้วยนะ", "ด้วย",
            "นะครับ", "นะคะ", "ครับ", "ค่ะ", "คะ", "นะ",
        ):
            if q.endswith(suffix) and len(q) > len(suffix):
                q = q[: -len(suffix)]
                break
        return q.strip()

    @staticmethod
    def _make_search_windows(q: str, win_len: int = 10, step: int = 3) -> list[str]:
        """Return a deduplicated list of substrings sampled every *step* chars.

        A stride of 3 chars guarantees that any keyword of length ≥ win_len
        that appears anywhere in the question is covered by at least one
        window — even if it straddles the midpoint of the question.

        Example for "ใครคือผู้ถือหุ้นใหญ่" (len=20, step=3, win=10):
            pos 0 → "ใครคือผู้ถ"
            pos 3 → "คือผู้ถือหุ"
            pos 6 → "ผู้ถือหุ้น"  ← catches "ผู้ถือหุ้น" in the shareholder page
            pos 9 → "ถือหุ้นใหญ่"
            ...
        """
        q_len = len(q)
        seen: set[str] = set()
        out: list[str] = []
        for start in range(0, q_len, step):
            length = min(win_len, q_len - start)
            if length < 4:
                break
            substr = q[start: start + length]
            if substr not in seen:
                seen.add(substr)
                out.append(substr)
        return out

    async def _text_search_wiki(self, question: str, company_code: str) -> list[dict]:
        """Sliding-window substring search on wiki_pages title AND content_markdown.

        Key improvements over the original title-only approach:
        - Strips Thai polite particles ("ขอ…หน่อย", "ครับ", etc.) so raw
          keywords remain (e.g. "ขอที่อยู่หน่อย" → "ที่อยู่").
        - Uses win_len=7 (down from 10) so 7-char keywords like "ที่อยู่"
          produce an exact-match window instead of being buried in noise.
        - Adaptive step: step=1 for short stripped queries (≤12 chars) so
          every start position is covered; step=2 for longer ones.
        - Also searches content_markdown so pages titled "ติดต่อเรา" whose
          body contains an address are still surfaced.
        """
        q = normalize_question(question)
        q_search = self._strip_particles(q)  # remove polite wrappers
        if not q_search:
            q_search = q
        # Adaptive step: fine-grained for short queries, coarser for long ones
        step = 1 if len(q_search) <= 12 else 2
        substrings = self._make_search_windows(q_search, win_len=7, step=step)

        # Add semantic synonyms so "เบอร์โทร" also searches "โทรศัพท์", etc.
        semantic_kws = self._get_semantic_keywords(q_search)
        logger.debug(
            "text_search_wiki | q=%r | stripped=%r | windows=%s | synonyms=%s",
            question[:40], q_search[:30], substrings, semantic_kws,
        )

        hits: dict[str, dict] = {}   # id → row + counters

        def _add_row(row: dict, title_hit: bool) -> None:
            rid = str(row["id"])
            if rid not in hits:
                hits[rid] = {**row, "source_type": "wiki", "_cnt": 0, "_title": False}
            hits[rid]["_cnt"] += 1
            if title_hit:
                hits[rid]["_title"] = True

        for substr in substrings:
            try:
                # ── Title search (strong signal) ─────────────────────────
                for row in (
                    supabase.table("wiki_pages")
                    .select("id,title,slug,content_markdown,source_urls")
                    .eq("company_code", company_code)
                    .ilike("title", f"%{substr}%")
                    .limit(5).execute().data or []
                ):
                    _add_row(row, title_hit=True)

                # ── Content search (weaker signal) ────────────────────────
                for row in (
                    supabase.table("wiki_pages")
                    .select("id,title,slug,content_markdown,source_urls")
                    .eq("company_code", company_code)
                    .ilike("content_markdown", f"%{substr}%")
                    .limit(3).execute().data or []
                ):
                    _add_row(row, title_hit=False)

            except Exception as exc:
                logger.warning("text_search_wiki | substr=%r | err=%s", substr[:12], exc)

        # ── Semantic synonym search ────────────────────────────────────────
        # Handles cases where the DB uses a different Thai/English word for
        # the same concept (e.g. wiki says "โทรศัพท์" but user asked "เบอร์โทร")
        for kw in semantic_kws:
            try:
                for row in (
                    supabase.table("wiki_pages")
                    .select("id,title,slug,content_markdown,source_urls")
                    .eq("company_code", company_code)
                    .ilike("title", f"%{kw}%")
                    .limit(5).execute().data or []
                ):
                    _add_row(row, title_hit=True)
                for row in (
                    supabase.table("wiki_pages")
                    .select("id,title,slug,content_markdown,source_urls")
                    .eq("company_code", company_code)
                    .ilike("content_markdown", f"%{kw}%")
                    .limit(3).execute().data or []
                ):
                    _add_row(row, title_hit=False)
            except Exception as exc:
                logger.warning("text_search_wiki | kw=%r | err=%s", kw[:12], exc)

        out = []
        for row in hits.values():
            cnt        = row.pop("_cnt", 1)
            title_hit  = row.pop("_title", False)
            # Title match: 0.70–0.95 | content-only match: 0.58–0.73
            if title_hit:
                row["similarity"] = 0.70 + min(0.25, 0.08 * cnt)
            else:
                row["similarity"] = 0.58 + min(0.15, 0.05 * cnt)
            out.append(row)
        return sorted(out, key=lambda x: x.get("similarity", 0), reverse=True)[:10]

    async def _text_search_chunks(self, question: str, company_code: str) -> list[dict]:
        """Sliding-window ILIKE on document_chunks.content.

        Uses the same particle-stripping and adaptive-step logic as
        _text_search_wiki so short Thai keywords are correctly extracted.
        """
        q = normalize_question(question)
        q_search = self._strip_particles(q)
        if not q_search:
            q_search = q
        step = 1 if len(q_search) <= 12 else 2
        substrings = self._make_search_windows(q_search, win_len=7, step=step)
        semantic_kws = self._get_semantic_keywords(q_search)

        hits: dict[str, dict] = {}

        def _add_chunk(row: dict) -> None:
            rid = str(row["id"])
            if rid not in hits:
                hits[rid] = {**row, "source_type": "chunk", "_cnt": 0}
            hits[rid]["_cnt"] += 1

        for substr in substrings:
            try:
                for row in (
                    supabase.table("document_chunks")
                    .select("id,title,content,source_url")
                    .eq("company_code", company_code)
                    .ilike("content", f"%{substr}%")
                    .limit(5).execute().data or []
                ):
                    _add_chunk(row)
            except Exception as exc:
                logger.warning("text_search_chunks | substr=%r | err=%s", substr[:12], exc)

        # Semantic synonym search for chunks
        for kw in semantic_kws:
            try:
                for row in (
                    supabase.table("document_chunks")
                    .select("id,title,content,source_url")
                    .eq("company_code", company_code)
                    .ilike("content", f"%{kw}%")
                    .limit(3).execute().data or []
                ):
                    _add_chunk(row)
            except Exception as exc:
                logger.warning("text_search_chunks | kw=%r | err=%s", kw[:12], exc)

        out = []
        for row in hits.values():
            cnt = row.pop("_cnt", 1)
            row["similarity"] = 0.65 + min(0.25, 0.08 * cnt)   # 0.73 – 0.90
            out.append(row)
        return sorted(out, key=lambda x: x.get("similarity", 0), reverse=True)[:5]

    def _apply_metadata_boost(self, rows: list[dict], question: str) -> list[dict]:
        """Boost similarity score for pages whose title/slug matches question keywords."""
        keywords = [w.lower() for w in question.split() if len(w) > 2]
        if not keywords:
            return rows

        boosted = []
        for row in rows:
            title = (row.get("title") or "").lower()
            slug = (row.get("slug") or "").lower()
            combined = f"{title} {slug}"
            matches = sum(1 for kw in keywords if kw in combined)
            if matches > 0:
                boost = min(0.05 * matches, 0.15)
                # Allow scores above 1.0 so boosted docs still sort above the rest
                row = {**row, "similarity": (row.get("similarity") or 0) + boost}
            boosted.append(row)
        return boosted

    async def _expand_via_relationships(
        self, base_rows: list[dict], company_code: str, q_emb: list[float]
    ) -> list[dict]:
        """Expand context by following wiki_relationships edges from found pages."""
        from app.services.relationship_service import relationship_service

        top_wiki = [r for r in base_rows if r.get("source_type") == "wiki"][:3]
        entities = [r.get("title", "") for r in top_wiki if r.get("title")]
        if not entities:
            return []

        graph_rows = relationship_service.find_related_entities(company_code, entities)
        if not graph_rows:
            return []

        related_entities: set[str] = set()
        for gr in graph_rows:
            related_entities.add(gr["source_entity"])
            related_entities.add(gr["target_entity"])
        related_entities -= set(entities)

        extra_rows: list[dict] = []
        for entity in list(related_entities)[:5]:
            try:
                res = supabase.table("wiki_pages").select(
                    "id,title,slug,content_markdown,source_urls"
                ).eq("company_code", company_code).ilike("title", f"%{entity}%").limit(2).execute()
                for page in (res.data or []):
                    extra_rows.append({
                        **page,
                        "source_type": "wiki_relationship",
                        "similarity": 0.5,
                    })
            except Exception as e:
                logger.warning(f"Relationship expand failed for entity '{entity}': {e}")

        return extra_rows

    def cache_key(self, question: str, company_code: str) -> str:
        return sha256_text(company_code + "|" + normalize_question(question))


retrieval_service = RetrievalService()
