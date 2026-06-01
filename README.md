<div align="center">

# 🏢 Enterprise LLM Wiki

**ระบบจัดการความรู้องค์กรแบบ RAG ครบวงจร — v0.2.0**

Chatbot · LLM Wiki · Knowledge Graph · Multi-Crawler · Multi-company · API Key Auth

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14+-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Cloud-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-1024d-336791?style=flat-square&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

</div>

---

## 📌 Overview

Enterprise LLM Wiki เป็น **full-stack knowledge management platform** สำหรับองค์กร รวมระบบหลัก 4 ส่วน:

| ระบบ | คำอธิบาย |
|---|---|
| 🤖 **RAG Chatbot** | ถาม-ตอบ 4 ชั้น: Answer Cache → Canonical QA → Wiki Search → Chunk Search |
| 📚 **LLM Wiki Generator** | URL/ไฟล์ → Facts → Wiki Page → Canonical QA → Entity Relationships อัตโนมัติ |
| 🕸️ **GraphRAG Knowledge Graph** | สกัด entity relationships ด้วย LLM → ขยาย context ผ่าน graph ตอน retrieval |
| 🕷️ **Multi-Crawler Pipeline** | เลือก crawler backend ได้: Trafilatura · Playwright · crawl4ai — ต่อ request หรือ global |
| 🔐 **API Key Authentication** | Middleware-based auth — Bearer token / X-API-Key header · Login page · auth guard |
| 💬 **Floating Chat Widget** | Chatbot สาธารณะบนหน้า Landing — ตอบคำถามแบบ SSE streaming ไม่ต้องล็อกอิน |
| 🔀 **Multi-Provider AI Failover** | กำหนด LLM/Embedding หลายเจ้าต่อ role ผ่าน UI · สลับอัตโนมัติเมื่อติด rate-limit · รองรับ Gemini ผ่าน OpenAI-compat |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    🌐 Frontend (Next.js 14+)                          │
│  🏠 Landing │ 💬 Admin Chat │ 📖 Wiki │ ❓ QA │ 🔗 Sources │ ⚙️ Jobs │
│  📭 Missed Q                                                          │
│  💬 Floating Chat Widget (public SSE streaming — ไม่ต้องล็อกอิน)      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼─────────────────────────────────────────┐
│                    ⚡ Backend (FastAPI v0.2.0)                         │
│  /chat · /public/chat · /sources · /wiki · /wiki/qa · /jobs          │
│  /companies · /unanswered                                            │
└──────┬──────────────────┬───────────────────┬─────────────────────────┘
       │                  │                   │
┌──────▼──────┐  ┌────────▼─────────┐  ┌──────▼───────────────────┐
│ 🔍 Retrieval │  │  📥 Ingest       │  │  🔄 Worker / Scheduler   │
│  Service    │  │  Pipeline        │  │  (APScheduler)           │
│             │  │                  │  │                          │
│ AnswerCache │  │ ┌─ 🕷️ Crawlers ─┐ │  │ Daily Crawl (cron)       │
│ CanonicalQA │  │ │ Trafilatura   │ │  │ Change Detection         │
│ WikiSearch  │  │ │ Playwright    │ │  │ Pending Job Runner       │
│ ChunkSearch │  │ │ crawl4ai      │ │  │                          │
│ GraphExpand │  │ └───────────────┘ │  └──────────────────────────┘
│ MetaBoost   │  │ Chunk & Embed    │
└──────┬──────┘  │ Wiki Generate    │
       │         │ QA Generate      │
       │         │ Relationship Ext.│
       │         └────────┬─────────┘
┌──────▼──────────────────▼──────────────────────────────────────────┐
│              🗄️ Supabase (PostgreSQL + pgvector)                     │
│  wiki_pages · canonical_qa · document_chunks · wiki_relationships   │
│  knowledge_sources · source_pages · answer_cache · job_runs         │
│  unanswered_questions                                               │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│           🔀 Provider Router (DB-backed, auto-failover)              │
│  role → [provider chain by priority] · 429/error → next provider    │
│  ☁️ cerebras · groq · sambanova · nvidia · openrouter · Gemini      │
│     (OpenAI-compatible) → answer_llm / fact / wiki / qa             │
│  🔢 embed → Gemini gemini-embedding-001 · 1024d (single provider)   │
│  💻 .env / local fallback (Ollama cloud · typhoon @ llm-server)     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Core Flows

### 📥 Ingest Flow (with Multi-Crawler)

```
URL / File
  │
  ├─ 🔍  Change Detection    (content_hash — skip if unchanged)
  │
  ├─ 🕷️  Crawler (เลือกได้)
  │       ├─ Trafilatura     httpx + trafilatura  → static HTML (default, เร็วที่สุด)
  │       ├─ Playwright      headless Chromium    → JavaScript SPA
  │       └─ crawl4ai        LLM-aware crawler    → Markdown คุณภาพสูงสุด
  │
  ├─ ✂️  Chunk               (LangChain Text Splitter)
  ├─ 🔢  Embed               (Ollama Local · mxbai-embed-large · 1024d)
  ├─ 💾  Save document_chunks + source_pages           ✅ searchable
  │
  ├─ 🧠  Extract Facts        (LLM)
  ├─ 📖  Generate Wiki Page   (LLM)
  ├─ ❓  Generate Canonical QA (LLM)
  ├─ 🕸️  Extract Relationships (LLM → entity graph)
  ├─ 🔢  Embed Wiki & QA
  └─ 💾  Save wiki_pages + canonical_qa + wiki_relationships  ✅ enriched
```

### 💬 Chat Flow (with GraphRAG + SSE Streaming)

```
Question
  │
  ├─ [0] 🧩  Smart Clarify Gate       คำถามกำกวม + ไม่เฉพาะ → ถามกลับ (ไม่เรียก LLM)
  ├─ [1] 🗃️  Answer Cache Search     threshold: 0.97  → ✅ return cached
  ├─ [2] ❓  Canonical QA Search      Qwen2.5 match → n-gram verify (≥0.18) → ✅ QA answer
  ├─ [3] 📖  Wiki Page Vector Search  top_k: 40
  │          Document Chunk Search    top_k: 40
  │          + Text Search (or-filter — ชดเชย vector ที่อ่อนกับไทย, ~3.5s)
  ├─ [4] 🕸️  Graph Expansion (GraphRAG)
  │          └─ wiki_relationships → find related entities → fetch related wiki pages
  ├─      🏷️  Metadata Boost         title/slug keyword scoring
  ├─      📊  Merge & Sort by similarity
  ├─      🧹  De-dup content (full)   ตัด chunk ซ้ำเป๊ะ → Top 8
  ├─      🤖  LLM → Grounded Answer  (cloud หรือ llm-server, SSE streaming)
  ├─      🛡️  Grounding Check         คำตอบตรงประเภทคำถามไหม → retry ถ้า fact-substitution
  ├─      💾  Save to answer_cache    (ข้าม "no data"/clarify)
  └─      📭  No answer → Save to unanswered_questions
```

### 💬 Floating Chat Flow (Public — no auth)

```
Visitor question (landing page)
  │
  ├─ POST /api/public/chat  (no API key required)
  ├─ SSE stream  → token by token
  └─ Same RAG pipeline as admin chat
     → context not found → unanswered_questions saved automatically
```

### 🧠 เทคนิคการจัดการข้อความใน Chat Service

#### 1. Python Ambiguity Gate — ตรวจคำกำกวมก่อน Cache

`_build_clarify_response()` ทำงานเป็น **interceptor ตัวแรก** ก่อนที่คำถามจะเข้า pipeline ใดๆ:

```
คำถาม → Python Ambiguity Gate → ถ้ากำกวม → ถามผู้ใช้ทันที (ไม่เรียก LLM)
                               → ถ้าชัดเจน → ผ่านต่อไป Cache / QA / RAG
```

- ตรวจ keyword เช่น `"ที่อยู่"` → แสดง choices `["ที่อยู่สาขา", "ที่อยู่สำนักงานใหญ่"]`
- ถ้าคำถามมี choice อยู่แล้ว (เช่น `"ที่อยู่สาขา"`) → ผ่านต่อ ไม่วนถาม
- Python เป็น **single source of truth** สำหรับ clarification — LLM prompt ไม่มีขั้นตอนถามกลับ

#### 2. Query Isolation — แยก `question` กับ `retrieval_q`

ระบบ rewrite query โดยเชื่อมคำถามก่อนหน้ากับคำถามปัจจุบัน (`retrieval_q`) เพื่อช่วย follow-up questions  
แต่ถ้าใช้ `retrieval_q` ตลอดจะเกิด **history contamination**:

```
ผู้ใช้ถาม "ที่อยู่สำนักงานใหญ่" → cache บันทึก retrieval_q
ผู้ใช้ถาม "ประกันรถยนต์"        → retrieval_q = "ที่อยู่สำนักงานใหญ่ ประกันรถยนต์"
                                  → cache hit ผิด → ได้คำตอบที่อยู่แทน
```

แก้โดยแยกการใช้งาน:

| ใช้ `question` (ต้นฉบับ) | ใช้ `retrieval_q` (enriched) |
|---|---|
| Answer Cache lookup | Vector Search (wiki + chunks) |
| Canonical QA lookup | — |
| LLM prompt QUESTION | — |

#### 3. Non-Streaming Workaround สำหรับ Cloud LLM

Cloud model (`gpt-oss:20b-cloud`) มีข้อจำกัด: เมื่อเรียกด้วย `stream=True` จะ **ไม่อ่าน CONTEXT** ที่ส่งไป ทำให้คำตอบผิดเสมอ

แก้โดย `_generate_answer_stream()` เรียก non-streaming API ภายใน แล้ว yield ผลลัพธ์เป็น token เดียว:

```python
async def _generate_answer_stream(self, question, context, history):
    answer = await self._generate_answer(question, context, history)  # stream=False
    yield answer   # yield once — SSE ยังทำงานปกติ
```

ผู้ใช้ยังได้รับ SSE stream ตามปกติ แต่ LLM ทำงานแบบ non-streaming จริงๆ

#### 4. Answer Cache Filtering — ไม่ cache คำตอบที่ไม่ดี

`_save_answer_cache()` ตรวจก่อน upsert ทุกครั้ง:

```
ถ้าคำตอบมี "ขณะนี้ยังไม่มีข้อมูล..." → ข้าม (ไม่ cache)
ถ้าคำตอบมี "หมายถึงอะไรครับ?"       → ข้าม (ไม่ cache clarification)
ถ้าไม่มี context rows                → ข้าม (RAG ไม่ได้ข้อมูล)
```

ป้องกันคำตอบ "no data" หรือ clarification question ถูก cache และส่งกลับผู้ใช้ครั้งต่อไป

#### 5. Smart Clarify — ไม่ถาม clarify เมื่อคำถามเฉพาะเจาะจงแล้ว

`_has_specific_context()` ป้องกันการถาม clarify เกินเหตุ เมื่อคำถามมี context เฉพาะอยู่แล้ว:

```
"ขอเอกสารหน่อย"                          → ตัด keyword + filler เหลือ "" → ถาม clarify
"เอกสารที่ต้องใช้ในการซื้อประกันรถยนต์"   → เหลือ "ซื้อประกันรถยนต์" (≥9 ตัว) → ตอบเลย
```

ตัด ambiguous keyword + Thai filler ออก ถ้าเหลือเนื้อหาเฉพาะ ≥ 9 ตัวอักษร ถือว่าผู้ใช้รู้ว่าต้องการอะไรแล้ว

#### 6. Canonical QA Verification Gate — character n-gram (ไม่ใช่ embedding)

หลัง Qwen2.5 เลือก canonical QA แล้ว ตรวจซ้ำด้วย **character-n-gram Jaccard overlap** ระหว่างคำถามผู้ใช้กับ canonical question ถ้า overlap < 0.18 → ปฏิเสธ → ตกไป RAG

```
"ที่อยู่สำนักงานใหญ่..."  vs  "โครงสร้างผู้ถือหุ้น..."  → jaccard 0.165 < 0.18 → reject ✅
"ทุนจดทะเบียน...เท่าไหร่" vs  "ทุนจดทะเบียนของเทเวศเท่าไหร่" → jaccard 0.449 → pass
```

> **⚠️ สำคัญ:** ใช้ n-gram ไม่ใช่ embedding cosine เพราะ **`mxbai-embed-large` ให้ vector เกือบเหมือนกันหมดสำหรับข้อความภาษาไทย** (cosine ≈ 1.0 แม้คนละเรื่อง) — vector search ภาษาไทยจึงอ่อน ต้องชดเชยด้วย text search + character n-gram

#### 7. Content De-duplication — ตัด chunk ซ้ำก่อนส่ง LLM

`_dedupe_by_content()` ตัด chunk ที่มีเนื้อหา**ซ้ำเป๊ะ** (boilerplate/nav/footer ที่ถูก ingest หลาย URL) โดย fingerprint = **full content** (whitespace-normalized) เก็บตัว similarity สูงสุด → คืน context slot ให้ chunk ที่เกี่ยวข้องจริง

> **⚠️ บทเรียน:** เดิมใช้ fingerprint 200 ตัวแรก แต่ chunk คนละเนื้อหาที่ขึ้นต้น header เหมือนกัน (เช่น "Company Profile" 2 อัน — อันหนึ่งทุนเริ่มต้น อีกอันทุนปัจจุบัน) โดน collapse ผิด → เปลี่ยนเป็น full-content เพื่อลบเฉพาะที่ซ้ำจริง

#### 8. Question-Type Matching — ตอบตรงประเภทคำถาม (LLM prompt)

LLM prompt มีกฎ: คำตอบต้องตรง "ประเภท" ของคำถาม แม้ CONTEXT มีข้อมูลอื่นปน
```
ถาม "ที่ไหน/ที่อยู่"  → ตอบสถานที่ (ห้ามตอบทุนจด/ปีก่อตั้ง)
ถาม "เมื่อไหร่/ปีไหน" → ตอบวัน/เวลา
ถาม "เท่าไหร่"        → ตอบจำนวน
```

#### 9. Answer Grounding Check — จับ fact-substitution หลัง generate

ด่านสุดท้ายหลัง LLM ตอบ: ตรวจ **deterministic** ว่าคำตอบ "ตรงประเภท" คำถามไหม (ต่อยอดจาก #8 แต่บังคับได้จริง ไม่พึ่ง LLM ทำตาม prompt)

```
_detect_question_type(q)  → location/amount/date/phone  (keyword match)
_answer_matches_type(a,t) → คำตอบมี marker ของประเภทนั้นไหม
                            location → ถนน/แขวง/เขต/อาคาร/เลขที่...
                            amount   → บาท/ล้าน  | date → 25xx/เดือน  | phone → digits
```

ถ้าคำถามถามหา type หนึ่งแต่คำตอบ**ไม่มี marker ของ type นั้น** (เช่น ถามที่อยู่ ตอบ "ทุนจดทะเบียน 500 ล้าน") → **retry 1 ครั้ง**ด้วย prompt เข้มขึ้น แล้วเก็บ retry เฉพาะเมื่อแก้ถูก (หรือยอมตอบ "ไม่มีข้อมูล")

- **ไม่เพิ่ม latency บน path ปกติ** — check เป็น string match (~0ms) retry fire เฉพาะตอน mismatch (หายาก)
- **Resilient** — retry ล้ม (rate limit) → คงคำตอบแรกไว้ ไม่พัง

---

## 🤖 Answer Generation Backend (configurable)

Generation model ของคำตอบ chat สลับได้ผ่าน `.env` โดยไม่ต้องแก้ code:

| `ANSWER_LLM_USE_LOCAL` | Backend | ความเร็ว | หมายเหตุ |
|---|---|---|---|
| `false` (default) | Cloud `gpt-oss:20b-cloud` | ⚡ 5-15s | คุณภาพดี แต่มี rate limit · บางคำถาม formal phrasing ตอบ fact ผิด |
| `true` | llm-server `ANSWER_LLM_MODEL` | 🐢 25-80s | ตาม question-type rule แม่นกว่า · ไม่มี rate limit · ช้ากว่าบน local GPU |

```env
ANSWER_LLM_USE_LOCAL=false           # cloud (เร็ว, default)
ANSWER_LLM_MODEL=qwen2.5:14b-instruct # ใช้เมื่อ USE_LOCAL=true
```

> Toggle นี้เป็น `.env` fallback — เมื่อมีการตั้ง provider chain (ด้านล่าง) ระบบจะใช้ provider ก่อน แล้วค่อย fallback มา `.env`/local

---

## 🔀 Multi-Provider AI Failover

ระบบเรียก LLM/Embedding ผ่าน **provider router แบบ DB-backed** — กำหนด provider หลายเจ้าต่อ "role" ได้ และ **สลับอัตโนมัติเมื่อเจ้าหนึ่งติด rate-limit (429) / error / timeout** โดยไม่ต้องแก้ `.env` หรือ restart

### แนวคิด: Role → ลำดับ Provider (failover chain)

แต่ละ role ผูกกับลิสต์ provider เรียงตาม `priority` — เรียกตัวแรกก่อน ถ้าล้ม (429/5xx/timeout/empty content) ข้ามไปตัวถัดไปอัตโนมัติ:

| Role | ใช้ตอน | ตัวอย่าง chain |
|---|---|---|
| `answer_llm` | สร้างคำตอบ chat | gemini-2.5-flash-lite → gemini-2.5-flash → groq llama-3.3-70b → *(typhoon local via .env)* |
| `fact_extraction` | สกัด fact ตอน ingest | cerebras gpt-oss-120b → groq llama-3.3-70b → sambanova DeepSeek-V3.2 → openrouter |
| `wiki_generation` | เขียนหน้า wiki | *(chain เดียวกับ fact)* |
| `canonical_qa` | สร้าง Q&A pairs | *(chain เดียวกับ fact)* |
| `embed` | ฝัง vector | gemini-embedding-001 *(เดี่ยว — ดูหัวข้อ Embeddings)* |

- เก็บใน 2 ตาราง: **`ai_providers`** (base_url, api_key, protocol) + **`ai_role_assignments`** (role, provider, model, priority)
- cache ในหน่วยความจำ TTL 30s · มี **`.env`/local fallback เสมอ** (เมื่อไม่ตั้ง role หรือทุกเจ้าล้ม)
- จัดการผ่านหน้า **`/providers`** (เพิ่ม/ลบ/test, ลาก priority = ลำดับ failover, dropdown เลือก model)
- API key ถูก **mask ทุก response** (`…xxxx`) — ไม่เคยส่ง full key กลับ frontend / log

### Provider เป็น OpenAI-compatible (รวม Gemini)

ทุก provider คุยผ่าน OpenAI protocol เดียว (`POST {base_url}/chat/completions`) — เพิ่มเจ้าใหม่ได้โดยไม่ต้องเขียน adapter:

| Provider | base_url | หมายเหตุ |
|---|---|---|
| cerebras | `https://api.cerebras.ai/v1` | เร็วสุด (~0.5s) + rate-limit ใจดี |
| groq | `https://api.groq.com/openai/v1` | llama-3.3-70b เร็ว |
| sambanova | `https://api.sambanova.ai/v1` | DeepSeek-V3.2 / Llama |
| nvidia | `https://integrate.api.nvidia.com/v1` | NIM (118 models) |
| openrouter | `https://openrouter.ai/api/v1` | router 344 models (ฟรี 26) |
| **Google AI Studio** | `https://generativelanguage.googleapis.com/v1beta/openai` | **Gemini ผ่าน OpenAI-compat layer** |

> **เทคนิค Gemini:** Google มี OpenAI-compatibility endpoint (`/v1beta/openai`) ที่รับ `messages` แบบ OpenAI ตรงๆ → เสียบเข้า provider router ได้เลย **ไม่ต้องเขียน adapter** สำหรับ format `contents`/`parts` ของ Gemini เนทีฟ (`:generateContent`)

### หน้า `/providers` — เลือก model อัตโนมัติ

- ดึง `/models` ของแต่ละ provider มาทำ dropdown กรองได้ 2 มิติ:
  - **`free_only`** — เฉพาะ model ฟรี (`:free` หรือ pricing 0; เจ้าที่ไม่มี free/paid split ถือว่าฟรีหมด)
  - **`kind`** — `chat` (ตัด embed/tts/whisper/guard/image) หรือ `embed` (เฉพาะ embedding model)
- ปุ่ม **test** ต่อ provider — auto-pick model เร็ว/เสถียร (preference list) หรือเลือกเองจาก dropdown

### 🔢 Embeddings — Gemini migration (แก้ Thai vector collapse)

เดิม `mxbai-embed-large` (1024d) **คืน vector เกือบเหมือนกันหมดสำหรับข้อความไทย** (cosine ≈ 1.0 แม้ข้อความไม่เกี่ยวกัน) → vector search ไทยแทบใช้ไม่ได้ ต้องพึ่ง text search ชดเชย

เปลี่ยนเป็น **`gemini-embedding-001` @ 1024 dims** ผ่าน provider role `embed`:

| Embedding | cos(ไทยเกี่ยวกัน) | cos(ไทยไม่เกี่ยว) | spread |
|---|---|---|---|
| mxbai-embed-large | ~1.0 | ~1.0 | **~0** ❌ |
| **gemini-embedding-001** | 0.93 | 0.49 | **0.45** ✅ |

เทคนิคที่เกี่ยวข้อง:
- **`dimensions` param** — gemini default 3072 มิติ ต้องส่ง `dimensions=EMBEDDING_DIM` (1024) ให้ตรงคอลัมน์ `vector(1024)` ของ DB
- **EmbeddingRouter** — หุ้ม `embed_llm` ที่จุดเดียว → ทุก caller (ingest/retrieval/wiki/qa/re-embed) สลับมา provider role `embed` พร้อมกัน
- **single-provider เท่านั้น** — embed role ตั้งได้เจ้าเดียว (API ตอบ **409** ถ้าเพิ่มตัวที่ 2) เพราะคนละ model = คนละ vector space → fallback ข้าม model จะทำ retrieval พังแบบเงียบๆ
- **retry/backoff** — แทน cross-model failover ด้วยการ retry provider เดิม 3 ครั้ง (exponential 1.5s→3s→6s) เมื่อ 429 ชั่วคราว
- เปลี่ยนขนาด/model → ต้อง **re-embed ทั้งหมด** (`scripts/reembed_all.py --force --sleep 0.7`)

> **กฎเหล็ก:** embedding failover ถูกต้องเฉพาะระหว่าง provider ที่รัน **model เดียวกัน** (vector space เดียวกัน) เท่านั้น — ต่างจาก chat ที่สลับ model ข้ามเจ้าได้

---

## 🧪 RAG Evaluation (Ragas)

`eval/ragas_eval.py` วัดคุณภาพ RAG 5 ตัว: **Faithfulness · Answer Relevancy · Context Precision · Context Recall · Answer Correctness** (รัน production pipeline จริงต่อคำถาม)

### ปัญหา: LLM-judge ติด rate-limit

judge ยิง sub-call เยอะ (context_precision ~8 call/คำถาม → รวม ~150 call/run) → free-tier ของ provider เดี่ยวติด 429 กลางคัน → metric หลายตัวได้ `null`

### แก้: Failover judge (round-robin ข้าม provider)

`--judge-failover` สร้าง custom LangChain chat model ที่ **หมุน judge call ข้าม 5 provider** (nvidia → groq → sambanova → cerebras → openrouter, ทั้งหมดรัน llama-3.3-70b) แบบ round-robin + failover → รวม rate budget ~5 เท่า

| วิธี | ผล full 10 คำถาม |
|---|---|
| judge เดี่ยว (nvidia/sambanova) | 45+ error, 2-3 metric เป็น `null` |
| **failover judge + `--max-workers 1`** | error ~5, **ครบ 5 metric** (coverage 9-10/10) |

```bash
python -m eval.ragas_eval --judge-failover --max-workers 1
```

เทคนิคเสริม: `strictness=1` (กัน `"n">1` ที่ cloud ไม่รองรับ) · `--judge-provider/-model/-key` (เลือก judge เจาะจง) · `reasoning_effort=low` สำหรับ gpt-oss judge กัน timeout

### ผลที่วัดได้ (eval-driven improvements)

ใช้ eval ขับการปรับจริง — score ขยับจากของเดิมมาก (DEVES, 10 คำถาม):

| Config | Faithfulness | Context Recall | Answer Correctness | metric ≥0.8 |
|---|---|---|---|---|
| baseline (mxbai + typhoon) | 0.37 | 0.78 | 0.70 | 0 |
| + Gemini embed + answer | 0.80 | 0.74 | 0.73 | 1 |
| **+ LLM reranker** ⭐ | **0.83** | **0.98** | **0.83** | **3** |

**LLM reranker** (`ENABLE_LLM_RERANK`): retrieve 40 → ส่ง top-20 (snippet) ให้ Gemini จัดอันดับตามความเกี่ยวข้อง → keep top-8
- ใช้ผ่าน `answer_llm` provider chain (failover ในตัว) — จัดไทยได้ดี ต่างจาก FlashRank `ms-marco` ที่เป็น **English** (จัด relevant doc ไทยอยู่ล่างสุด)
- fallback เป็น order เดิมถ้า LLM ล้ม/parse พัง → retrieval ไม่มีวันพังเพราะ rerank
- แลกกับ ~1 LLM call/query (latency +1-2s)

> **บทเรียนจาก eval:** (1) **ลด chunk โดยไม่ rerank → แย่ลงทุกตัว** (ลำดับห่วยตัดมั่ว) · (2) reranker ต้อง **เข้าใจภาษาของ content** — English cross-encoder จัดไทยกลับด้าน · (3) **precision ↔ recall trade-off** เป็นกำแพงจริง: keep มาก = recall สูง/precision ต่ำ, keep น้อย = กลับกัน → "0.8 ทุกตัวพร้อมกัน" ติดเพดานเชิงโครงสร้าง ไม่ใช่แค่จูนไม่พอ

---

## 🤖 Agentic RAG (Phase 5)

ยกระดับจาก linear pipeline → **agent ที่วางแผน + ตรวจสอบ + แก้ตัวเองได้** (opt-in ผ่าน flags, default off):

### Flow แบบ agentic
```
_plan_query  →  simple? ──→ single-pass RAG (เร็ว)
                complex? ─→ _agentic_rag loop:
                              retrieve → generate → _validate_answer (grounded+ครบ?)
                                ├─ พอแล้ว → คืนคำตอบ
                                └─ ยังขาด → _reformulate_query(จาก feedback) → retrieve+generate ใหม่ (≤ AGENTIC_MAX_ITERS)
```

| ส่วนประกอบ | ทำอะไร | Flag |
|---|---|---|
| **Query planner** | LLM จัดประเภท simple/complex → simple ไป single-pass เร็ว, complex ไป agentic loop (กัน latency เปลือง) | `ENABLE_QUERY_PLANNER` |
| **Multi-step retrieval** | retrieve→validate→reformulate→retrieve ซ้ำ จน critic พอใจ | `ENABLE_AGENTIC_ANSWER` |
| **Validation agent** | LLM critic ตัดสิน "คำตอบ grounded + ครบไหม" คืน `{sufficient, missing}` | (มากับ agentic) |
| **Multi-hop GraphRAG** | BFS เดิน wiki_relationships 2-3 hop + ให้คะแนน decay ตามระยะ hop | `GRAPHRAG_MAX_HOPS`, `ENABLE_RELATIONSHIP_SEARCH` |

### หลักการออกแบบ
- **lightweight async loop แทน LangGraph** — fit สถาปัตยกรรม service เดิม, ไม่ลง framework หนัก, ship เร็ว (LangGraph เป็น Phase 6)
- **fail-open** — critic/planner ล่ม/429 → ถือว่าผ่าน ไม่ loop ค้าง · ใช้ `answer_llm` provider chain (failover ในตัว)
- **gate ทุกตัว default off** → production เป็น single-pass จนกว่าจะเปิด → A/B ผ่าน eval ก่อน (เหมือน LLM-rerank)

> ข้อแลก: agentic เพิ่ม 1-3 LLM call/query (latency) — เปิดเฉพาะเมื่อ eval ยืนยันว่าคุ้ม

### Tool-calling agent (Phase 6)

ทางเลือกที่ยืดหยุ่นกว่า fixed loop — `ENABLE_TOOL_CALLING` ให้ LLM **เลือกเครื่องมือเอง**ผ่าน function-calling:

| Tool | ทำอะไร |
|---|---|
| `search_knowledge_base(query)` | ค้น wiki + chunks (ข้อมูลเชิงลึก) |
| `lookup_faq(question)` | ค้น canonical QA (คำตอบสำเร็จรูป) |

LLM อ่านคำถาม → ตัดสินใจเรียก tool ไหน (หรือหลายตัว) → รัน → ตอบจากผล (loop ≤ `TOOL_CALLING_MAX_STEPS`)
- ใช้ `provider_service.chat_tools()` (function-calling + failover ข้าม provider)
- **fail-safe**: provider ไม่รองรับ tools / 429 → fallback single-pass RAG อัตโนมัติ

### LangGraph — streaming agent steps (Phase 6.3)

`ENABLE_LANGGRAPH` เขียน agentic loop เป็น **LangGraph StateGraph** (`agent_graph.py`) — node: retrieve → generate → validate → (conditional) reformulate. คุณค่าหลักคือ **stream ขั้นตอนให้ผู้ใช้เห็น real-time** ผ่าน SSE:

```
🔍 กำลังค้นหาข้อมูล... → ✍️ กำลังเรียบเรียงคำตอบ... → 🔎 กำลังตรวจสอบความถูกต้อง...
   → 🔄 ข้อมูลยังไม่ครบ กำลังค้นเพิ่ม... → 🔍 ... → คำตอบ
```

- ใช้ `graph.astream(stream_mode="updates")` → map node → label → ส่งเป็น `{"status","label"}` event → FloatingChat แสดงในฟองแชต
- **pin `langgraph<0.3`** (เข้ากับ langchain-core 0.3.x — เลี่ยง major bump ที่ทำ langchain-text-splitters พัง)
- fail-safe: graph error → fallback single-pass
- ไม่เพิ่ม**คุณภาพคำตอบ** (logic เดิม) แต่เพิ่ม **UX/observability** — ผู้ใช้เห็น agent "คิด" ทีละขั้น

### Human-in-the-loop & Checkpointing (Phase 7)

| Feature | คือ |
|---|---|
| **Review queue** (`ENABLE_REVIEW_QUEUE`) | wiki/QA ที่ AI สร้าง → `status=pending_review` / `is_active=false` (retrieval **ไม่ serve**) → editor approve/reject ที่ `/review` → publish เมื่ออนุมัติ. กัน KB เผยแพร่ข้อมูลผิดอัตโนมัติ |
| **Claim intake** (`ENABLE_CLAIM_INTAKE`) | flow แจ้งเคลมหลายขั้น: "แจ้งเคลม" → เลขกรมธรรม์ → ข้อมูลรถ → เหตุการณ์ → สรุป+เลขอ้างอิง. **state checkpoint ต่อ session** (`claim_intakes` table; in-memory fallback) → ลูกค้าหลุดกลางคันแล้วกลับมาทำต่อได้ |

> Review queue **retrieval-safe by construction**: pending content อยู่ในตาราง live แต่ query กรอง `status=published` / `is_active=true` ออก → ผู้ใช้ไม่มีวันเห็นจนกว่าจะ approve

---

## ⚡ Retrieval Latency Optimization

Text search ของไทยใช้ **sliding-window substring** (mxbai แยกไทยไม่ได้ ต้องชดเชยด้วย ILIKE) เดิมยิง Supabase ทีละ window:

```
"ที่อยู่สำนักงานใหญ่ของบริษัทเทเวศ..." → ~25 windows × (title + content) × (wiki + chunks)
                                        = 60-80 ILIKE query เรียงต่อกัน
                                        → ~19 วินาที (คอขวดจริงของทั้งระบบ)
```

**แก้: รวม windows เป็น PostgREST `or` filter query เดียวต่อ column**

```python
# เดิม: N queries เรียงกัน
for w in windows:
    supabase.table("document_chunks").ilike("content", f"%{w}%").execute()   # ~0.3s ต่อตัว

# ใหม่: 1 query รวมทุก window
or_filter = ",".join(f"content.ilike.*{w}*" for w in terms)
supabase.table("document_chunks").or_(or_filter).limit(50).execute()        # ~0.3s ตัวเดียว
```

| | เดิม | ใหม่ |
|---|---|---|
| Supabase calls / คำถาม | 60-80 | **3** |
| Retrieval latency | ~19.4s | **~3.5s** (5× เร็วขึ้น) |

- `_cnt` (จำนวน window ที่ match สำหรับ scoring) คำนวณใน Python จาก row ที่ดึงมา (ไม่ต้องยิง DB เพิ่ม)
- `_dedupe_terms()` ตัด term ซ้ำ + sanitize อักขระที่ทำ or-filter พัง (`, . * ( ) :`) + cap 20 term กัน URL ยาวเกิน
- `limit` สูงพอ (chunks 50, wiki 30) เพื่อรักษา recall (or-filter คืน top-N ตาม default order ต้องดึงเผื่อ)

> **บทเรียน:** คอขวด latency ไม่ใช่ LLM แต่เป็น **DB round-trips** — model ทุกขนาด (4B–14B) latency เท่ากันเพราะ retrieval กลบหมด แก้ retrieval ช่วยทุก backend

---

## 🕷️ Multi-Crawler Backends

ระบบรองรับ 3 crawler backends เลือกได้ทั้งแบบ global (`.env`) และ per-request (API):

| Backend | Engine | JS Render | ความเร็ว | คุณภาพ Markdown |
|---|---|---|---|---|
| `trafilatura` | httpx + trafilatura | ❌ | ⚡ เร็วมาก | ดี (เหมาะ static HTML) |
| `playwright` | Headless Chromium | ✅ | 🐢 ช้ากว่า | ดี (render แล้วสกัด) |
| `crawl4ai` | Patchright + LLM-aware | ✅ | 🐢 ช้ากว่า | ⭐ ดีที่สุด (LLM-optimised) |

### ตั้งค่า Global Default

```env
# .env
CRAWLER_BACKEND=trafilatura   # trafilatura | playwright | crawl4ai
```

### Override ต่อ Request (API)

```json
POST /api/sources/url
{
  "url": "https://example.com",
  "crawler_backend": "crawl4ai"
}
```

### ติดตั้ง Playwright และ crawl4ai

```bash
pip install playwright crawl4ai

# Playwright: ติดตั้ง Chromium
playwright install chromium

# crawl4ai: ติดตั้ง patchright Chromium
patchright install chromium
```

---

## 🕸️ GraphRAG — Knowledge Graph

ระบบสกัด **entity relationships** ด้วย LLM จากทุก wiki page และสร้างเป็น knowledge graph:

```
Wiki Page  →  LLM Extract  →  wiki_relationships table
                              (source_entity, target_entity, type, weight)

Relationship Types:
  has_coverage · requires · part_of · related_to · applies_to
  excludes · contacts · located_at · replaces · depends_on
```

ตอน retrieval ระบบจะ **ขยาย context** โดยเดินตาม graph:

```
Vector Search Result  →  find related entities (graph)  →  fetch related wiki pages
                                                            (similarity=0.5, lower priority)
```

เปิดใช้งาน:

```env
ENABLE_RELATIONSHIP_SEARCH=true
```

---

## 🎨 Frontend Pages

| หน้า | URL | การเข้าถึง | ฟีเจอร์ |
|---|---|---|---|
| 🏠 **Landing** | `/` | 🌍 สาธารณะ | หน้าแรกของระบบ · แนะนำ features · Floating Chat Widget |
| 🔐 **Login** | `/login` | 🌍 สาธารณะ | กรอก API Key · Demo key hint · ตรวจสอบกับ `/api/auth/verify` |
| 💬 **Admin Chat** | `/chat` | 🔒 ต้องล็อกอิน | Message history · SSE streaming · source chips · mode badges · Force RAG |
| 📖 **Wiki Viewer** | `/wiki` | 🔒 ต้องล็อกอิน | Browse + search · ดู full content · แก้ไข · ลบ |
| ❓ **QA Editor** | `/qa` | 🔒 ต้องล็อกอิน | List/Create/Edit/Delete QA · toggle active · pagination · search |
| 🔗 **Sources** | `/sources` | 🔒 ต้องล็อกอิน | Add URL · Upload file · Crawler selector (3 backends) · deactivate |
| ⚙️ **Jobs** | `/jobs` | 🔒 ต้องล็อกอิน | Status monitor · auto-refresh · crawl trigger · expand job details |
| 🕸️ **Knowledge Graph** | `/graph` | 🔒 ต้องล็อกอิน | Force-directed graph · zoom/pan · click node → relationships · filter by type |
| 📭 **Missed Q** | `/unanswered` | 🔒 ต้องล็อกอิน | คำถามที่ RAG ตอบไม่ได้ · ทดสอบ 2 โหมด (RAG `force_rag=true` / Floating Chat streaming) · filter · export |
| 📋 **Audit Logs** | `/audit` | 🔒 ต้องล็อกอิน | บันทึกการกระทำทั้งหมด · filter by action / company / status · paginated |
| 🧪 **Eval** | `/eval` | 🔒 ต้องล็อกอิน | ผล Ragas evaluation (5 metrics) · per-question scores |
| 🤖 **Providers** | `/providers` | 🔒 ต้องล็อกอิน | จัดการ AI provider + role failover chain · test · dropdown เลือก model (free/kind filter) · embed badge แสดงมิติ |
| 📊 **Analytics** | `/analytics` | 🔒 ต้องล็อกอิน | ภาพรวมต่อ company — content/unanswered counts · latest RAG eval scores · provider + agentic status · **agent graph viz** · recent activity |
| ✅ **Review Queue** | `/review` | 🔒 ต้องล็อกอิน | **HITL** — อนุมัติ/ปฏิเสธ wiki + QA ที่ AI สร้างก่อนเผยแพร่ (pending ไม่ถูก serve จน approve) |

> **เมนูจัดเป็นหมวด dropdown:** 💬 Chat · 📚 ความรู้ (Wiki/QA/Sources/Graph) · 🔧 ระบบงาน (Jobs/Missed Q/Audit) · 🤖 AI (Providers/Eval) · 🛠️ Settings

### 💬 Floating Chat Widget

Widget ถาม-ตอบแบบ SSE streaming ที่ฝังอยู่บนหน้า Landing (`/`) — **ไม่ต้องล็อกอิน**:
- ปุ่ม chat icon มุมขวาล่าง → เปิด/ปิด dialog
- พิมพ์คำถาม → ส่งไปยัง `/api/public/chat` → แสดงคำตอบแบบ token-by-token
- แสดง sources ที่อ้างอิงหลังได้รับคำตอบ
- คำถามที่ไม่มีข้อมูลถูกบันทึกลง `unanswered_questions` อัตโนมัติ

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| 🐍 Backend | Python 3.11+, FastAPI 0.115, Uvicorn | REST API Server |
| 🌐 Frontend | Next.js 14+, TypeScript, Tailwind CSS | Web UI |
| 🗄️ Database | Supabase Cloud, PostgreSQL | Primary Data Store |
| 🔍 Vector Search | pgvector + IVFFlat index | ANN Similarity Search (1024d cosine) |
| 🔀 AI Routing | DB-backed Provider Router + auto-failover | role → provider chain (429/error → next) |
| 🕸️ Agent Orchestration | LangGraph (StateGraph) | Agentic loop + streaming agent steps to UI |
| 🤖 LLM (Chat/Wiki/QA/Graph) | OpenAI-compat providers: cerebras · groq · sambanova · nvidia · openrouter · **Gemini** · Ollama | Generation (failover chain) |
| 🔢 Embeddings | **Gemini `gemini-embedding-001`** 1024d *(fallback: Ollama `mxbai-embed-large`)* | Vectorization |
| 🕷️ Crawler 1 | Trafilatura + httpx + BeautifulSoup4 | Static HTML extraction (default) |
| 🎭 Crawler 2 | Playwright 1.60 + Chromium | JS-rendered pages |
| 🤖 Crawler 3 | crawl4ai 0.8.6 + Patchright | LLM-aware Markdown extraction |
| ✂️ Chunking | LangChain Text Splitters | Document Splitting |
| 📄 File Parsing | pypdf, python-docx, openpyxl | PDF / DOCX / XLSX |
| ⏰ Jobs | APScheduler 3.11 | Background Scheduling (in-process, daily cron) |
| 🔀 Reranker | **LLM reranker** (Gemini via provider chain — Thai-capable) · FlashRank *(English fallback)* | Relevance reranking of retrieved chunks |
| 🌐 Tunnel | cloudflared | Cloudflare Quick Tunnel (dev/demo) |
| 🐳 Deploy | Docker, Docker Compose | Containerization |
| 🔁 CI/CD | GitHub Actions | Auto test on push (main + master) |

---

## 🗄️ Database Schema

| Table | Description |
|---|---|
| `companies` | 🏢 Multi-tenant company registry |
| `knowledge_sources` | 📌 Source registry (URL / file) |
| `source_pages` | 📄 Raw crawled pages + `content_hash` สำหรับ change detection |
| `document_chunks` | 🧩 Text chunks with 1024d vector embeddings |
| `extracted_facts` | 🧠 Structured facts extracted by LLM |
| `wiki_pages` | 📖 LLM-generated wiki pages with vector embeddings |
| `canonical_qa` | ❓ Curated Q&A pairs with embeddings (CRUD-able) |
| `wiki_relationships` | 🕸️ **Entity relationship graph** — GraphRAG knowledge graph |
| `answer_cache` | 🗃️ Semantic answer cache (avoids redundant LLM calls) |
| `job_runs` | 📊 Background job execution logs |
| `chat_sessions` | 💬 Chat session metadata |
| `chat_messages` | 📝 Individual messages per session |
| `user_feedback` | ⭐ User rating & feedback on answers |
| `unanswered_questions` | 📭 **คำถามที่ RAG ตอบไม่ได้** — บันทึกอัตโนมัติเมื่อไม่มีข้อมูล |
| `audit_logs` | 📋 **Audit trail** — บันทึก action, IP, api_key_tag, company, status, detail (JSONB) |
| `ai_providers` | 🔀 **AI provider registry** — name, base_url, api_key, protocol (OpenAI-compat) |
| `ai_role_assignments` | 🔗 **Role → provider chain** — role, provider_id, model, priority (ลำดับ failover) |

> All vector columns use `ivfflat` index with `vector_cosine_ops` for fast ANN search.

---

## 🚀 Quick Start

### Prerequisites

- 🐍 Python 3.11+
- 🟢 Node.js 20+
- ☁️ [Supabase](https://supabase.com) project (pgvector enabled)
- 🤖 Ollama running locally (`http://localhost:11434`) for embeddings with `mxbai-embed-large`

### 1️⃣ Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/enterprise-llm-wiki.git
cd enterprise-llm-wiki
cp .env.example .env
# แก้ไข .env ตาม Configuration Reference ด้านล่าง
```

### 2️⃣ Setup Database

รัน SQL scripts ตามลำดับใน Supabase SQL Editor:

```
backend/sql/001_extensions.sql           ← Enable pgvector
backend/sql/002_schema.sql               ← สร้าง tables + indexes ทั้งหมด (1024d)
backend/sql/003_rpc.sql                  ← สร้าง RPC functions สำหรับ vector search (1024d)
backend/sql/007_unanswered_questions.sql ← สร้าง unanswered_questions table
backend/sql/009_audit_logs.sql          ← สร้าง audit_logs table
backend/sql/010_ai_providers.sql        ← สร้าง ai_providers + ai_role_assignments (multi-provider failover)
backend/sql/011_claim_intakes.sql       ← (optional) claim intake checkpoint table (Phase 7 — in-memory fallback ถ้าไม่รัน)
```

> หลังรัน `010` แล้ว seed provider + chain ผ่านหน้า `/providers` (หรือ `scripts/seed_providers.py` + env keys) — ระบบจะ fallback ไป `.env`/local เองถ้ายังไม่ตั้ง

> **Upgrading from a previous install?** ถ้าเคยรันกับ `nomic-embed-text` (768d) แล้วเปลี่ยนมาใช้ `mxbai-embed-large` (1024d) ให้รัน migration เพิ่มก่อน:
> ```
> backend/sql/008_update_embedding_dim_1024.sql  ← migration 768d → 1024d
> ```
> จากนั้น re-ingest ข้อมูลทั้งหมดผ่าน `POST /api/jobs/crawl-all`

### 3️⃣ Run Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# ติดตั้ง browser engines สำหรับ Playwright / crawl4ai (optional)
playwright install chromium
patchright install chromium

uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 4️⃣ Run Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5️⃣ Open in Browser

| Service | URL |
|---|---|
| 🌐 Frontend | http://localhost:3000 |
| ⚡ Backend API | http://localhost:8080 |
| 📋 Swagger Docs | http://localhost:8080/docs |

---

## 🌐 Cloudflare Tunnel (Dev / Demo)

สำหรับแชร์ระบบออกสู่ internet แบบชั่วคราวโดยไม่ต้อง deploy:

### Prerequisites

```bash
# ติดตั้ง cloudflared
winget install Cloudflare.cloudflared   # Windows
brew install cloudflared                # macOS
```

### รัน Tunnel

```powershell
# 1. เปิด backend + frontend ตามปกติก่อน
# 2. รัน tunnel script (สร้าง 2 tunnels: backend :8080 + frontend :3000)
.\tunnel.ps1
```

สคริปต์จะ:
1. สร้าง Cloudflare Quick Tunnel สำหรับ backend (port 8080) และ frontend (port 3000)
2. อัปเดต `ALLOW_ORIGINS=*` ใน `backend/.env`
3. Restart backend อัตโนมัติ

### รัน Frontend ในโหมด Tunnel

```bash
cd frontend
npm run dev:tunnel    # = next dev --hostname 0.0.0.0
```

> Next.js server-side rewrite ส่ง `/api/*` ไปยัง backend โดย browser ไม่ได้คุยกับ backend โดยตรง → ไม่มีปัญหา CORS

---

## 🐳 Docker Compose

```bash
cp .env.example .env
# แก้ไข .env
docker compose up --build
```

เปิด 3 containers: `backend` (8080) · `frontend` (3000) · `worker` (job daemon loop ทุก 10s)

> Worker จะ poll `job_runs` ทุก 10 วินาที — ทำงานเป็น daemon ไม่หยุด

---

## ⚙️ Configuration Reference

### Required Settings

```env
# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY   # ต้องเป็น service_role ไม่ใช่ anon

# Ollama Cloud (Chat, Wiki, QA, Fact Extraction)
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEY=YOUR_KEY
OLLAMA_CHAT_MODEL=gpt-oss:20b-cloud

# Chat answer backend (toggle cloud ↔ local — see "Answer Generation Backend")
ANSWER_LLM_USE_LOCAL=false              # false = cloud (เร็ว, default) | true = llm-server
ANSWER_LLM_MODEL=qwen2.5:14b-instruct   # ใช้เมื่อ ANSWER_LLM_USE_LOCAL=true

# Local LLM server (canonical QA matching, query rewrite, optional answer gen)
LOCAL_LLM_BASE_URL=http://llm-server:11434

# Embeddings — fallback เมื่อไม่ได้ตั้ง provider role `embed`
# (production แนะนำตั้ง role embed = Gemini gemini-embedding-001 ผ่านหน้า /providers)
OLLAMA_EMBED_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=mxbai-embed-large
EMBEDDING_DIM=1024        # ต้องตรงกับคอลัมน์ vector(N) ของ DB (ส่งเป็น dimensions ให้ gemini)
```

> **🔢 Embeddings (ปัจจุบัน):** ใช้ **Gemini `gemini-embedding-001` @ 1024d** ผ่าน provider role `embed`
> (แยกแยะไทยได้ดี spread ~0.45) — ดูหัวข้อ *Multi-Provider AI Failover → Embeddings*
> `EMBEDDING_DIM` ต้องตรงกับคอลัมน์ `vector(N)` ของ DB เสมอ · เปลี่ยน model/มิติ → re-embed ทั้งหมด

> **⚠️ ค่า `.env` ด้านบนเป็น fallback** — `mxbai-embed-large` ให้ vector เกือบเหมือนกันสำหรับข้อความไทย
> (vector search ไทยอ่อน ต้องชดเชยด้วย text search + n-gram) จึงย้ายมา Gemini เป็นหลัก
> Cloud Ollama (`https://ollama.com`) ไม่มี embedding model — fallback ต้องใช้ local Ollama

### Authentication Settings

```env
# ตั้ง API_KEY เป็น secret ที่แข็งแรง  — ว่างเปล่า = ปิด auth
API_KEY=changeme-enterprise-wiki-2025
API_KEY_ENABLED=true     # false = ข้ามการตรวจสอบทั้งหมด (dev only)
```

หลังตั้งค่า `API_KEY` ในไฟล์ `.env` ผู้ใช้จะต้องกรอก API Key ที่หน้า Login ก่อนใช้งาน Frontend  
Key จะถูกเก็บใน `sessionStorage` และส่งไปกับทุก request เป็น `Authorization: Bearer <key>`

> หน้า Login มี **Demo Key hint** — แสดงค่า key สำหรับทดสอบพร้อมปุ่มกรอกอัตโนมัติ

### Crawler Settings

```env
# เลือก crawler default: trafilatura | playwright | crawl4ai
CRAWLER_BACKEND=trafilatura
```

### Retrieval Tuning

```env
DEFAULT_COMPANY_CODE=DEVES
RETRIEVAL_TOP_K=40           # จำนวน candidates ก่อน rerank
RERANK_TOP_K=8               # จำนวน context ส่งให้ LLM
CANONICAL_THRESHOLD=0.95     # ความคล้ายขั้นต่ำสำหรับ canonical QA
ANSWER_CACHE_THRESHOLD=0.97  # ความคล้ายขั้นต่ำสำหรับ cache hit
SIMILARITY_THRESHOLD=0.35    # ความคล้ายขั้นต่ำสำหรับ vector search
```

### Scheduler Settings

```env
ENABLE_SCHEDULER=true
DAILY_CRAWL_CRON_HOUR=2      # ชั่วโมงที่รัน daily crawl (0-23)
DAILY_CRAWL_CRON_MINUTE=0    # นาทีที่รัน
```

> APScheduler ทำงานใน process เดียวกับ FastAPI (`lifespan()`) — ไม่ใช่ OS cron หรือ Celery  
> รีสตาร์ท backend = รีสตาร์ท scheduler (cron schedule จะเริ่มนับใหม่)

### 🎛️ Feature Flags

| Flag | Default | Description |
|---|---|---|
| `ENABLE_ANSWER_CACHE` | `false` | 🗃️ Semantic cache — fastest retrieval path |
| `ENABLE_CANONICAL_QA` | `true` | ❓ Pre-generated QA lookup before RAG |
| `ENABLE_WIKI_SEARCH` | `true` | 📖 Include wiki pages in context retrieval |
| `ENABLE_CHUNK_SEARCH` | `true` | 🧩 Include raw document chunks in retrieval |
| `ENABLE_RELATIONSHIP_SEARCH` | `true` | 🕸️ GraphRAG — graph-based context expansion |
| `ENABLE_METADATA_SEARCH` | `true` | 🏷️ Boost score ด้วย title/slug keyword matching |
| `ENABLE_RERANKER` | `false` | 🔀 FlashRank cross-encoder reranking (English — ไม่เหมาะไทย) |
| `ENABLE_LLM_RERANK` | `true` | 🔀 **LLM reranker** (Gemini via provider chain — Thai-capable, ใช้แทน FlashRank) |
| `ENABLE_AGENTIC_ANSWER` | `false` | 🤖 **Agentic loop** (Phase 5) — retrieve→validate→reformulate→retry (`AGENTIC_MAX_ITERS=2`) |
| `ENABLE_QUERY_PLANNER` | `false` | 🤖 **Query planner** (Phase 5) — route simple→single-pass, complex→agentic |
| `GRAPHRAG_MAX_HOPS` | `1` | 🕸️ **Multi-hop GraphRAG** (Phase 5) — BFS depth (2-3 = multi-hop traversal) |
| `ENABLE_TOOL_CALLING` | `false` | 🛠️ **Tool-calling agent** (Phase 6) — LLM เลือก retrieval tool เอง (function-calling) |
| `ENABLE_LANGGRAPH` | `false` | 🕸️ **LangGraph** (Phase 6) — agentic loop เป็น StateGraph + stream ขั้นตอนให้ UI |
| `ENABLE_REVIEW_QUEUE` | `false` | ✅ **HITL review** (Phase 7) — wiki/QA ที่ AI สร้าง → pending รอ editor อนุมัติที่ `/review` ก่อน publish |
| `ENABLE_CLAIM_INTAKE` | `false` | 📋 **Claim intake** (Phase 7) — flow แจ้งเคลมหลายขั้น resumable (checkpoint per session) |
| `ENABLE_QUERY_REWRITE` | `true` | ✏️ LLM-based query rewriting |
| `ENABLE_GROUNDING` | `true` | 📌 Source-grounded answer generation |
| `ENABLE_SCHEDULER` | `true` | ⏰ APScheduler daily crawl |

---

## 📋 API Endpoints

### 💬 Chat

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/chat` | 🔒 | ถามคำถาม — 4-layer RAG + GraphRAG (JSON response) |
| `GET` | `/api/chat/stream` | 🔒 | ถามคำถาม — SSE streaming response |
| `POST` | `/api/public/chat` | 🌍 | Public chat สำหรับ Floating Widget (SSE streaming) |

### 📭 Unanswered Questions

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/unanswered` | 🔒 | List คำถามที่ RAG ตอบไม่ได้ |
| `PATCH` | `/api/unanswered/{id}` | 🔒 | Mark as resolved / add note |
| `DELETE` | `/api/unanswered/{id}` | 🔒 | Delete record |

### 📋 Audit Logs

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/audit/logs` | 🔒 | Paginated audit log (filter: `company_code`, `action`, `status`) |
| `GET` | `/api/audit/actions` | 🔒 | List known action names สำหรับ filter dropdown |

### 🤖 AI Providers

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/providers` | 🔒 | List providers (key masked) + roles |
| `POST` · `PUT` · `DELETE` | `/api/providers[/{id}]` | 🔒 | CRUD provider |
| `POST` | `/api/providers/{id}/test` | 🔒 | Test chat — auto-pick model หรือระบุ `?model=` |
| `GET` | `/api/providers/{id}/models` | 🔒 | List models (`?free_only=`, `?kind=chat\|embed\|all`) |
| `GET` | `/api/providers/roles` | 🔒 | List role assignments + `embedding_dim` |
| `POST` · `PUT` · `DELETE` | `/api/providers/roles[/{id}]` | 🔒 | จัดการ failover chain (embed = single, ตอบ 409 ถ้าเกิน 1) |

### 🔗 Sources

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sources` | List knowledge sources |
| `POST` | `/api/sources/url` | Ingest URL (+ `crawler_backend` override) |
| `POST` | `/api/sources/file` | Upload file (PDF/DOCX/XLSX/TXT/MD) |
| `GET` | `/api/sources/backends` | List crawler backends + current default |
| `GET` | `/api/sources/{id}/pages` | List pages of a source |
| `DELETE` | `/api/sources/{id}` | Deactivate source |

### 📖 Wiki

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/wiki/pages` | List wiki pages (filter: `q`, `status`) |
| `GET` | `/api/wiki/pages/{id}` | Get wiki page detail |
| `PUT` | `/api/wiki/pages/{id}` | Update wiki page |
| `DELETE` | `/api/wiki/pages/{id}` | Delete wiki page |

### ❓ Canonical QA

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/wiki/qa` | List QA (filter: `q`, `wiki_page_id`) |
| `POST` | `/api/wiki/qa` | Create QA (auto-embed) |
| `PUT` | `/api/wiki/qa/{id}` | Edit QA (re-embed question) |
| `DELETE` | `/api/wiki/qa/{id}` | Delete QA |

### 🕸️ Relationships

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/wiki/relationships` | List entity relationships (filter: `entity`, `rel_type`) |
| `DELETE` | `/api/wiki/relationships/{id}` | Delete relationship |

### ⚙️ Jobs

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/jobs` | List jobs (filter: `status`, `company_code`) |
| `GET` | `/api/jobs/{id}` | Get job detail |
| `POST` | `/api/jobs/run-pending` | Run pending jobs now |
| `POST` | `/api/jobs/crawl-all` | Trigger manual crawl all sources |
| `DELETE` | `/api/jobs/{id}` | Delete job log |

### 🏢 Companies

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/companies` | List companies |
| `POST` | `/api/companies` | Create / upsert company |
| `DELETE` | `/api/companies/{code}` | Deactivate company |

### 🔐 Auth

| Method | Path | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/auth/verify` | ❌ | ตรวจสอบ API key — login endpoint |

> Public paths (no token needed): `/api/public/*`, `/api/health`, `/api/auth/verify`, `/docs`, `/redoc`, `/openapi.json`  
> ดู interactive docs ทั้งหมดได้ที่ `http://localhost:8080/docs`

---

## 📁 Project Structure

```
enterprise-llm-wiki/
│
├── 🐍 backend/
│   ├── app/
│   │   ├── api/               # FastAPI route handlers
│   │   │   ├── chat.py        # Admin chat (auth required)
│   │   │   ├── public_chat.py # Public chat SSE (no auth)
│   │   │   ├── sources.py     # URL + file upload
│   │   │   ├── wiki.py        # wiki pages + QA + relationships
│   │   │   ├── jobs.py        # job monitor + crawl trigger
│   │   │   ├── unanswered.py  # unanswered questions CRUD
│   │   │   ├── companies.py   # multi-tenant management
│   │   │   ├── auth.py        # POST /api/auth/verify
│   │   │   └── health.py
│   │   ├── core/              # Config, logging, auth middleware
│   │   ├── db/                # Supabase client
│   │   ├── jobs/              # APScheduler + job runner daemon
│   │   ├── pipeline/          # Ingest pipeline (URL + file)
│   │   ├── schemas/           # Pydantic models
│   │   └── services/
│   │       ├── crawlers/      # Multi-crawler backends
│   │       │   ├── base.py
│   │       │   ├── trafilatura_crawler.py
│   │       │   ├── playwright_crawler.py
│   │       │   ├── crawl4ai_crawler.py
│   │       │   └── factory.py
│   │       ├── crawler_service.py       # façade
│   │       ├── retrieval_service.py     # 4-layer + GraphRAG
│   │       ├── relationship_service.py  # entity graph
│   │       ├── wiki_service.py
│   │       ├── qa_service.py
│   │       ├── chat_service.py          # answer() + answer_stream() + unanswered tracking
│   │       ├── provider_service.py      # 🔀 DB-backed multi-provider failover (chat + embed)
│   │       ├── ollama_client.py         # Ollama client + EmbeddingRouter (provider-first)
│   │       ├── extraction_service.py
│   │       ├── chunking_service.py
│   │       ├── file_loader_service.py
│   │       └── job_service.py
│   │   # api/providers.py — provider/role CRUD + /models + /test
│   ├── eval/                # 🧪 Ragas evaluation (ragas_eval.py + failover judge)
│   ├── scripts/             # reembed_all.py · seed_providers.py · ...
│   ├── sql/
│   │   ├── 001_extensions.sql
│   │   ├── 002_schema.sql
│   │   ├── 003_rpc.sql
│   │   ├── 007_unanswered_questions.sql
│   │   └── 010_ai_providers.sql        # 🔀 ai_providers + ai_role_assignments
│   ├── requirements.txt
│   └── Dockerfile
│
├── 🌐 frontend/
│   ├── app/
│   │   ├── page.tsx           # 🏠 Landing (public — hero, features, FloatingChat)
│   │   ├── landing/page.tsx   # ↩️ Redirect → / (backward compat)
│   │   ├── chat/page.tsx      # 💬 Admin Chat (SSE streaming, source chips)
│   │   ├── wiki/page.tsx      # 📖 Wiki Viewer (search, edit, delete)
│   │   ├── qa/page.tsx        # ❓ QA Editor (CRUD + pagination)
│   │   ├── sources/page.tsx   # 🔗 Sources (crawler selector)
│   │   ├── jobs/page.tsx      # ⚙️ Job Monitor (auto-refresh)
│   │   ├── graph/page.tsx     # 🕸️ Knowledge Graph (force-directed)
│   │   ├── unanswered/page.tsx # 📭 Missed Q (unanswered questions + dual RAG / Floating Chat test)
│   │   ├── login/page.tsx     # 🔐 Login (API key form + demo key hint)
│   │   └── layout.tsx         # Nav bar + AuthGuard + ThemeProvider
│   ├── components/
│   │   └── FloatingChat.tsx   # 💬 Floating chat widget (SSE streaming)
│   ├── lib/
│   │   └── api.ts             # apiFetch() — Bearer token injector
│   ├── public/
│   │   └── favicon.svg        # 🧠 Neural network icon
│   ├── package.json           # dev:tunnel script included
│   └── Dockerfile
│
├── 📚 docs/
│   ├── ARCHITECTURE.md
│   ├── TECHNOLOGY_STACK.md
│   ├── ROADMAP.md
│   ├── COMPLETE_PROJECT_INSTRUCTION.md
│   └── API_EXAMPLES.http
│
├── tunnel.ps1                 # 🌐 Cloudflare Quick Tunnel script (Windows)
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## 🗺️ Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 — MVP | ✅ Done | URL ingest, chunking, embedding, vector search, chat API |
| Phase 2 — LLM Wiki | ✅ Done | Fact extraction, wiki generation, canonical QA |
| Phase 3 — Enterprise Jobs | ✅ Done | Multi-crawler, APScheduler, change detection, file upload, job monitor UI |
| Phase 3.5 — GraphRAG | ✅ Done | Entity relationship extraction, graph expansion in retrieval, QA CRUD, full frontend |
| Phase 3.8 — Public Demo | ✅ Done | Landing page, Floating Chat widget (SSE), unanswered question tracking, Cloudflare tunnel |
| Phase 4 — Production | ✅ Done | ~~Authentication~~ · ~~Docker hardening~~ · ~~Input validation~~ · ~~Structured logging~~ · ~~RLS per company~~ · ~~Rate limiting~~ · ~~Crawler retry~~ · ~~Job retry~~ · ~~Audit logs~~ · ~~RAG Evaluation (Ragas + failover judge)~~ · ~~Embedding upgrade (Gemini gemini-embedding-001 @1024)~~ · ~~LLM reranker (Thai-capable, via provider chain)~~ |
| Phase 4.5 — Multi-Provider AI | ✅ Done | ~~DB-backed provider router + auto-failover chain~~ · ~~Provider UI (test/model dropdown)~~ · ~~Gemini via OpenAI-compat~~ · ~~Gemini embeddings @1024 (fix Thai vector collapse)~~ · ~~Ragas failover judge~~ |
| Phase 5 — Agentic RAG | ✅ Done | ~~Query planner (simple↔complex routing)~~ · ~~Multi-step retrieval (retrieve→validate→reformulate loop)~~ · ~~Validation agent (LLM critic)~~ · ~~Multi-hop GraphRAG traversal (BFS)~~ — *opt-in via flags; lightweight async loop แทน LangGraph* |
| Phase 6 — Advanced | ✅ Done | ~~Analytics dashboard (per-company stats · eval scores · provider/agentic status)~~ · ~~Tool-calling agent (function-calling)~~ · ~~LangGraph agentic graph + **streaming agent steps** to the chat UI~~ |
| Phase 7 — Observability & Control | ✅ Done | ~~Agent graph visualization~~ · ~~HITL review queue (approve AI wiki/QA before publish)~~ · ~~Checkpoint-resumable multi-step claim intake~~ |

---

## 🔐 Security & Production Checklist

> ⚠️ **สิ่งที่ต้องทำก่อน deploy ไป production**

### Security

- ❌ ห้าม commit ไฟล์ `.env` — `.gitignore` ป้องกันไว้แล้ว
- 🔑 `SUPABASE_SERVICE_ROLE_KEY` ใช้ได้เฉพาะ **backend/worker** — ห้ามส่งไป frontend หรือ browser
- 🔐 สร้าง `API_KEY` ที่แข็งแรงก่อน deploy:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- 🌐 กำหนด `ALLOW_ORIGINS` ให้เฉพาะ frontend domain จริง (ห้ามใช้ `*` ใน production)
- 🛡️ เปิด Supabase Row Level Security (RLS) ต่อ company สำหรับ multi-tenant isolation
- 🍪 API Key เก็บใน `sessionStorage` — ปิด browser tab = logout อัตโนมัติ

### Production Configuration

```env
APP_ENV=production      # เปลี่ยน development → production (JSON logs + strict checks)
DEBUG=false             # ซ่อน stack trace จาก error responses
ALLOW_ORIGINS=https://wiki.mycompany.com
LOG_LEVEL=WARNING       # ลด log volume
```

### Production Hardening (ทำแล้ว ✅)

| รายการ | สถานะ |
|---|---|
| Docker containers run as non-root user | ✅ |
| `curl` installed in backend image for healthcheck | ✅ |
| `--reload` ถูกลบออกจาก production command | ✅ |
| Next.js standalone output (minimal image) | ✅ |
| File upload size limit: 50 MB | ✅ |
| Chat question max length: 2,000 chars | ✅ |
| Global exception handler (no stack trace leak) | ✅ |
| Deep health check tests Supabase connectivity | ✅ |
| JSON structured logging when `APP_ENV=production` | ✅ |
| Startup warnings for weak API key / open CORS | ✅ |

---

## 📚 Documents

| ไฟล์ | คำอธิบาย |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 🏗️ Architecture, module map, ingest/chat flow, service dependencies |
| [TECHNOLOGY_STACK.md](docs/TECHNOLOGY_STACK.md) | 🛠️ Library ทุกตัวพร้อม version และ role |
| [ROADMAP.md](docs/ROADMAP.md) | 🗺️ แผนพัฒนา 5 phases พร้อม status |
| [COMPLETE_PROJECT_INSTRUCTION.md](docs/COMPLETE_PROJECT_INSTRUCTION.md) | 🤖 Task brief, requirements, backlog, coding style |
| [API_EXAMPLES.http](docs/API_EXAMPLES.http) | 📋 ตัวอย่าง HTTP requests สำหรับทดสอบทุก endpoint |

---

## 📄 License

MIT © 2024–2025

---

<div align="center">

Built with ❤️ using FastAPI · Next.js · Supabase · Ollama · crawl4ai · Playwright

</div>
