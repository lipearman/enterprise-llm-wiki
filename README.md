<div align="center">

# 🏢 Enterprise LLM Wiki

**ระบบจัดการความรู้องค์กรแบบ RAG ครบวงจร — v0.2.0**

Chatbot · LLM Wiki · Knowledge Graph · Multi-Crawler · Multi-company

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14+-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Cloud-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-768d-336791?style=flat-square&logo=postgresql&logoColor=white)
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

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    🌐 Frontend (Next.js 14+)                       │
│  💬 Chat │ 📖 Wiki Viewer │ ❓ QA Editor │ 🔗 Sources │ ⚙️ Jobs  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ REST API
┌───────────────────────────▼──────────────────────────────────────┐
│                    ⚡ Backend (FastAPI v0.2.0)                     │
│  /chat │ /sources │ /wiki │ /wiki/qa │ /jobs │ /companies        │
└──────┬──────────────────┬───────────────────┬────────────────────┘
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
┌──────▼──────────────────▼──────────────────────────────────────┐
│              🗄️ Supabase (PostgreSQL + pgvector)                 │
│  wiki_pages · canonical_qa · document_chunks · wiki_relationships│
│  knowledge_sources · source_pages · answer_cache · job_runs     │
└──────────────────────────┬─────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│                         🤖 Ollama                                │
│  ☁️ Cloud → Chat / Wiki / QA / Fact / Relationship Extraction   │
│  💻 Local → Embeddings (nomic-embed-text · 768d)                │
└────────────────────────────────────────────────────────────────┘
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
  ├─ 🔢  Embed               (Ollama Local · nomic-embed-text · 768d)
  ├─ 💾  Save document_chunks + source_pages           ✅ searchable
  │
  ├─ 🧠  Extract Facts        (LLM)
  ├─ 📖  Generate Wiki Page   (LLM)
  ├─ ❓  Generate Canonical QA (LLM)
  ├─ 🕸️  Extract Relationships (LLM → entity graph)
  ├─ 🔢  Embed Wiki & QA
  └─ 💾  Save wiki_pages + canonical_qa + wiki_relationships  ✅ enriched
```

### 💬 Chat Flow (with GraphRAG)

```
Question
  │
  ├─ [1] 🗃️  Answer Cache Search     threshold: 0.96  → ✅ return cached
  ├─ [2] ❓  Canonical QA Search      threshold: 0.90  → ✅ return QA answer
  ├─ [3] 📖  Wiki Page Vector Search  top_k: 20
  │          Document Chunk Search    top_k: 20
  ├─ [4] 🕸️  Graph Expansion (GraphRAG)
  │          └─ wiki_relationships → find related entities → fetch related wiki pages
  ├─      🏷️  Metadata Boost         title/slug keyword scoring
  ├─      📊  Merge & Sort by similarity → Top 5
  ├─      🤖  LLM → Grounded Answer
  └─      💾  Save to answer_cache
```

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

| หน้า | URL | ฟีเจอร์ |
|---|---|---|
| 💬 **Chat** | `/` | Message history · typing indicator · source chips · mode badges · Force RAG |
| 📖 **Wiki Viewer** | `/wiki` | Browse + search · ดู full content · แก้ไข · ลบ |
| ❓ **QA Editor** | `/qa` | List/Create/Edit/Delete QA · toggle active · pagination · search |
| 🔗 **Sources** | `/sources` | Add URL · Upload file · Crawler selector (3 backends) · deactivate |
| ⚙️ **Jobs** | `/jobs` | Status monitor · auto-refresh · crawl trigger · expand job details |

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| 🐍 Backend | Python 3.11+, FastAPI 0.115, Uvicorn | REST API Server |
| 🌐 Frontend | Next.js 14+, TypeScript, Tailwind CSS | Web UI (5 pages) |
| 🗄️ Database | Supabase Cloud, PostgreSQL | Primary Data Store |
| 🔍 Vector Search | pgvector + IVFFlat index | ANN Similarity Search (768d cosine) |
| 🤖 LLM (Chat/Wiki/QA/Graph) | Ollama Cloud `gpt-oss:20b-cloud` | Generation |
| 🔢 Embeddings | Ollama Local `nomic-embed-text` 768d | Vectorization |
| 🕷️ Crawler 1 | Trafilatura + httpx + BeautifulSoup4 | Static HTML extraction (default) |
| 🎭 Crawler 2 | Playwright 1.60 + Chromium | JS-rendered pages |
| 🤖 Crawler 3 | crawl4ai 0.8.6 + Patchright | LLM-aware Markdown extraction |
| ✂️ Chunking | LangChain Text Splitters | Document Splitting |
| 📄 File Parsing | pypdf, python-docx, openpyxl | PDF / DOCX / XLSX |
| ⏰ Jobs | APScheduler 3.11 | Background Scheduling (daily cron) |
| 🔀 Reranker | FlashRank *(optional)* | Cross-encoder Reranking |
| 🐳 Deploy | Docker, Docker Compose | Containerization |
| 🔁 CI/CD | GitHub Actions | Auto test on push (main + master) |

---

## 🗄️ Database Schema

| Table | Description |
|---|---|
| `companies` | 🏢 Multi-tenant company registry |
| `knowledge_sources` | 📌 Source registry (URL / file) |
| `source_pages` | 📄 Raw crawled pages + `content_hash` สำหรับ change detection |
| `document_chunks` | 🧩 Text chunks with 768d vector embeddings |
| `extracted_facts` | 🧠 Structured facts extracted by LLM |
| `wiki_pages` | 📖 LLM-generated wiki pages with vector embeddings |
| `canonical_qa` | ❓ Curated Q&A pairs with embeddings (CRUD-able) |
| `wiki_relationships` | 🕸️ **Entity relationship graph** — GraphRAG knowledge graph |
| `answer_cache` | 🗃️ Semantic answer cache (avoids redundant LLM calls) |
| `job_runs` | 📊 Background job execution logs |
| `chat_sessions` | 💬 Chat session metadata |
| `chat_messages` | 📝 Individual messages per session |
| `user_feedback` | ⭐ User rating & feedback on answers |

> All vector columns use `ivfflat` index with `vector_cosine_ops` for fast ANN search.

---

## 🚀 Quick Start

### Prerequisites

- 🐍 Python 3.11+
- 🟢 Node.js 20+
- ☁️ [Supabase](https://supabase.com) project (pgvector enabled)
- 🤖 Ollama running locally for embeddings

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
backend/sql/001_extensions.sql   ← Enable pgvector
backend/sql/002_schema.sql       ← สร้าง tables + indexes ทั้งหมด
backend/sql/003_rpc.sql          ← สร้าง RPC functions สำหรับ vector search
```

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

# Ollama Local (Embeddings)
OLLAMA_EMBED_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
EMBEDDING_DIM=768
```

### Crawler Settings

```env
# เลือก crawler default: trafilatura | playwright | crawl4ai
CRAWLER_BACKEND=trafilatura
```

### Retrieval Tuning

```env
DEFAULT_COMPANY_CODE=DEVES
RETRIEVAL_TOP_K=20           # จำนวน candidates ก่อน rerank
RERANK_TOP_K=5               # จำนวน context ส่งให้ LLM
CANONICAL_THRESHOLD=0.90     # ความคล้ายขั้นต่ำสำหรับ canonical QA
ANSWER_CACHE_THRESHOLD=0.96  # ความคล้ายขั้นต่ำสำหรับ cache hit
SIMILARITY_THRESHOLD=0.35    # ความคล้ายขั้นต่ำสำหรับ vector search
```

### Scheduler Settings

```env
ENABLE_SCHEDULER=true
DAILY_CRAWL_CRON_HOUR=2      # ชั่วโมงที่รัน daily crawl (0-23)
DAILY_CRAWL_CRON_MINUTE=0    # นาทีที่รัน
```

### 🎛️ Feature Flags

| Flag | Default | Description |
|---|---|---|
| `ENABLE_ANSWER_CACHE` | `true` | 🗃️ Semantic cache — fastest retrieval path |
| `ENABLE_CANONICAL_QA` | `true` | ❓ Pre-generated QA lookup before RAG |
| `ENABLE_WIKI_SEARCH` | `true` | 📖 Include wiki pages in context retrieval |
| `ENABLE_CHUNK_SEARCH` | `true` | 🧩 Include raw document chunks in retrieval |
| `ENABLE_RELATIONSHIP_SEARCH` | `true` | 🕸️ GraphRAG — graph-based context expansion |
| `ENABLE_METADATA_SEARCH` | `true` | 🏷️ Boost score ด้วย title/slug keyword matching |
| `ENABLE_RERANKER` | `false` | 🔀 FlashRank cross-encoder reranking |
| `ENABLE_QUERY_REWRITE` | `false` | ✏️ LLM-based query rewriting |
| `ENABLE_GROUNDING` | `true` | 📌 Source-grounded answer generation |
| `ENABLE_SCHEDULER` | `true` | ⏰ APScheduler daily crawl |

---

## 📋 API Endpoints

### 💬 Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | ถามคำถาม — 4-layer RAG + GraphRAG |

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

> ดู interactive docs ทั้งหมดได้ที่ `http://localhost:8080/docs`

---

## 📁 Project Structure

```
enterprise-llm-wiki/
│
├── 🐍 backend/
│   ├── app/
│   │   ├── api/               # FastAPI route handlers
│   │   │   ├── chat.py
│   │   │   ├── sources.py     # URL + file upload
│   │   │   ├── wiki.py        # wiki pages + QA + relationships
│   │   │   ├── jobs.py        # job monitor + crawl trigger
│   │   │   ├── companies.py   # multi-tenant management
│   │   │   └── health.py
│   │   ├── core/              # Config, logging, text utilities
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
│   │       ├── crawler_service.py    # façade
│   │       ├── retrieval_service.py  # 4-layer + GraphRAG
│   │       ├── relationship_service.py  # entity graph
│   │       ├── wiki_service.py
│   │       ├── qa_service.py
│   │       ├── chat_service.py
│   │       ├── extraction_service.py
│   │       ├── chunking_service.py
│   │       ├── file_loader_service.py
│   │       └── job_service.py
│   ├── scripts/
│   ├── sql/
│   ├── requirements.txt
│   └── Dockerfile
│
├── 🌐 frontend/
│   ├── app/
│   │   ├── page.tsx           # 💬 Chat (message history, source chips)
│   │   ├── wiki/page.tsx      # 📖 Wiki Viewer (search, edit, delete)
│   │   ├── qa/page.tsx        # ❓ QA Editor (CRUD + pagination)
│   │   ├── sources/page.tsx   # 🔗 Sources (crawler selector)
│   │   ├── jobs/page.tsx      # ⚙️ Job Monitor (auto-refresh)
│   │   └── layout.tsx         # Nav bar (responsive)
│   ├── package.json
│   └── Dockerfile
│
├── 📚 docs/
│   ├── ARCHITECTURE.md
│   ├── TECHNOLOGY_STACK.md
│   ├── ROADMAP.md
│   ├── COMPLETE_PROJECT_INSTRUCTION.md
│   └── API_EXAMPLES.http
│
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
| Phase 4 — Production | 📋 Planned | Authentication, RLS per company, audit logs, evaluation (Ragas/DeepEval), human review |
| Phase 5 — Agentic | 📋 Planned | LangGraph planner, multi-step retrieval, validation agent, full GraphRAG traversal |

---

## 🔐 Security Notes

> ⚠️ **สิ่งที่ต้องระวังก่อน deploy**

- ❌ ห้าม commit ไฟล์ `.env` — `.gitignore` ป้องกันไว้แล้ว
- 🔑 `SUPABASE_SERVICE_ROLE_KEY` ใช้ได้เฉพาะ **backend/worker** — ห้ามส่งไป frontend หรือ browser
- 🌐 Production ควรกำหนด `ALLOW_ORIGINS` ให้เฉพาะ frontend domain จริง
- 🛡️ เปิด Supabase Row Level Security (RLS) ต่อ company สำหรับ multi-tenant isolation

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
