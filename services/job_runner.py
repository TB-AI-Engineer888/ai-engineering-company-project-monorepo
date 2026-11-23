"""Status control for the nightly telemetry export.

job_runs is this job's record. reporting.pipeline_runs stays the monthly
pipeline's record. This module does not import the API.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

JOB_NAME = "nightly_export"
STATUSES = ("pending", "processing", "completed", "failed")

_engine: Engine | None = None


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://") :]
    host = url.split("@")[-1]
    local = "127.0.0.1" in host or "localhost" in host
    if "sslmode=" not in url and not local:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), pool_pre_ping=True)
    return _engine


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def ensure_job_runs_table(connection: Connection) -> None:
    if connection.dialect.name == "postgresql":
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS job_runs (
                    id uuid PRIMARY KEY,
                    job_name text NOT NULL,
                    target_date date NOT NULL,
                    status text NOT NULL CHECK (
                        status IN ('pending', 'processing', 'completed', 'failed')
                    ),
                    started_at timestamptz,
                    finished_at timestamptz,
                    error_message text,
                    created_at timestamptz NOT NULL
                )
                """
            )
        )
    else:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS job_runs (
                    id text PRIMARY KEY,
                    job_name text NOT NULL,
                    target_date text NOT NULL,
                    status text NOT NULL CHECK (
                        status IN ('pending', 'processing', 'completed', 'failed')
                    ),
                    started_at text,
                    finished_at text,
                    error_message text,
                    created_at text NOT NULL
                )
                """
            )
        )
    connection.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS job_runs_job_name_target_date
                ON job_runs (job_name, target_date)
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS job_runs_one_processing
                ON job_runs (job_name)
                WHERE status = 'processing'
            """
        )
    )


def has_processing_lock(connection: Connection, job_name: str = JOB_NAME) -> bool:
    row = connection.execute(
        text(
            """
            SELECT 1
            FROM job_runs
            WHERE job_name = :job_name AND status = 'processing'
            LIMIT 1
            """
        ),
        {"job_name": job_name},
    ).first()
    return row is not None


def has_completed_for_date(connection: Connection, job_name: str, target_date: date) -> bool:
    row = connection.execute(
        text(
            """
            SELECT 1
            FROM job_runs
            WHERE job_name = :job_name
              AND target_date = :target_date
              AND status = 'completed'
            LIMIT 1
            """
        ),
        {"job_name": job_name, "target_date": target_date.isoformat()},
    ).first()
    return row is not None


def create_job_run(connection: Connection, job_name: str, target_date: date) -> str:
    job_id = str(uuid4())
    connection.execute(
        text(
            """
            INSERT INTO job_runs (
                id, job_name, target_date, status,
                started_at, finished_at, error_message, created_at
            ) VALUES (
                :id, :job_name, :target_date, 'pending',
                NULL, NULL, NULL, :created_at
            )
            """
        ),
        {
            "id": job_id,
            "job_name": job_name,
            "target_date": target_date.isoformat(),
            "created_at": utc_now(),
        },
    )
    return job_id


def update_job_run(
    connection: Connection,
    job_id: str,
    status: str,
    error_message: str | None = None,
) -> int:
    if status not in STATUSES or status == "pending":
        raise ValueError(status)
    now = utc_now()
    if status == "processing":
        result = connection.execute(
            text(
                """
                UPDATE job_runs
                SET status = 'processing', started_at = :now, error_message = NULL
                WHERE id = :id AND status = 'pending'
                """
            ),
            {"id": job_id, "now": now},
        )
        return int(result.rowcount or 0)
    result = connection.execute(
        text(
            """
            UPDATE job_runs
            SET status = :status, finished_at = :now, error_message = :error_message
            WHERE id = :id AND status = 'processing'
            """
        ),
        {"id": job_id, "status": status, "now": now, "error_message": error_message},
    )
    return int(result.rowcount or 0)


def delete_pending(connection: Connection, job_id: str) -> None:
    connection.execute(
        text("DELETE FROM job_runs WHERE id = :id AND status = 'pending'"),
        {"id": job_id},
    )


def get_job_run(connection: Connection, job_id: str) -> dict | None:
    row = connection.execute(
        text(
            """
            SELECT id, job_name, target_date, status, started_at, finished_at,
                   error_message, created_at
            FROM job_runs
            WHERE id = :id
            """
        ),
        {"id": job_id},
    ).mappings().first()
    return dict(row) if row else None


def query_job_runs(
    connection: Connection,
    job_name: str | None = None,
    target_date: date | None = None,
    status: str | None = None,
) -> list[dict]:
    clauses: list[str] = []
    params: dict[str, str] = {}
    if job_name is not None:
        clauses.append("job_name = :job_name")
        params["job_name"] = job_name
    if target_date is not None:
        clauses.append("target_date = :target_date")
        params["target_date"] = target_date.isoformat()
    if status is not None:
        clauses.append("status = :status")
        params["status"] = status
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        text(
            f"""
            SELECT id, job_name, target_date, status, started_at, finished_at,
                   error_message, created_at
            FROM job_runs
            {where}
            ORDER BY created_at, id
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


def csv_destination(raw_dir: Path, target_date: date) -> Path:
    return raw_dir / f"telemetry_{target_date.isoformat()}.csv"


def _day_bounds(target_date: date) -> tuple[str, str]:
    start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _telemetry_columns(connection: Connection) -> list[str]:
    if connection.dialect.name == "postgresql":
        rows = connection.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'telemetry_events'
                  AND table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY ordinal_position
                """
            )
        ).all()
        names: list[str] = []
        for row in rows:
            if row[0] not in names:
                names.append(row[0])
        return names
    rows = connection.execute(text("PRAGMA table_info(telemetry_events)")).all()
    return [row[1] for row in rows]


def _csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def export_telemetry_csv(connection: Connection, target_date: date, destination: Path) -> Path:
    """Write telemetry_events for the UTC day. Leave an existing file untouched."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    columns = _telemetry_columns(connection)
    if "timestamp" not in columns:
        raise RuntimeError("telemetry_events is missing timestamp")
    for name in columns:
        if not name.replace("_", "").isalnum():
            raise RuntimeError(f"unexpected telemetry column {name}")
    start, end = _day_bounds(target_date)
    selected = ", ".join(columns)
    rows = connection.execute(
        text(
            f"""
            SELECT {selected}
            FROM telemetry_events
            WHERE timestamp >= :start AND timestamp < :end
            ORDER BY timestamp
            """
        ),
        {"start": start, "end": end},
    ).mappings().all()
    partial = destination.with_name(destination.name + ".partial")
    try:
        with partial.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({column: _csv_cell(row[column]) for column in columns})
        if destination.exists():
            return destination
        os.replace(partial, destination)
    finally:
        if partial.exists():
            partial.unlink()
    return destination
