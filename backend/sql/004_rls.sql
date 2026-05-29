-- =============================================================================
-- 004_rls.sql  —  Row Level Security per company
-- =============================================================================
-- Run this in Supabase SQL Editor AFTER 002_schema.sql.
-- Safe to run multiple times (uses IF NOT EXISTS / DROP … IF EXISTS).
--
-- Architecture note:
--   • The backend uses the service_role key → bypasses RLS automatically.
--   • RLS protects against:
--       - Direct REST/JS clients using the anon key
--       - Future JWT-based per-company authenticated access
--       - Accidental exposure via Supabase Studio / anon API
--
-- How company isolation works for authenticated (JWT) requests:
--   The JWT must carry a custom claim:  { "company_code": "DEVES" }
--   This is set by your auth layer (see docs/AUTH.md for JWT setup).
-- =============================================================================

-- Helper: current company from JWT claim (returns NULL if not set)
CREATE OR REPLACE FUNCTION current_company_code() RETURNS text
  LANGUAGE sql STABLE
  AS $$
    SELECT nullif(
      current_setting('request.jwt.claims', true)::jsonb ->> 'company_code',
      ''
    )
  $$;


-- =============================================================================
-- companies
-- =============================================================================
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "companies_anon_deny"    ON companies;
DROP POLICY IF EXISTS "companies_auth_read"    ON companies;

-- anon: no access
CREATE POLICY "companies_anon_deny"
  ON companies AS RESTRICTIVE TO anon
  USING (false);

-- authenticated: read-only (company list is not sensitive)
CREATE POLICY "companies_auth_read"
  ON companies FOR SELECT TO authenticated
  USING (true);


-- =============================================================================
-- Tables with company_code — macro applied to each
-- =============================================================================

-- knowledge_sources
ALTER TABLE knowledge_sources ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "ks_anon_deny"   ON knowledge_sources;
DROP POLICY IF EXISTS "ks_auth_all"    ON knowledge_sources;
CREATE POLICY "ks_anon_deny" ON knowledge_sources AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "ks_auth_all"  ON knowledge_sources FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- source_pages
ALTER TABLE source_pages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "sp_anon_deny"   ON source_pages;
DROP POLICY IF EXISTS "sp_auth_all"    ON source_pages;
CREATE POLICY "sp_anon_deny" ON source_pages AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "sp_auth_all"  ON source_pages FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- document_chunks
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dc_anon_deny"   ON document_chunks;
DROP POLICY IF EXISTS "dc_auth_all"    ON document_chunks;
CREATE POLICY "dc_anon_deny" ON document_chunks AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "dc_auth_all"  ON document_chunks FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- extracted_facts
ALTER TABLE extracted_facts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "ef_anon_deny"   ON extracted_facts;
DROP POLICY IF EXISTS "ef_auth_all"    ON extracted_facts;
CREATE POLICY "ef_anon_deny" ON extracted_facts AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "ef_auth_all"  ON extracted_facts FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- wiki_pages
ALTER TABLE wiki_pages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "wp_anon_deny"   ON wiki_pages;
DROP POLICY IF EXISTS "wp_auth_all"    ON wiki_pages;
CREATE POLICY "wp_anon_deny" ON wiki_pages AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "wp_auth_all"  ON wiki_pages FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- canonical_qa
ALTER TABLE canonical_qa ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "qa_anon_deny"   ON canonical_qa;
DROP POLICY IF EXISTS "qa_auth_all"    ON canonical_qa;
CREATE POLICY "qa_anon_deny" ON canonical_qa AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "qa_auth_all"  ON canonical_qa FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- wiki_relationships
ALTER TABLE wiki_relationships ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "wr_anon_deny"   ON wiki_relationships;
DROP POLICY IF EXISTS "wr_auth_all"    ON wiki_relationships;
CREATE POLICY "wr_anon_deny" ON wiki_relationships AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "wr_auth_all"  ON wiki_relationships FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- answer_cache
ALTER TABLE answer_cache ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "ac_anon_deny"   ON answer_cache;
DROP POLICY IF EXISTS "ac_auth_all"    ON answer_cache;
CREATE POLICY "ac_anon_deny" ON answer_cache AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "ac_auth_all"  ON answer_cache FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- chat_sessions
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "cs_anon_deny"   ON chat_sessions;
DROP POLICY IF EXISTS "cs_auth_all"    ON chat_sessions;
CREATE POLICY "cs_anon_deny" ON chat_sessions AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "cs_auth_all"  ON chat_sessions FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- chat_messages (linked to chat_sessions via session_id — no direct company_code)
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "cm_anon_deny"   ON chat_messages;
DROP POLICY IF EXISTS "cm_auth_all"    ON chat_messages;
CREATE POLICY "cm_anon_deny" ON chat_messages AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "cm_auth_all"  ON chat_messages FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_sessions s
      WHERE s.id = session_id
        AND s.company_code = current_company_code()
    )
  );

-- job_runs
ALTER TABLE job_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "jr_anon_deny"   ON job_runs;
DROP POLICY IF EXISTS "jr_auth_all"    ON job_runs;
CREATE POLICY "jr_anon_deny" ON job_runs AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "jr_auth_all"  ON job_runs FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());

-- user_feedback
ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "uf_anon_deny"   ON user_feedback;
DROP POLICY IF EXISTS "uf_auth_all"    ON user_feedback;
CREATE POLICY "uf_anon_deny" ON user_feedback AS RESTRICTIVE TO anon USING (false);
CREATE POLICY "uf_auth_all"  ON user_feedback FOR ALL TO authenticated
  USING (company_code = current_company_code())
  WITH CHECK (company_code = current_company_code());


-- =============================================================================
-- Grant RPC functions execute permission (they run under service_role context)
-- =============================================================================
GRANT EXECUTE ON FUNCTION current_company_code() TO authenticated;
