create table if not exists companies (
  company_code text primary key,
  company_name text not null,
  is_active boolean default true,
  created_at timestamptz default now()
);

insert into companies(company_code, company_name)
values ('LOCKTON', 'Lockton')
on conflict(company_code) do nothing;

create table if not exists knowledge_sources (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  source_type text not null,
  source_url text,
  source_name text,
  crawl_schedule text,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(company_code, source_url)
);

create table if not exists source_pages (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  source_id uuid references knowledge_sources(id),
  url text not null,
  title text,
  content_markdown text,
  content_hash text,
  last_crawled_at timestamptz default now(),
  changed_at timestamptz,
  created_at timestamptz default now(),
  unique(company_code, url)
);

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  source_page_id uuid references source_pages(id),
  source_url text,
  title text,
  chunk_index int not null default 0,
  content text not null,
  embedding vector(768),
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists extracted_facts (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  title text,
  facts_json jsonb not null,
  source_urls jsonb default '[]'::jsonb,
  created_at timestamptz default now()
);

create table if not exists wiki_pages (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  title text not null,
  slug text not null,
  summary text,
  content_markdown text not null,
  source_urls jsonb default '[]'::jsonb,
  embedding vector(768),
  status text default 'draft',
  version int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(company_code, slug, version)
);

create table if not exists canonical_qa (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  wiki_page_id uuid references wiki_pages(id),
  question text not null,
  normalized_question text not null,
  answer text not null,
  embedding vector(768),
  priority int default 100,
  is_active boolean default true,
  created_at timestamptz default now()
);

create table if not exists wiki_relationships (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  source_entity text not null,
  target_entity text not null,
  relationship_type text not null,
  weight numeric default 1,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists answer_cache (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  question text not null,
  normalized_question text not null,
  answer text not null,
  embedding vector(768),
  source_refs jsonb default '[]'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(company_code, normalized_question)
);

create table if not exists chat_sessions (
  id uuid primary key default gen_random_uuid(),
  company_code text not null references companies(company_code),
  user_id text,
  summary text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references chat_sessions(id),
  role text not null,
  content text not null,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists job_runs (
  id uuid primary key default gen_random_uuid(),
  company_code text references companies(company_code),
  job_type text not null,
  status text not null default 'pending',
  payload jsonb default '{}'::jsonb,
  result jsonb,
  message text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists user_feedback (
  id uuid primary key default gen_random_uuid(),
  company_code text references companies(company_code),
  question text,
  answer text,
  rating int,
  comment text,
  created_at timestamptz default now()
);

create index if not exists idx_document_chunks_company on document_chunks(company_code);
create index if not exists idx_wiki_pages_company on wiki_pages(company_code);
create index if not exists idx_canonical_qa_company on canonical_qa(company_code);
create index if not exists idx_answer_cache_company on answer_cache(company_code);

create index if not exists idx_document_chunks_embedding on document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists idx_wiki_pages_embedding on wiki_pages using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists idx_canonical_qa_embedding on canonical_qa using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists idx_answer_cache_embedding on answer_cache using ivfflat (embedding vector_cosine_ops) with (lists = 100);
