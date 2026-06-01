-- Phase 7: multi-step claim intake with per-session checkpointing.
-- Run once in the Supabase SQL Editor. Until then claim_service falls back to
-- an in-memory store (state lost on restart).

create table if not exists public.claim_intakes (
    id            uuid primary key default gen_random_uuid(),
    session_id    text not null,
    company_code  text not null,
    current_step  int  not null default 0,
    data          jsonb not null default '{}'::jsonb,
    status        text not null default 'collecting',   -- collecting | submitted | cancelled
    reference     text,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

create index if not exists idx_claim_intakes_session on public.claim_intakes (session_id, status);

-- keep updated_at fresh
create or replace function public.touch_claim_intakes() returns trigger as $$
begin new.updated_at = now(); return new; end; $$ language plpgsql;

drop trigger if exists trg_touch_claim_intakes on public.claim_intakes;
create trigger trg_touch_claim_intakes before update on public.claim_intakes
    for each row execute function public.touch_claim_intakes();
