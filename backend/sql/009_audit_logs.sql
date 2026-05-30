-- ── 009_audit_logs.sql ────────────────────────────────────────────────────────
-- Audit log table — records every significant mutation in the system.
-- Run once in Supabase SQL Editor.

create table if not exists audit_logs (
  id           uuid        default gen_random_uuid() primary key,
  created_at   timestamptz default now(),

  -- Who
  client_ip    text,
  api_key_tag  text,          -- last 4 chars of API key e.g. "***ab12", or "public"
  company_code text,

  -- What
  action       text not null, -- e.g. "chat.question", "source.add_url"
  http_method  text,
  path         text,

  -- Result
  status       text default 'ok',   -- ok | error | fail
  status_code  int  default 200,

  -- Extra context (action-specific JSON)
  detail       jsonb default '{}'::jsonb
);

-- Fast newest-first listing
create index if not exists audit_logs_created_at_idx
  on audit_logs (created_at desc);

-- Filter by company + action
create index if not exists audit_logs_company_action_idx
  on audit_logs (company_code, action, created_at desc);

-- Optional: auto-purge entries older than 90 days via pg_cron:
-- select cron.schedule('purge-audit-logs', '0 3 * * *',
--   $$delete from audit_logs where created_at < now() - interval '90 days'$$);
