# 🤖 Claude Code — Development Task Brief

คำแนะนำสำหรับ Claude Code ในการพัฒนาต่อระบบ Enterprise LLM Wiki Platform

---

## 🎯 Goal

สร้างระบบ **production-ready web service** สำหรับองค์กร ประกอบด้วย:

- 📥 Ingesting website URLs and files
- 🧩 Creating searchable chunks with vector embeddings
- 🧠 Extracting structured facts via LLM
- 📖 Generating LLM Wiki pages automatically
- ❓ Generating canonical QA pairs
- 💬 Answering chat questions with deterministic grounded answers
- 🔄 Running daily background jobs
- 🖥️ Providing frontend admin screens

> **Current state:** Working starter scaffold — improve it into production-ready code.

---

## 📋 Product Requirements

| # | Requirement |
|---|---|
| 1 | 👤 User can add one URL or file manually |
| 2 | ⚡ System creates a job and returns `job_id` immediately |
| 3 | 🏃 Fast Ingest first — content becomes searchable quickly |
| 4 | 🧠 Deep Enrichment afterward (facts → wiki → QA) |
| 5 | 💬 Chat search order: answer cache → canonical QA → wiki → chunks |
| 6 | 🔒 Same question must return stable answer as much as possible |
| 7 | 🏢 All knowledge separated by `company_code` |
| 8 | 🗄️ Use **Supabase Cloud** as primary database / vector store |
| 9 | 🤖 Use **Ollama Cloud** for chat / fact / wiki generation |
| 10 | 💻 Prefer **local Ollama** for embeddings if configured |
| 11 | 📌 Include source references in final answers |
| 12 | 🔐 Never expose `SUPABASE_SERVICE_ROLE_KEY` to frontend |

---

## 🗂️ Development Backlog

### 🔧 Phase 1 — Stabilize Backend

- [ ] Add full error handling (try/except with typed exceptions)
- [ ] Add structured logging (JSON format)
- [ ] Add migrations runner script
- [ ] Add integration tests
- [ ] Add typed service interfaces (Protocol / ABC)
- [ ] Add retry logic for Ollama and Supabase calls

### 🔩 Phase 2 — Complete Pipeline

- [ ] Improve web crawler (handle redirects, auth, robots.txt)
- [ ] Add file parsers: PDF, DOCX, XLSX, Markdown, TXT
- [ ] Add content hash change detection
- [ ] Add section extraction from documents
- [ ] Add robust chunk metadata (page, section, position)
- [ ] Add deep enrichment job queue with priority

### 🖥️ Phase 3 — Frontend Admin

- [ ] Build **Sources** page (list, add, delete)
- [ ] Build **Upload** page (URL + file drag-and-drop)
- [ ] Build **Wiki** page viewer + editor
- [ ] Build **Canonical QA** editor (approve / edit / disable)
- [ ] Build **Jobs Monitor** (status, logs, retry)
- [ ] Build **Chat Test Console** (with source display)

### 🚀 Phase 4 — Production

- [ ] Add authentication (JWT / Supabase Auth)
- [ ] Design and apply RLS policies per company
- [ ] Add audit log table + middleware
- [ ] Add evaluation loop (Ragas / DeepEval)
- [ ] Add feedback learning pipeline
- [ ] Complete Docker deployment
- [ ] Complete GitHub Actions CI/CD

---

## 🎨 Coding Style Guidelines

### Python (Backend)
- Use **type hints** everywhere
- Use **Pydantic models** for all request/response schemas
- Use **service classes** — keep business logic out of route handlers
- Keep route handlers thin (validate → call service → return response)

### TypeScript (Frontend)
- **Strict mode** enabled in tsconfig
- Build **reusable components** with clear props interfaces
- No `any` types without explicit justification

### Database
- Use **explicit SQL migrations** (numbered files in `backend/sql/`)
- Never run ad-hoc schema changes — always write a migration file

### General
- Secrets only in `.env` — never hardcode
- All knowledge queries must be scoped by `company_code`
- Prefer async/await patterns throughout
