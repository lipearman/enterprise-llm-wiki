# 🛠️ Technology Stack

รายละเอียด technology ทั้งหมดที่ใช้ในระบบ Enterprise LLM Wiki

---

## 🐍 Backend

| Library | Version | Purpose |
|---|---|---|
| **FastAPI** | 0.115.6 | REST API framework |
| **Uvicorn** | 0.34.0 | ASGI server |
| **Pydantic** | 2.10.4 | Data validation & serialization |
| **Pydantic Settings** | 2.7.1 | `.env` config management |
| **HTTPX** | 0.28.1 | Async HTTP client (Ollama API calls) |
| **python-dotenv** | 1.0.1 | Environment variable loading |
| **APScheduler** | 3.11.0 | Background job scheduling |
| **orjson** | 3.10.12 | Fast JSON serialization |

---

## 🗄️ Database

| Library | Version | Purpose |
|---|---|---|
| **supabase** | 2.11.0 | Supabase Python client |
| **psycopg[binary]** | 3.2.3 | PostgreSQL adapter |
| **pgvector** | 0.3.6 | Vector similarity search extension |

### Vector Search Configuration
- **Dimension:** 768d (nomic-embed-text)
- **Index:** IVFFlat with `lists = 100`
- **Operation:** `vector_cosine_ops`
- **Tables:** `document_chunks`, `wiki_pages`, `canonical_qa`, `answer_cache`

---

## 🕷️ Web Crawling & Content Extraction

| Library | Version | Purpose |
|---|---|---|
| **Trafilatura** | 2.0.0 | Main content extraction from web pages |
| **BeautifulSoup4** | 4.12.3 | HTML parsing fallback |
| **Markdownify** | 0.14.1 | HTML → Markdown conversion |

---

## 📄 File Parsing

| Library | Version | Format |
|---|---|---|
| **pypdf** | 5.1.0 | 📕 PDF |
| **python-docx** | 1.1.2 | 📘 DOCX (Microsoft Word) |
| **openpyxl** | 3.1.5 | 📗 XLSX (Microsoft Excel) |

> **Supported formats:** URL, PDF, DOCX, XLSX, Markdown, TXT

---

## ✂️ Text Processing

| Library | Version | Purpose |
|---|---|---|
| **langchain-text-splitters** | 0.3.4 | Intelligent document chunking |
| **python-multipart** | 0.0.20 | File upload handling |

---

## 🔀 Reranking *(Optional)*

| Library | Version | Purpose |
|---|---|---|
| **flashrank** | 0.2.10 | Cross-encoder reranking (enable via `ENABLE_RERANKER=true`) |

---

## 🤖 AI / LLM

### Chat & Generation (Cloud)
- **Provider:** Ollama Cloud
- **Model:** `gpt-oss:20b-cloud`
- **Used for:** Chat answers, fact extraction, wiki generation, QA generation
- **Settings:** `TEMPERATURE=0`, `TOP_P=0.1`, `SEED=42` (deterministic)

### Embeddings (Local Recommended)
- **Provider:** Ollama Local
- **Model:** `nomic-embed-text`
- **Dimension:** 768d
- **Used for:** All vector embedding operations

---

## 🌐 Frontend

| Library | Version | Purpose |
|---|---|---|
| **Next.js** | 14+ | React framework (App Router) |
| **TypeScript** | — | Type-safe JavaScript |
| **Tailwind CSS** | — | Utility-first CSS framework |

---

## 🐳 Infrastructure

| Tool | Purpose |
|---|---|
| **Docker** | Container packaging |
| **Docker Compose** | Multi-service orchestration (backend + frontend + worker) |
| **GitHub Actions** | CI/CD — Python compile check + Next.js build |

---

## 🔮 Optional / Future Stack

| Technology | Category | Use Case |
|---|---|---|
| **Redis** | Cache / Queue | In-memory cache, job queue |
| **FlashRank / FlagEmbedding** | Reranking | Better retrieval accuracy |
| **LangGraph** | Agentic | Multi-step reasoning planner |
| **GraphRAG** | Knowledge Graph | Entity relationship retrieval |
| **Ragas / DeepEval** | Evaluation | RAG quality measurement |
| **Supabase RLS** | Security | Per-company row-level security |
