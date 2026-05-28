# 🗺️ Roadmap

แผนพัฒนาระบบ Enterprise LLM Wiki ทั้งหมด 5 phases

---

## ✅ Phase 1 — Working MVP

> เป้าหมาย: ระบบสามารถนำเข้าข้อมูลและตอบคำถามได้ครบวงจร

- [x] 🕷️ URL ingestion
- [x] ✂️ Chunking
- [x] 🔢 Embedding
- [x] 🔍 Supabase vector search
- [x] 💬 Chat API
- [x] 🌐 Frontend chat + add URL

---

## ✅ Phase 2 — LLM Wiki

> เป้าหมาย: สร้าง knowledge base อัตโนมัติจาก LLM

- [x] 🧠 Extract facts from documents
- [x] 📖 Generate wiki pages (LLM)
- [x] ❓ Generate canonical QA (LLM)
- [x] 👁️ Wiki viewer
- [x] ✏️ QA editor

---

## 🔄 Phase 3 — Enterprise Jobs

> เป้าหมาย: ระบบ background jobs สำหรับ production scale

- [ ] 🕷️ Daily crawl job
- [ ] 🔍 Change detection (content hash)
- [ ] 📊 Job monitor UI
- [ ] 🔁 Retry failed jobs
- [ ] 📦 Batch processing

---

## 📋 Phase 4 — Production Ready

> เป้าหมาย: ความปลอดภัยและความน่าเชื่อถือระดับ production

- [ ] 🔐 Authentication
- [ ] 🛡️ Row Level Security (RLS) per company
- [ ] 📝 Audit logs
- [ ] 📐 Evaluation loop (Ragas / DeepEval)
- [ ] 👤 Human review / approval workflow
- [ ] 🔁 GitHub Actions full CI/CD

---

## 🚀 Phase 5 — Agentic Knowledge System

> เป้าหมาย: ระบบ AI agent ที่สามารถวางแผนและตอบคำถามซับซ้อนได้

- [ ] 🧩 LangGraph planner agent
- [ ] 🔗 Multi-step retrieval
- [ ] ✅ Validation agent
- [ ] 🕸️ GraphRAG (graph-based retrieval)
- [ ] 🛠️ Tool calling support

---

## 📊 Status Summary

| Phase | Status | Progress |
|---|---|---|
| Phase 1 — MVP | ✅ Done | ██████████ 100% |
| Phase 2 — LLM Wiki | ✅ Done | ██████████ 100% |
| Phase 3 — Enterprise Jobs | 🔄 In Progress | ████░░░░░░ 40% |
| Phase 4 — Production | 📋 Planned | ░░░░░░░░░░ 0% |
| Phase 5 — Agentic | 📋 Planned | ░░░░░░░░░░ 0% |
