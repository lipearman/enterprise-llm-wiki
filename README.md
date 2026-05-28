<div align="center">

# 🏢 Enterprise LLM Wiki

**ระบบจัดการความรู้องค์กรแบบ RAG ครบวงจร**

Chatbot · LLM Wiki · Knowledge Ingestion Pipeline · Multi-company

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14+-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Cloud-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-768d-336791?style=flat-square&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

</div>

---

## 📌 Overview

Enterprise LLM Wiki เป็น **full-stack knowledge management platform** สำหรับองค์กร โดยรวมระบบหลัก 3 ส่วนเข้าด้วยกัน:

| ระบบ | คำอธิบาย |
|---|---|
| 🤖 **RAG Chatbot** | ถาม-ตอบด้วย 4 ชั้นการค้นหา: Answer Cache → Canonical QA → Wiki → Chunk Search |
| 📚 **LLM Wiki Generator** | นำ URL/ไฟล์เข้าระบบ → LLM สกัด Facts → สร้าง Wiki Page → สร้าง QA อัตโนมัติ |
| ⚙️ **Knowledge Pipeline** | Background jobs สำหรับ Daily Crawl, Deep Enrichment, Embedding Rebuild |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    🌐 Frontend (Next.js)                      │
│         💬 Chat  │  ➕ Add URL  │  📖 Wiki  │  📊 Jobs        │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                   ⚡ Backend (FastAPI)                        │
│   /api/chat  │  /api/sources  │  /api/wiki  │  /api/jobs     │
└──────┬───────────────────┬───────────────────┬──────────────┘
       │                   │                   │
┌──────▼──────┐   ┌────────▼────────┐   ┌──────▼────────────┐
│  🔍 Retrieval│   │  📥 Ingest      │   │  🔄 Worker/Jobs   │
│  Service    │   │  Pipeline       │   │  (APScheduler)    │
│             │   │                 │   │                   │
│ AnswerCache │   │ Crawl & Extract │   │ Fast Ingest       │
│ CanonicalQA │   │ Chunk & Embed   │   │ Deep Enrichment   │
│ WikiSearch  │   │ Wiki Generate   │   │ Daily Crawl       │
│ ChunkSearch │   │ QA Generate     │   │ Embed Rebuild     │
└──────┬──────┘   └────────┬────────┘   └───────────────────┘
       │                   │
┌──────▼───────────────────▼──────────────────────────────────┐
│           🗄️ Supabase (PostgreSQL + pgvector)                │
│  sources │ pages │ chunks │ wiki │ canonical_qa │ cache      │
│  chat_sessions │ job_runs │ facts │ feedback                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     🤖 Ollama                                 │
│   ☁️ Cloud  →  Chat / Wiki / QA / Fact Extraction            │
│   💻 Local  →  Embeddings (nomic-embed-text · 768d)          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Core Flows

### 📥 Ingest Flow

```
URL / File
  │
  ├─ 🕷️  Crawl & Extract     (Trafilatura / BeautifulSoup)
  ├─ 🧹  Clean → Markdown
  ├─ ✂️  Chunk               (LangChain Text Splitter)
  ├─ 🔢  Embed               (Ollama Local · nomic-embed-text · 768d)
  ├─ 💾  Save document_chunks              ✅ status: searchable
  │
  ├─ 🧠  Extract Facts       (LLM)
  ├─ 📖  Generate Wiki Page  (LLM)
  ├─ ❓  Generate Canonical QA (LLM)
  ├─ 🔢  Embed Wiki & QA
  └─ 💾  Save wiki_pages + canonical_qa    ✅ status: enriched
```

### 💬 Chat Flow

```
Question
  │
  ├─ [1] 🗃️  Answer Cache Search     threshold: 0.96  → ✅ return cached
  ├─ [2] ❓  Canonical QA Search      threshold: 0.90  → ✅ return QA answer
  ├─ [3] 📖  Wiki Page Vector Search  top_k: 20
  │          Document Chunk Search   top_k: 20
  ├─      📊  Merge & Sort by similarity → Top 5
  ├─ [4] 🔀  Reranker (FlashRank)    optional
  ├─      🤖  LLM → Grounded Answer
  └─      💾  Save to answer_cache + chat_messages
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| 🐍 Backend | Python 3.11+, FastAPI, Uvicorn | REST API Server |
| 🌐 Frontend | Next.js 14+, TypeScript, Tailwind CSS | Web UI |
| 🗄️ Database | Supabase Cloud, PostgreSQL | Primary Data Store |
| 🔍 Vector Search | pgvector + IVFFlat index | ANN Similarity Search |
| 🤖 LLM (Chat/Wiki/QA) | Ollama Cloud `gpt-oss:20b-cloud` | Generation |
| 🔢 Embeddings | Ollama Local `nomic-embed-text` 768d | Vectorization |
| 🕷️ Crawling | Trafilatura, BeautifulSoup4, Markdownify | Web Extraction |
| ✂️ Chunking | LangChain Text Splitters | Document Splitting |
| 📄 File Parsing | pypdf, python-docx, openpyxl | PDF/DOCX/XLSX |
| ⏰ Jobs | APScheduler | Background Scheduling |
| 🔀 Reranker | FlashRank *(optional)* | Cross-encoder Rerank |
| 🐳 Deploy | Docker, Docker Compose | Containerization |
| 🔁 CI/CD | GitHub Actions | Automated Testing |

---

## 🗄️ Database Schema

| Table | Description |
|---|---|
| `companies` | 🏢 Multi-tenant company registry |
| `knowledge_sources` | 📌 Source registry (URL / file / wiki) |
| `source_pages` | 📄 Raw crawled pages + content hash for change detection |
| `document_chunks` | 🧩 Text chunks with 768d vector embeddings |
| `extracted_facts` | 🧠 Structured facts extracted by LLM |
| `wiki_pages` | 📖 LLM-generated wiki pages with vector embeddings |
| `canonical_qa` | ❓ Curated Q&A pairs derived from wiki pages |
| `answer_cache` | 🗃️ Semantic answer cache (avoids redundant LLM calls) |
| `wiki_relationships` | 🕸️ Entity relationship graph between wiki topics |
| `chat_sessions` | 💬 Chat session metadata |
| `chat_messages` | 📝 Individual messages per session |
| `job_runs` | 📊 Background job execution logs |
| `user_feedback` | ⭐ User rating & feedback on answers |

> All vector columns use `ivfflat` index with `vector_cosine_ops` for fast ANN search.

---

## 🚀 Quick Start

### Prerequisites

- 🐍 Python 3.11+
- 🟢 Node.js 20+
- ☁️ [Supabase](https://supabase.com) project (pgvector enabled)
- 🤖 [Ollama](https://ollama.com) running locally (for embeddings)

### 1️⃣ Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/enterprise-llm-wiki.git
cd enterprise-llm-wiki
cp .env.example .env
# แก้ไข .env ด้วย Supabase URL, service role key และ Ollama settings
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

เปิด 3 containers: `backend` (8080) · `frontend` (3000) · `worker` (job runner)

---

## ⚙️ Configuration Reference

### Required Settings

```env
# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_KEY

# Ollama Cloud (Chat, Wiki, QA, Fact Extraction)
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEY=YOUR_KEY
OLLAMA_CHAT_MODEL=gpt-oss:20b-cloud

# Ollama Local (Embeddings)
OLLAMA_EMBED_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
EMBEDDING_DIM=768
```

### Retrieval Tuning

```env
DEFAULT_COMPANY_CODE=LOCKTON
RETRIEVAL_TOP_K=20          # จำนวน candidates ก่อน rerank
RERANK_TOP_K=5              # จำนวน context ส่งให้ LLM
CANONICAL_THRESHOLD=0.90    # ความคล้ายขั้นต่ำสำหรับ canonical QA
ANSWER_CACHE_THRESHOLD=0.96 # ความคล้ายขั้นต่ำสำหรับ cache hit
SIMILARITY_THRESHOLD=0.35   # ความคล้ายขั้นต่ำสำหรับ vector search
```

### 🎛️ Feature Flags

| Flag | Default | Description |
|---|---|---|
| `ENABLE_ANSWER_CACHE` | `true` | 🗃️ Semantic cache (fastest path) |
| `ENABLE_CANONICAL_QA` | `true` | ❓ Pre-generated QA lookup before RAG |
| `ENABLE_WIKI_SEARCH` | `true` | 📖 Include wiki pages in context retrieval |
| `ENABLE_CHUNK_SEARCH` | `true` | 🧩 Include raw chunks in context retrieval |
| `ENABLE_RERANKER` | `false` | 🔀 FlashRank cross-encoder reranking |
| `ENABLE_QUERY_REWRITE` | `false` | ✏️ LLM-based query rewriting |
| `ENABLE_GROUNDING` | `true` | 📌 Source-grounded answer generation |
| `ENABLE_RELATIONSHIP_SEARCH` | `false` | 🕸️ Graph-based entity relationship search |
| `ENABLE_METADATA_SEARCH` | `true` | 🏷️ Metadata-aware retrieval |

---

## 📋 API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | 💬 Ask a question (RAG chatbot) |
| `POST` | `/api/sources/url` | ➕ Add URL → trigger ingest pipeline |
| `GET` | `/api/sources` | 📋 List all knowledge sources |
| `GET` | `/api/wiki` | 📖 List wiki pages |
| `GET` | `/api/wiki/{id}` | 🔍 Get a single wiki page |
| `GET` | `/api/jobs` | 📊 List background jobs |
| `GET` | `/api/jobs/{id}` | 🔎 Get job status |
| `GET` | `/health` | 💚 Health check |

> ดู interactive docs ได้ที่ `http://localhost:8080/docs`

---

## 📁 Project Structure

```
enterprise-llm-wiki/
│
├── 🐍 backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── core/         # Config, logging, text utilities
│   │   ├── db/           # Supabase client
│   │   ├── jobs/         # Job runner (APScheduler)
│   │   ├── pipeline/     # Ingest pipeline orchestrator
│   │   ├── schemas/      # Pydantic request/response models
│   │   └── services/     # Business logic (chat, retrieval, wiki, QA...)
│   ├── scripts/          # Utility & test scripts
│   ├── sql/              # Database migration scripts
│   ├── requirements.txt
│   └── Dockerfile
│
├── 🌐 frontend/
│   ├── app/              # Next.js App Router pages
│   ├── package.json
│   └── Dockerfile
│
├── 📚 docs/
│   ├── ARCHITECTURE.md
│   ├── TECHNOLOGY_STACK.md
│   ├── ROADMAP.md
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
| Phase 1 — MVP | ✅ Done | URL ingest, chunking, embedding, vector search, chat API, basic frontend |
| Phase 2 — LLM Wiki | ✅ Done | Fact extraction, wiki generation, canonical QA |
| Phase 3 — Enterprise Jobs | 🔄 In Progress | Daily crawl, change detection, job monitor, batch processing |
| Phase 4 — Production | 📋 Planned | Auth, RLS per company, audit logs, evaluation, human review |
| Phase 5 — Agentic | 📋 Planned | LangGraph planner, multi-step retrieval, validation agent, GraphRAG |

---

## 🔐 Security Notes

> ⚠️ **สิ่งที่ต้องระวังก่อน push ขึ้น GitHub**

- ❌ ห้าม commit ไฟล์ `.env` ขึ้น version control
- 🔑 `SUPABASE_SERVICE_ROLE_KEY` ใช้ได้เฉพาะ **backend/worker** เท่านั้น — ห้ามส่งไป frontend หรือ browser
- 🌐 Production ควรกำหนด `ALLOW_ORIGINS` ให้เฉพาะ frontend domain จริง
- 🛡️ เปิด Supabase Row Level Security (RLS) ต่อ company สำหรับ multi-tenant isolation

---

## 📄 License

MIT © 2024

---

<div align="center">

Built with ❤️ using FastAPI · Next.js · Supabase · Ollama

</div>
