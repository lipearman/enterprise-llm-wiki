import logging
import math
from app.core.config import settings
from app.core.text import normalize_question, sha256_text
from app.services.ollama_client import embed_llm, local_llm
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    """Character n-grams of *text* with whitespace removed (Thai has no word
    boundaries, so character n-grams are a segmentation-free overlap signal)."""
    s = "".join(text.split())
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def _ngram_jaccard(a: str, b: str, n: int = 3) -> float:
    """Jaccard overlap of character n-grams — robust for Thai, deterministic."""
    ga, gb = _char_ngrams(a, n), _char_ngrams(b, n)
    if not ga or not gb:
        return 0.0
    inter = len(ga & gb)
    union = len(ga | gb)
    return inter / union if union else 0.0


# Minimum character-n-gram overlap between the user question and the
# LLM-selected canonical question. Embedding cosine is unusable here because
# mxbai-embed-large returns near-identical vectors for *all* Thai text, so the
# gate uses a segmentation-free lexical overlap instead. Rejects matches where
# the Qwen matcher picked an entry that only shares the company name (e.g.
# "โครงสร้างผู้ถือหุ้น" matched to an address question) → falls through to RAG.
CANONICAL_VERIFY_MIN_OVERLAP = 0.18


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

        # Stable ordering (priority desc, then id) so the LLM's numeric pick maps
        # to a deterministic candidate. Without this, candidates accumulate in
        # non-deterministic Postgres order and the same query can match different
        # entries on repeated calls.
        candidates.sort(key=lambda r: (-(r.get("priority") or 0), str(r.get("id"))))

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

                    # ── Verification gate (lexical overlap) ──────────────────
                    # Confirm the LLM-picked canonical question shares real
                    # wording with the user question. Uses character-n-gram
                    # Jaccard because mxbai embeddings can't distinguish Thai
                    # text. Rejects matches sharing only the company name (e.g.
                    # "โครงสร้างผู้ถือหุ้น" picked for an address question) →
                    # the request then falls through to full RAG.
                    overlap = _ngram_jaccard(
                        normalize_question(question),
                        normalize_question(matched.get("question", "")),
                    )
                    if overlap < CANONICAL_VERIFY_MIN_OVERLAP:
                        logger.info(
                            "canonical_qa_rejected_low_overlap | overlap=%.3f < %.2f | q=%r | canonical=%r",
                            overlap, CANONICAL_VERIFY_MIN_OVERLAP,
                            question[:60], matched.get("question", "")[:60],
                        )
                        return None

                    matched["similarity"] = 1.0   # verified match → treat as exact
                    logger.info(
                        "canonical_qa_llm_matched | overlap=%.3f | q=%r | canonical=%r",
                        overlap, question[:80], matched.get("question", "")[:80],
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
            try:
                res = supabase.rpc("match_wiki_pages", {
                    "query_embedding": q_emb,
                    "match_company_code": company_code,
                    "match_threshold": settings.SIMILARITY_THRESHOLD,
                    "match_count": settings.RETRIEVAL_TOP_K,
                }).execute()
                wiki_rows = res.data or []
                rows.extend([{**x, "source_type": "wiki"} for x in wiki_rows])
                logger.debug("vector_search_wiki | found=%d | company=%s", len(wiki_rows), company_code)
            except Exception as exc:
                logger.warning(
                    "vector_search_wiki_error | company=%s | %s: %s — "
                    "check embedding dimension (stored vs query). "
                    "Run sql/008_update_embedding_dim_1024.sql if you switched models.",
                    company_code, type(exc).__name__, exc,
                )

        if settings.ENABLE_CHUNK_SEARCH:
            try:
                res = supabase.rpc("match_document_chunks", {
                    "query_embedding": q_emb,
                    "match_company_code": company_code,
                    "match_threshold": settings.SIMILARITY_THRESHOLD,
                    "match_count": settings.RETRIEVAL_TOP_K,
                }).execute()
                chunk_rows = res.data or []
                rows.extend([{**x, "source_type": "chunk"} for x in chunk_rows])
                logger.debug("vector_search_chunks | found=%d | company=%s", len(chunk_rows), company_code)
            except Exception as exc:
                logger.warning(
                    "vector_search_chunks_error | company=%s | %s: %s — "
                    "check embedding dimension (stored vs query). "
                    "Run sql/008_update_embedding_dim_1024.sql if you switched models.",
                    company_code, type(exc).__name__, exc,
                )

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

        # ── FlashRank reranker (optional) ─────────────────────────────────
        if settings.ENABLE_RERANKER and rows:
            rows = self._rerank(question, rows)

        # ── De-duplicate near-identical content ───────────────────────────
        # The KB ingests the same boilerplate (nav/footer, shared page blocks)
        # under several URLs/titles. Those duplicates score the same similarity
        # and crowd out genuinely distinct chunks, hurting context precision.
        # Keep only the first (highest-similarity) copy of each content block.
        before = len(rows)
        rows = self._dedupe_by_content(rows)
        deduped = before - len(rows)

        result = rows[: settings.RERANK_TOP_K]
        if deduped:
            logger.debug("search_context_dedup | removed=%d duplicate chunks", deduped)
        logger.info(
            "search_context | company=%s | total_rows=%d | returned=%d | reranker=%s | q=%r",
            company_code, len(rows), len(result), settings.ENABLE_RERANKER, question[:60],
        )
        return result

    @staticmethod
    def _dedupe_by_content(rows: list[dict]) -> list[dict]:
        """Drop rows that are *exact* content duplicates of an already-kept row.

        The fingerprint is the whitespace-normalized FULL content. This removes
        boilerplate ingested verbatim under several URLs/titles, while keeping
        chunks that merely share a header but differ in the body (e.g. two
        "Company Profile" chunks — one with the founding capital, one with the
        current capital — must both survive). The first occurrence (highest
        similarity, list is pre-sorted) is kept.
        """
        seen: set[str] = set()
        out: list[dict] = []
        for r in rows:
            content = (r.get("content_markdown") or r.get("content") or r.get("answer") or "")
            key = "".join(content.split())
            if not key:
                out.append(r)
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out

    @staticmethod
    def _rerank(question: str, rows: list[dict]) -> list[dict]:
        """Re-rank rows with FlashRank cross-encoder and return sorted list."""
        try:
            from flashrank import Ranker, RerankRequest

            ranker = Ranker(model_name="ms-marco-MultiBERT-L-12", cache_dir="/tmp/flashrank")
            passages = [
                {
                    "id":   i,
                    "text": r.get("content_markdown") or r.get("content") or r.get("answer") or "",
                }
                for i, r in enumerate(rows)
            ]
            rerank_req = RerankRequest(query=question, passages=passages)
            result     = ranker.rerank(rerank_req)

            # Map scores back and re-sort
            score_map = {item["id"]: item["score"] for item in result}
            for i, r in enumerate(rows):
                r["rerank_score"] = score_map.get(i, 0.0)
            rows.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            logger.debug("reranker | reranked %d rows", len(rows))
        except Exception as exc:
            logger.warning("reranker | skipped: %s", exc)
        return rows

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

    @staticmethod
    def _dedupe_terms(terms: list[str], cap: int = 20) -> list[str]:
        """Unique, order-preserving search terms safe for a PostgREST `or` filter.

        Drops terms containing characters that would break the comma/dot-delimited
        or-filter syntax, and caps the count to keep the request URL bounded.
        """
        out: list[str] = []
        seen: set[str] = set()
        for t in terms:
            t = t.strip()
            if not t or t in seen:
                continue
            if any(c in t for c in (",", ".", "*", "(", ")", ":")):
                continue
            seen.add(t)
            out.append(t)
            if len(out) >= cap:
                break
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
        semantic_kws = self._get_semantic_keywords(q_search)
        terms = self._dedupe_terms(substrings + semantic_kws)
        logger.debug(
            "text_search_wiki | q=%r | stripped=%r | terms=%d",
            question[:40], q_search[:30], len(terms),
        )
        if not terms:
            return []

        hits: dict[str, dict] = {}   # id → row + counters

        def _add_row(row: dict, title_hit: bool) -> None:
            rid = str(row["id"])
            if rid not in hits:
                title   = row.get("title") or ""
                content = row.get("content_markdown") or ""
                # Count distinct matched terms in-memory (no extra DB calls) so
                # rows matching more of the query rank higher.
                cnt = sum(1 for t in terms if t in title or t in content)
                hits[rid] = {**row, "source_type": "wiki", "_cnt": max(cnt, 1), "_title": title_hit}
            elif title_hit:
                hits[rid]["_title"] = True

        # Two combined OR-queries replace ~2×N sequential ILIKE calls.
        try:
            title_or = ",".join(f"title.ilike.*{t}*" for t in terms)
            for row in (
                supabase.table("wiki_pages")
                .select("id,title,slug,content_markdown,source_urls")
                .eq("company_code", company_code)
                .or_(title_or).limit(30).execute().data or []
            ):
                _add_row(row, title_hit=True)

            content_or = ",".join(f"content_markdown.ilike.*{t}*" for t in terms)
            for row in (
                supabase.table("wiki_pages")
                .select("id,title,slug,content_markdown,source_urls")
                .eq("company_code", company_code)
                .or_(content_or).limit(30).execute().data or []
            ):
                _add_row(row, title_hit=False)
        except Exception as exc:
            logger.warning("text_search_wiki | or_query | err=%s", exc)

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
        terms = self._dedupe_terms(substrings + semantic_kws)
        if not terms:
            return []

        hits: dict[str, dict] = {}

        def _add_chunk(row: dict) -> None:
            rid = str(row["id"])
            if rid not in hits:
                content = row.get("content") or ""
                cnt = sum(1 for t in terms if t in content)
                hits[rid] = {**row, "source_type": "chunk", "_cnt": max(cnt, 1)}

        # Single combined OR-query replaces ~N sequential ILIKE calls.
        try:
            content_or = ",".join(f"content.ilike.*{t}*" for t in terms)
            for row in (
                supabase.table("document_chunks")
                .select("id,title,content,source_url")
                .eq("company_code", company_code)
                .or_(content_or).limit(50).execute().data or []
            ):
                _add_chunk(row)
        except Exception as exc:
            logger.warning("text_search_chunks | or_query | err=%s", exc)

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
