-- Nightly export record for ticket DEV-53.
-- This table is not reporting.pipeline_runs. pipeline_runs belongs to the
-- monthly clinic supply pipeline. job_runs belongs to scripts/nightly_export.py.
-- The processing status is the lock: job_runs_one_processing allows one
-- processing row per job_name. There is no separate lock table or lock column.

CREATE TABLE IF NOT EXISTS job_runs (
    id uuid PRIMARY KEY,
    job_name text NOT NULL,
    target_date date NOT NULL,
    status text NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    started_at timestamptz,
    finished_at timestamptz,
    error_message text,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS job_runs_job_name_target_date
    ON job_runs (job_name, target_date);

CREATE UNIQUE INDEX IF NOT EXISTS job_runs_one_processing
    ON job_runs (job_name)
    WHERE status = 'processing';
