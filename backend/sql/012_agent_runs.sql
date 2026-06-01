-- Phase 7: persistent agent run history (observability).
-- Run once in the Supabase SQL Editor. Until then agent_graph keeps the last
-- ~25 runs in memory (lost on restart).

create table if not exists public.agent_runs (
    id             uuid primary key default gen_random_uuid(),
    company_code   text,
    question       text,
    answer_preview text,
    duration       numeric,
    iterations     int,
    steps          jsonb not null default '[]'::jsonb,
    created_at     timestamptz not null default now()
);

create index if not exists idx_agent_runs_created  on public.agent_runs (created_at desc);
create index if not exists idx_agent_runs_company  on public.agent_runs (company_code, created_at desc);
