"""HealthCore monthly clinic supply performance flow.

Reads telemetry_events. Writes reporting.monthly_clinic_supply_performance.
Does not write telemetry_events and does not call the technical report.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Connection, Engine

from data.process.clinic_supply_kpis import (
    SUPPLY_EVENT_TYPES,
    build_clinic_month,
    dedup_events,
    parse_month_start,
)

_ROOT = Path(__file__).resolve().parents[2]
_RAW = _ROOT / "data" / "raw"
_EVAL = _ROOT / "data" / "eval"

_engine: Engine | None = None


class PipelineAlreadyRunning(RuntimeError):
    """A run for this month is already in progress."""


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


def ensure_reporting_tables(connection: Connection) -> None:
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS reporting"))
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reporting.monthly_clinic_supply_performance (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              clinic_id text NOT NULL,
              country text NOT NULL,
              month_start date NOT NULL,
              total_supply_cost numeric NOT NULL DEFAULT 0,
              supply_consumption_count integer NOT NULL DEFAULT 0,
              critical_stockout_count integer NOT NULL DEFAULT 0,
              expiry_risk_count integer NOT NULL DEFAULT 0,
              currency text NOT NULL,
              computed_at timestamptz NOT NULL DEFAULT now(),
              UNIQUE (clinic_id, month_start)
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reporting.pipeline_runs (
              run_id uuid PRIMARY KEY,
              flow_name text NOT NULL,
              month_start date NOT NULL,
              trigger text NOT NULL,
              phase text NOT NULL,
              status text NOT NULL,
              started_at timestamptz NOT NULL,
              finished_at timestamptz,
              records_extracted integer NOT NULL DEFAULT 0,
              records_loaded integer NOT NULL DEFAULT 0,
              records_rejected integer NOT NULL DEFAULT 0,
              cost_missing_count integer NOT NULL DEFAULT 0,
              distinct_session_count integer NOT NULL DEFAULT 0,
              clinics_reporting_count integer NOT NULL DEFAULT 0,
              distinct_request_count integer NOT NULL DEFAULT 0,
              silent_clinic_ids text NOT NULL DEFAULT '',
              error_message text
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS pipeline_runs_one_running
            ON reporting.pipeline_runs (month_start)
            WHERE status = 'Running'
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reporting.pipeline_run_events (
              run_id uuid NOT NULL,
              event_id text NOT NULL,
              request_id text NOT NULL,
              session_id text,
              event_type text NOT NULL,
              clinic_id text NOT NULL,
              event_timestamp timestamptz NOT NULL,
              PRIMARY KEY (run_id, event_id)
            )
            """
        )
    )


def _telemetry_columns(connection: Connection) -> set[str]:
    rows = connection.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'telemetry_events'
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
            """
        )
    ).all()
    return {row[0] for row in rows}


def _expr(columns: set[str], column: str, fallback: str) -> str:
    if column in columns:
        return column
    return fallback


def _fetch_supply_events(connection: Connection, month_start: date) -> list[dict]:
    columns = _telemetry_columns(connection)
    if "event_type" not in columns or "timestamp" not in columns:
        raise RuntimeError("telemetry_events is missing event_type or timestamp")
    if "tags" not in columns:
        raise RuntimeError("telemetry_events is missing tags")
    event_id = _expr(columns, "event_id", "COALESCE(tags->>'eventId', tags->>'event_id')")
    request_id = _expr(columns, "request_id", "COALESCE(tags->>'requestId', tags->>'request_id', '')")
    session_id = _expr(columns, "session_id", "COALESCE(tags->>'sessionId', tags->>'session_id')")
    from sqlalchemy import bindparam

    statement = text(
        f"""
        SELECT
          {event_id} AS event_id,
          {request_id} AS request_id,
          {session_id} AS session_id,
          timestamp,
          event_type,
          tags
        FROM telemetry_events
        WHERE event_type IN :event_types
          AND timestamp >= :month_start
          AND timestamp < :month_end
        """
    ).bindparams(bindparam("event_types", expanding=True))
    month_end = date(month_start.year + (month_start.month == 12), 1 if month_start.month == 12 else month_start.month + 1, 1)
    rows = connection.execute(
        statement,
        {
            "event_types": list(SUPPLY_EVENT_TYPES),
            "month_start": datetime(month_start.year, month_start.month, month_start.day, tzinfo=timezone.utc),
            "month_end": datetime(month_end.year, month_end.month, month_end.day, tzinfo=timezone.utc),
        },
    ).mappings().all()
    extracted = []
    for row in rows:
        tags = row["tags"] if isinstance(row["tags"], dict) else {}
        if isinstance(row["tags"], str):
            tags = json.loads(row["tags"])
        extracted.append(
            {
                "event_id": row["event_id"],
                "request_id": row["request_id"] or "",
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "event_type": row["event_type"],
                "clinic_id": tags.get("clinic_id"),
                "country": tags.get("country"),
                "total_cost": tags.get("total_cost"),
            }
        )
    return extracted


# Three attempts, ten seconds apart. Extract and load talk to Postgres.
# A Supabase pooler timeout usually clears on the next try. A fourth try would
# mean the outage is no longer transient.
DB_RETRIES = 3
DB_RETRY_DELAY_SECONDS = 10


def extract_supply_events(month_start_iso: str, run_id: str) -> dict:
    month_start = parse_month_start(month_start_iso)
    with get_engine().begin() as connection:
        ensure_reporting_tables(connection)
        connection.execute(
            text("UPDATE reporting.pipeline_runs SET phase = 'extract' WHERE run_id = :run_id"),
            {"run_id": run_id},
        )
        raw_rows = _fetch_supply_events(connection, month_start)
        kept, missing_ids = dedup_events(raw_rows)
        for event in kept:
            connection.execute(
                text(
                    """
                    INSERT INTO reporting.pipeline_run_events (
                      run_id, event_id, request_id, session_id, event_type, clinic_id, event_timestamp
                    ) VALUES (
                      :run_id, :event_id, :request_id, :session_id, :event_type, :clinic_id, :event_timestamp
                    )
                    ON CONFLICT (run_id, event_id) DO NOTHING
                    """
                ),
                {
                    "run_id": run_id,
                    "event_id": str(event["event_id"]),
                    "request_id": str(event.get("request_id") or ""),
                    "session_id": None if event.get("session_id") in (None, "") else str(event["session_id"]),
                    "event_type": event["event_type"],
                    "clinic_id": "" if event.get("clinic_id") is None else str(event["clinic_id"]),
                    "event_timestamp": event["timestamp"],
                },
            )
    serializable = []
    for event in kept:
        stamp = event["timestamp"]
        serializable.append(
            {
                "event_id": str(event["event_id"]),
                "request_id": str(event.get("request_id") or ""),
                "session_id": None if not event.get("session_id") else str(event["session_id"]),
                "timestamp": stamp.isoformat() if isinstance(stamp, datetime) else str(stamp),
                "event_type": event["event_type"],
                "clinic_id": None if event.get("clinic_id") is None else str(event["clinic_id"]),
                "country": None if event.get("country") is None else str(event["country"]),
                "total_cost": event.get("total_cost"),
            }
        )
    _RAW.mkdir(parents=True, exist_ok=True)
    (_RAW / f"supply_events_{month_start.isoformat()}.json").write_text(
        json.dumps(serializable, default=str),
        encoding="utf-8",
    )
    return {
        "month_start": month_start.isoformat(),
        "events": serializable,
        "missing_event_ids": missing_ids,
    }


def transform_clinic_month_kpis(extracted: dict) -> dict:
    month_start = parse_month_start(extracted["month_start"])
    events = []
    for event in extracted["events"]:
        stamp = event["timestamp"]
        if isinstance(stamp, str):
            stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        events.append({**event, "timestamp": stamp})
    with get_engine().connect() as connection:
        previous = _previous_consumption(connection, month_start)
    built = build_clinic_month(events, month_start, previous)
    built["records_rejected"] += int(extracted.get("missing_event_ids") or 0)
    return built


def _previous_consumption(connection: Connection, month_start: date) -> dict[str, int]:
    previous = (month_start.replace(day=1) - timedelta(days=1)).replace(day=1)
    rows = connection.execute(
        text(
            """
            SELECT clinic_id, supply_consumption_count
            FROM reporting.monthly_clinic_supply_performance
            WHERE month_start = :month_start
            """
        ),
        {"month_start": previous},
    ).all()
    return {str(row[0]): int(row[1]) for row in rows}


def load_monthly_clinic_supply_performance(result: dict, run_id: str) -> dict:
    # Same retry budget as extract. Load is the other task that opens Postgres.
    with get_engine().begin() as connection:
        connection.execute(
            text("UPDATE reporting.pipeline_runs SET phase = 'load' WHERE run_id = :run_id"),
            {"run_id": run_id},
        )
        for clinic in result["clinics"]:
            connection.execute(
                text(
                    """
                    INSERT INTO reporting.monthly_clinic_supply_performance (
                      clinic_id, country, month_start,
                      total_supply_cost, supply_consumption_count,
                      critical_stockout_count, expiry_risk_count,
                      currency, computed_at
                    ) VALUES (
                      :clinic_id, :country, :month_start,
                      :total_supply_cost, :supply_consumption_count,
                      :critical_stockout_count, :expiry_risk_count,
                      :currency, now()
                    )
                    ON CONFLICT (clinic_id, month_start) DO UPDATE SET
                      country = EXCLUDED.country,
                      total_supply_cost = EXCLUDED.total_supply_cost,
                      supply_consumption_count = EXCLUDED.supply_consumption_count,
                      critical_stockout_count = EXCLUDED.critical_stockout_count,
                      expiry_risk_count = EXCLUDED.expiry_risk_count,
                      currency = EXCLUDED.currency,
                      computed_at = EXCLUDED.computed_at
                    """
                ),
                {
                    "clinic_id": clinic["clinic_id"],
                    "country": clinic["country"],
                    "month_start": result["month_start"],
                    "total_supply_cost": clinic["total_supply_cost"],
                    "supply_consumption_count": clinic["supply_consumption_count"],
                    "critical_stockout_count": clinic["critical_stockout_count"],
                    "expiry_risk_count": clinic["expiry_risk_count"],
                    "currency": clinic["currency"],
                },
            )
        _close_run(connection, run_id, "Completed", "load", result, None)
    return result


def publish_eval_snapshot(result: dict) -> str:
    _EVAL.mkdir(parents=True, exist_ok=True)
    path = _EVAL / f"monthly_clinic_supply_performance_{result['month_start']}.json"
    path.write_text(json.dumps(result, default=str), encoding="utf-8")
    return str(path)


def _close_run(connection: Connection, run_id: str, status: str, phase: str, result: dict | None, error: str | None) -> None:
    counts = result or {}
    connection.execute(
        text(
            """
            UPDATE reporting.pipeline_runs SET
              status = :status,
              phase = :phase,
              finished_at = now(),
              records_extracted = :records_extracted,
              records_loaded = :records_loaded,
              records_rejected = :records_rejected,
              cost_missing_count = :cost_missing_count,
              distinct_session_count = :distinct_session_count,
              clinics_reporting_count = :clinics_reporting_count,
              distinct_request_count = :distinct_request_count,
              silent_clinic_ids = :silent_clinic_ids,
              error_message = :error_message
            WHERE run_id = :run_id
            """
        ),
        {
            "run_id": run_id,
            "status": status,
            "phase": phase,
            "records_extracted": int(counts.get("records_extracted") or 0),
            "records_loaded": int(counts.get("records_loaded") or 0),
            "records_rejected": int(counts.get("records_rejected") or 0),
            "cost_missing_count": int(counts.get("cost_missing_count") or 0),
            "distinct_session_count": int(counts.get("distinct_session_count") or 0),
            "clinics_reporting_count": int(counts.get("clinics_reporting_count") or 0),
            "distinct_request_count": int(counts.get("distinct_request_count") or 0),
            "silent_clinic_ids": counts.get("silent_clinic_ids") or "",
            "error_message": error,
        },
    )


def _open_run(month_start: date, trigger: str) -> str:
    run_id = str(uuid4())
    with get_engine().begin() as connection:
        ensure_reporting_tables(connection)
        running = connection.execute(
            text(
                """
                SELECT run_id FROM reporting.pipeline_runs
                WHERE month_start = :month_start AND status = 'Running'
                LIMIT 1
                """
            ),
            {"month_start": month_start},
        ).first()
        if running is not None:
            raise PipelineAlreadyRunning(str(running[0]))
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO reporting.pipeline_runs (
                      run_id, flow_name, month_start, trigger, phase, status, started_at
                    ) VALUES (
                      :run_id, 'monthly_clinic_supply_performance', :month_start, :trigger, 'extract', 'Running', now()
                    )
                    """
                ),
                {"run_id": run_id, "month_start": month_start, "trigger": trigger},
            )
        except IntegrityError as exc:
            raise PipelineAlreadyRunning(run_id) from exc
    return run_id


def _fail_run(run_id: str, phase: str, error: str) -> None:
    with get_engine().begin() as connection:
        _close_run(connection, run_id, "Failed", phase, None, error[:2000])


def latest_run_status() -> dict | None:
    with get_engine().begin() as connection:
        ensure_reporting_tables(connection)
        row = connection.execute(
            text(
                """
                SELECT run_id, flow_name, month_start, trigger, phase, status,
                       started_at, finished_at, records_extracted, records_loaded,
                       records_rejected, cost_missing_count, distinct_session_count,
                       clinics_reporting_count, distinct_request_count, silent_clinic_ids,
                       error_message
                FROM reporting.pipeline_runs
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
        ).mappings().first()
    if row is None:
        return None
    return _public_run(dict(row))


def query_monthly_clinic_supply_performance(month_start: str | None = None) -> dict:
    with get_engine().begin() as connection:
        ensure_reporting_tables(connection)
        if month_start:
            target = parse_month_start(month_start)
        else:
            latest = connection.execute(
                text("SELECT max(month_start) FROM reporting.monthly_clinic_supply_performance")
            ).scalar()
            if latest is None:
                target = parse_month_start(None)
            else:
                target = parse_month_start(latest)
        rows = connection.execute(
            text(
                """
                SELECT clinic_id, country, total_supply_cost, supply_consumption_count,
                       critical_stockout_count, expiry_risk_count, currency
                FROM reporting.monthly_clinic_supply_performance
                WHERE month_start = :month_start
                ORDER BY length(clinic_id), clinic_id
                """
            ),
            {"month_start": target},
        ).mappings().all()
    return {
        "month_start": target.isoformat(),
        "clinics": [
            {
                "clinic_id": row["clinic_id"],
                "country": row["country"],
                "total_supply_cost": float(row["total_supply_cost"]),
                "supply_consumption_count": int(row["supply_consumption_count"]),
                "critical_stockout_count": int(row["critical_stockout_count"]),
                "expiry_risk_count": int(row["expiry_risk_count"]),
                "currency": row["currency"],
            }
            for row in rows
        ],
    }


def trigger_monthly_clinic_supply_performance(month_start: str | None = None) -> dict:
    from data.pipelines.pipeline import monthly_clinic_supply_performance

    run_id = monthly_clinic_supply_performance(month_start=month_start, trigger="manual")
    with get_engine().connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT run_id, flow_name, month_start, trigger, phase, status,
                       started_at, finished_at, records_extracted, records_loaded,
                       records_rejected, cost_missing_count, distinct_session_count,
                       clinics_reporting_count, distinct_request_count, silent_clinic_ids,
                       error_message
                FROM reporting.pipeline_runs
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        ).mappings().one()
    return _public_run(dict(row))


def _public_run(row: dict) -> dict:
    started = row["started_at"]
    finished = row["finished_at"]
    month = row["month_start"]
    return {
        "run_id": str(row["run_id"]),
        "flow_name": row["flow_name"],
        "month_start": month.isoformat() if isinstance(month, date) else str(month),
        "trigger": row["trigger"],
        "phase": row["phase"],
        "status": row["status"],
        "started_at": started.isoformat() if isinstance(started, datetime) else started,
        "finished_at": finished.isoformat() if isinstance(finished, datetime) else finished,
        "records_extracted": row["records_extracted"],
        "records_loaded": row["records_loaded"],
        "records_rejected": row["records_rejected"],
        "cost_missing_count": row["cost_missing_count"],
        "distinct_session_count": row["distinct_session_count"],
        "clinics_reporting_count": row["clinics_reporting_count"],
        "distinct_request_count": row["distinct_request_count"],
        "silent_clinic_ids": row["silent_clinic_ids"],
        "error_message": row["error_message"],
    }
