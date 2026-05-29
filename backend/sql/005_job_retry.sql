-- =============================================================================
-- 005_job_retry.sql  —  Add retry_count to job_runs
-- =============================================================================
-- Safe to run multiple times.

ALTER TABLE job_runs
  ADD COLUMN IF NOT EXISTS retry_count int NOT NULL DEFAULT 0;

-- Index to quickly find jobs eligible for retry
CREATE INDEX IF NOT EXISTS idx_job_runs_retry
  ON job_runs (status, retry_count)
  WHERE status IN ('pending', 'failed');
