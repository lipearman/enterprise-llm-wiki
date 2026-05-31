-- ── 010_ai_providers.sql ──────────────────────────────────────────────────────
-- Multi-provider AI configuration with per-role assignment + failover ordering.
-- Run once in Supabase SQL Editor.

-- Providers: an API endpoint + key (OpenAI-compatible protocol for now).
create table if not exists ai_providers (
  id         uuid        default gen_random_uuid() primary key,
  name       text        unique not null,           -- sambanova | cerebras | ollama | ...
  base_url   text        not null,                   -- https://api.sambanova.ai/v1
  api_key    text        not null,                   -- stored server-side, masked in API
  protocol   text        default 'openai',           -- 'openai' (OpenAI-compatible) | 'ollama'
  is_active  boolean     default true,
  created_at timestamptz default now()
);

-- Role → provider assignment. Each role can have several providers; the lowest
-- `priority` is tried first, and the service fails over to the next on a
-- rate-limit / transient error.
create table if not exists ai_role_assignments (
  id          uuid        default gen_random_uuid() primary key,
  role        text        not null,   -- answer_llm | chat | fact_extraction
                                      -- | wiki_generation | canonical_qa | embed
  provider_id uuid        references ai_providers(id) on delete cascade,
  model       text        not null,   -- gpt-oss-120b | gpt-oss:20b-cloud | ...
  priority    int         default 100,   -- lower = tried first
  is_active   boolean     default true,
  created_at  timestamptz default now()
);

create index if not exists ai_role_assignments_role_idx
  on ai_role_assignments (role, priority);

-- Known roles (for reference / frontend dropdown):
--   answer_llm        — final RAG chat answer
--   chat              — generic chat model (OLLAMA_CHAT_MODEL)
--   fact_extraction   — ingest fact extraction
--   wiki_generation   — ingest wiki page generation
--   canonical_qa      — canonical Q&A LLM matching
--   embed             — embeddings (only providers exposing /embeddings)
