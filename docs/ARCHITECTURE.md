# 🏗️ Architecture

ภาพรวมการออกแบบระบบ Enterprise LLM Wiki ทั้งหมด

---

## 📦 Module Overview

```
🌐 Frontend Web
├─ 💬 Chatbot
├─ 📖 Wiki Pages
├─ 📌 Knowledge Sources
├─ ➕ Upload URL / File
├─ ❓ Canonical QA
├─ 📊 Job Monitor
└─ ⚙️  Settings

⚡ Backend API
├─ 💬 Chat API
├─ 📌 Source API
├─ 📖 Wiki API
├─ ❓ QA API
├─ 📊 Job API
├─ 📤 Upload API
└─ 💚 Health API

🔄 Worker / Jobs
├─ ⚡ Fast Ingest Job
├─ 🧠 Deep Enrichment Job
├─ 🕷️  Daily Crawl Job
├─ 🔢 Embedding Rebuild Job
├─ 📐 Evaluation Job
└─ 🧹 Cache Cleanup Job

🗄️ Supabase
├─ 🏢 source registry
├─ 📄 raw pages / documents
├─ 🧩 chunks + vectors
├─ 🧠 facts
├─ 📖 wiki pages + vectors
├─ ❓ canonical QA + vectors
├─ 💬 chat sessions
├─ 🗃️  answer cache
└─ 📊 job runs / logs
```

---

## 📥 Ingest Flow

```
URL / File
    │
    ▼
🆕 Create Job
    │
    ▼
⚡ Fast Ingest
    ├─ 📥 load
    ├─ 🧹 clean
    ├─ 🗂️  section extract
    ├─ ✂️  chunk
    ├─ 🔢 embed
    └─ 💾 save chunks
    │
    ▼
✅ status: searchable
    │
    ▼
🧠 Deep Enrichment
    ├─ 🔍 extract facts
    ├─ 📖 generate wiki page
    ├─ ❓ generate canonical QA
    ├─ 🔢 embed wiki / QA
    └─ 🚀 publish
    │
    ▼
✅ status: enriched
```

---

## 💬 Chat Flow

```
Question
    │
    ▼
🔤 Normalize Question
    │
    ▼
🗃️  Answer Cache Search ─────── hit ──► 🟢 Return cached answer
    │ miss
    ▼
❓ Canonical QA Search ──────── hit ──► 🟢 Return QA answer
    │ miss
    ▼
📖 Wiki Page Search  ┐
🧩 Chunk Search      ┘ (parallel vector search)
    │
    ▼
📊 Merge & Sort by similarity
    │
    ▼
🔀 Reranker (optional)
    │
    ▼
🤖 LLM → Grounded Answer
    │
    ▼
💾 Save to answer_cache + chat_messages
    │
    ▼
📤 Return response + sources
```

---

## 🗄️ Database Layer

```
companies
    └── knowledge_sources ──────────────────────┐
            └── source_pages                     │
                    └── document_chunks          │ company_code
                                                 │ (multi-tenant)
wiki_pages ─────────────── canonical_qa         │
extracted_facts                                  │
answer_cache                                     │
wiki_relationships                               │
chat_sessions ──── chat_messages                 │
job_runs                                         │
user_feedback ───────────────────────────────────┘
```

### Vector Search Indexes

| Table | Index Type | Operation |
|---|---|---|
| `document_chunks` | IVFFlat (lists=100) | `vector_cosine_ops` |
| `wiki_pages` | IVFFlat (lists=100) | `vector_cosine_ops` |
| `canonical_qa` | IVFFlat (lists=100) | `vector_cosine_ops` |
| `answer_cache` | IVFFlat (lists=100) | `vector_cosine_ops` |

---

## 🔗 Service Dependencies

```
ChatService
    └── RetrievalService
            ├── OllamaClient (embed_llm)
            └── SupabaseClient (RPC: match_*)

IngestPipeline
    ├── CrawlerService
    ├── ChunkingService
    ├── OllamaClient (embed_llm)
    ├── ExtractionService → OllamaClient (chat_llm)
    ├── WikiService       → OllamaClient (chat_llm)
    └── QAService         → OllamaClient (chat_llm)

JobRunner (APScheduler)
    ├── IngestPipeline (fast ingest)
    ├── IngestPipeline (deep enrichment)
    └── CrawlerService (daily crawl)
```

---

## 🌐 API Layer

```
FastAPI App
    ├── CORSMiddleware  (configurable origins)
    ├── GET  /          (root info)
    ├── GET  /health    (health check)
    ├── POST /api/chat  (RAG answer)
    ├── POST /api/sources/url  (add URL)
    ├── GET  /api/sources      (list sources)
    ├── GET  /api/wiki         (list wiki pages)
    ├── GET  /api/wiki/{id}    (get wiki page)
    ├── GET  /api/jobs         (list jobs)
    └── GET  /api/jobs/{id}    (job status)
```
