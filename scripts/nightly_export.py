#!/usr/bin/env python3
"""Export one UTC day of telemetry and trigger the supply pipeline."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, TextIO

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

import job_runner

JOB_NAME = job_runner.JOB_NAME
RAW_DIR = ROOT / "data" / "raw"
logger = logging.getLogger("healthcore.nightly_export")
Pipeline = Callable[[date], None]


def configure_logging(stream: TextIO | None = None) -> None:
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%SZ")
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


def log_status(level: int, status: str, detail: str = "") -> None:
    message = f"nightly_export {status}"
    cleaned = " ".join(detail.split())
    if cleaned:
        message = f"{message} {cleaned}"
    logger.log(level, message)


def resolve_target_date(now: datetime | None = None) -> date:
    raw = os.environ.get("TARGET_DATE", "").strip()
    if raw:
        return date.fromisoformat(raw)
    clock = now or datetime.now(timezone.utc)
    return (clock.astimezone(timezone.utc) - timedelta(days=1)).date()


def run_pipeline(target_date: date) -> None:
    script = ROOT / "data" / "pipelines" / "pipeline.py"
    completed = subprocess.run(
        [sys.executable, str(script), target_date.isoformat()],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(detail[-2000:] or f"pipeline exited {completed.returncode}")


def _fail(engine: Engine, job_id: str, message: str) -> None:
    with engine.begin() as connection:
        row = job_runner.get_job_run(connection, job_id)
        if row and row["status"] == "processing":
            job_runner.update_job_run(connection, job_id, "failed", message)


def _close_if_processing(engine: Engine, job_id: str) -> None:
    try:
        with engine.begin() as connection:
            row = job_runner.get_job_run(connection, job_id)
            if not row or row["status"] != "processing":
                return
            job_runner.update_job_run(
                connection,
                job_id,
                "failed",
                "execution ended while processing",
            )
        log_status(logging.ERROR, "failed", "execution ended while processing")
    except Exception as exc:
        log_status(logging.ERROR, "failed", str(exc) or exc.__class__.__name__)


def run_nightly_export(
    engine: Engine,
    target_date: date,
    raw_dir: Path,
    pipeline: Pipeline | None = None,
) -> str:
    """Return aborted, skipped, completed, or failed. A failed row is never left processing."""
    runner = pipeline or run_pipeline
    with engine.begin() as connection:
        job_runner.ensure_job_runs_table(connection)
        if job_runner.has_processing_lock(connection, JOB_NAME):
            log_status(logging.INFO, "processing", "aborted")
            return "aborted"
        if job_runner.has_completed_for_date(connection, JOB_NAME, target_date):
            log_status(logging.INFO, "completed", "skipped as duplicate")
            return "skipped"
        job_id = job_runner.create_job_run(connection, JOB_NAME, target_date)
    log_status(logging.INFO, "pending")

    try:
        with engine.begin() as connection:
            claimed = job_runner.update_job_run(connection, job_id, "processing")
    except IntegrityError:
        claimed = 0
    if claimed != 1:
        with engine.begin() as connection:
            job_runner.delete_pending(connection, job_id)
        log_status(logging.INFO, "processing", "aborted")
        return "aborted"
    log_status(logging.INFO, "processing")

    try:
        with engine.begin() as connection:
            job_runner.export_telemetry_csv(
                connection,
                target_date,
                job_runner.csv_destination(raw_dir, target_date),
            )
        runner(target_date)
        with engine.begin() as connection:
            job_runner.update_job_run(connection, job_id, "completed")
        log_status(logging.INFO, "completed")
        return "completed"
    except Exception as exc:
        message = " ".join(str(exc).split()) or exc.__class__.__name__
        try:
            _fail(engine, job_id, message)
        except Exception as write_error:
            log_status(logging.ERROR, "failed", f"{message} ({write_error})")
        else:
            log_status(logging.ERROR, "failed", message)
        return "failed"
    finally:
        _close_if_processing(engine, job_id)


def main() -> int:
    configure_logging()
    try:
        target_date = resolve_target_date()
    except ValueError as exc:
        log_status(logging.ERROR, "failed", str(exc))
        return 1
    try:
        engine = job_runner.get_engine()
    except Exception as exc:
        log_status(logging.ERROR, "failed", str(exc) or exc.__class__.__name__)
        return 1
    outcome = run_nightly_export(engine, target_date, RAW_DIR, run_pipeline)
    if outcome == "failed":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
