-- Migration 007: unanswered_questions
-- Stores questions from the FloatingChat widget that the bot could not answer.
-- Allows admins to review, note, and resolve them, then improve the knowledge base.

create table if not exists unanswered_questions (
  id           uuid        primary key default gen_random_uuid(),
  company_code text        not null references companies(company_code),
  question     text        not null,
  session_id   text,                          -- pub_<uuid> for floating-chat sessions
  asked_at     timestamptz not null default now(),
  is_resolved  boolean     not null default false,
  resolved_at  timestamptz,
  note         text                           -- admin note / follow-up action
);

create index if not exists idx_unanswered_company_asked
  on unanswered_questions(company_code, asked_at desc);

create index if not exists idx_unanswered_resolved
  on unanswered_questions(is_resolved, asked_at desc);
