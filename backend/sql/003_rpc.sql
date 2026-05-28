create or replace function match_document_chunks(
  query_embedding vector(768),
  match_company_code text,
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  title text,
  source_url text,
  content text,
  similarity float
)
language sql stable
as $$
  select
    dc.id,
    dc.title,
    dc.source_url,
    dc.content,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  where dc.company_code = match_company_code
    and dc.embedding is not null
    and 1 - (dc.embedding <=> query_embedding) >= match_threshold
  order by dc.embedding <=> query_embedding asc, dc.source_url asc, dc.chunk_index asc
  limit match_count;
$$;

create or replace function match_wiki_pages(
  query_embedding vector(768),
  match_company_code text,
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  title text,
  source_url text,
  content_markdown text,
  similarity float
)
language sql stable
as $$
  select
    wp.id,
    wp.title,
    null::text as source_url,
    wp.content_markdown,
    1 - (wp.embedding <=> query_embedding) as similarity
  from wiki_pages wp
  where wp.company_code = match_company_code
    and wp.embedding is not null
    and wp.status = 'published'
    and 1 - (wp.embedding <=> query_embedding) >= match_threshold
  order by wp.embedding <=> query_embedding asc, wp.title asc
  limit match_count;
$$;

create or replace function match_canonical_qa(
  query_embedding vector(768),
  match_company_code text,
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  question text,
  answer text,
  similarity float
)
language sql stable
as $$
  select
    qa.id,
    qa.question,
    qa.answer,
    1 - (qa.embedding <=> query_embedding) as similarity
  from canonical_qa qa
  where qa.company_code = match_company_code
    and qa.is_active = true
    and qa.embedding is not null
    and 1 - (qa.embedding <=> query_embedding) >= match_threshold
  order by qa.embedding <=> query_embedding asc, qa.priority asc, qa.question asc
  limit match_count;
$$;

create or replace function match_answer_cache(
  query_embedding vector(768),
  match_company_code text,
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  question text,
  answer text,
  similarity float
)
language sql stable
as $$
  select
    ac.id,
    ac.question,
    ac.answer,
    1 - (ac.embedding <=> query_embedding) as similarity
  from answer_cache ac
  where ac.company_code = match_company_code
    and ac.embedding is not null
    and 1 - (ac.embedding <=> query_embedding) >= match_threshold
  order by ac.embedding <=> query_embedding asc, ac.updated_at desc
  limit match_count;
$$;
