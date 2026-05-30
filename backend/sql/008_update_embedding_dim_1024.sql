-- ============================================================
--  Migration 008 — Update embedding dimension 768 → 1024
--  Required when switching from nomic-embed-text (768d)
--  to mxbai-embed-large (1024d).
--
--  ⚠️  This drops all existing embedding vectors.
--      After running this, re-ingest your data:
--      POST /api/jobs/crawl-all   (or re-add each source)
-- ============================================================

-- 1. Drop old embedding columns (768d data is incompatible)
ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE wiki_pages      DROP COLUMN IF EXISTS embedding;
ALTER TABLE canonical_qa    DROP COLUMN IF EXISTS embedding;
ALTER TABLE answer_cache    DROP COLUMN IF EXISTS embedding;

-- 2. Recreate columns with 1024d
ALTER TABLE document_chunks ADD COLUMN embedding vector(1024);
ALTER TABLE wiki_pages      ADD COLUMN embedding vector(1024);
ALTER TABLE canonical_qa    ADD COLUMN embedding vector(1024);
ALTER TABLE answer_cache    ADD COLUMN embedding vector(1024);

-- 3. Drop old ivfflat indexes (dimension-specific)
DROP INDEX IF EXISTS idx_document_chunks_embedding;
DROP INDEX IF EXISTS idx_wiki_pages_embedding;
DROP INDEX IF EXISTS idx_canonical_qa_embedding;
DROP INDEX IF EXISTS idx_answer_cache_embedding;

-- 4. Recreate indexes for 1024d
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
  ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_wiki_pages_embedding
  ON wiki_pages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_canonical_qa_embedding
  ON canonical_qa USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_answer_cache_embedding
  ON answer_cache USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 5. Update RPC functions to accept vector(1024)
CREATE OR REPLACE FUNCTION match_document_chunks(
  query_embedding vector(1024),
  match_company_code text,
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  title text,
  source_url text,
  content text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    dc.id,
    dc.title,
    dc.source_url,
    dc.content,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM document_chunks dc
  WHERE dc.company_code = match_company_code
    AND dc.embedding IS NOT NULL
    AND 1 - (dc.embedding <=> query_embedding) >= match_threshold
  ORDER BY dc.embedding <=> query_embedding ASC, dc.source_url ASC, dc.chunk_index ASC
  LIMIT match_count;
$$;

CREATE OR REPLACE FUNCTION match_wiki_pages(
  query_embedding vector(1024),
  match_company_code text,
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  title text,
  source_url text,
  content_markdown text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    wp.id,
    wp.title,
    NULL::text AS source_url,
    wp.content_markdown,
    1 - (wp.embedding <=> query_embedding) AS similarity
  FROM wiki_pages wp
  WHERE wp.company_code = match_company_code
    AND wp.embedding IS NOT NULL
    AND wp.status = 'published'
    AND 1 - (wp.embedding <=> query_embedding) >= match_threshold
  ORDER BY wp.embedding <=> query_embedding ASC, wp.title ASC
  LIMIT match_count;
$$;

CREATE OR REPLACE FUNCTION match_canonical_qa(
  query_embedding vector(1024),
  match_company_code text,
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  question text,
  answer text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    qa.id,
    qa.question,
    qa.answer,
    1 - (qa.embedding <=> query_embedding) AS similarity
  FROM canonical_qa qa
  WHERE qa.company_code = match_company_code
    AND qa.is_active = TRUE
    AND qa.embedding IS NOT NULL
    AND 1 - (qa.embedding <=> query_embedding) >= match_threshold
  ORDER BY qa.embedding <=> query_embedding ASC, qa.priority ASC, qa.question ASC
  LIMIT match_count;
$$;

CREATE OR REPLACE FUNCTION match_answer_cache(
  query_embedding vector(1024),
  match_company_code text,
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  question text,
  answer text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    ac.id,
    ac.question,
    ac.answer,
    1 - (ac.embedding <=> query_embedding) AS similarity
  FROM answer_cache ac
  WHERE ac.company_code = match_company_code
    AND ac.embedding IS NOT NULL
    AND 1 - (ac.embedding <=> query_embedding) >= match_threshold
  ORDER BY ac.embedding <=> query_embedding ASC, ac.updated_at DESC
  LIMIT match_count;
$$;

-- 6. Ensure DEVES company exists (default company code in .env)
INSERT INTO companies(company_code, company_name)
VALUES ('DEVES', 'Deves Insurance')
ON CONFLICT(company_code) DO NOTHING;
