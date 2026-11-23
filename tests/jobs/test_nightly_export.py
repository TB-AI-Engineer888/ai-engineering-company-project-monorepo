"""Nightly export."""

from __future__ import annotations

import ast
import logging
import sys
import threading
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "scripts"))

import job_runner
import nightly_export

DAY = date(2026, 11, 22)


def _engine(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'jobs.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 5},
        poolclass=NullPool,
    )

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    with engine.begin() as connection:
        job_runner.ensure_job_runs_table(connection)
        connection.execute(
            text(
                """
                CREATE TABLE telemetry_events (
                    id text,
                    timestamp text,
                    service text,
                    event_type text,
                    level text,
                    value text,
                    message text,
                    tags text
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO telemetry_events
                    (id, timestamp, service, event_type, level, value, message, tags)
                VALUES
                    ('evt-1', '2026-11-22T10:15:00+00:00', 'inventory', 'supply_used',
                     'info', '2', 'gloves', '{"clinic_id": "1"}'),
                    ('evt-2', '2026-11-22T18:40:00+00:00', 'inventory', 'stock_adjusted',
                     'warn', '5', 'masks', '{"clinic_id": "2"}'),
                    ('evt-3', '2026-11-23T00:00:00+00:00', 'inventory', 'supply_used',
                     'info', '9', 'next day', '{}')
                """
            )
        )
    return engine


def _rows(engine, target: date | None = None) -> list[dict]:
    with engine.begin() as connection:
        return job_runner.query_job_runs(connection, job_name=job_runner.JOB_NAME, target_date=target)


def test_modules_do_not_import_the_api() -> None:
    for relative in ("scripts/nightly_export.py", "services/job_runner.py"):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        lowered = " ".join(imported).lower()
        assert "fastapi" not in lowered
        assert "apscheduler" not in lowered
        assert "services.api" not in lowered
    assert "fastapi" not in sys.modules


def test_crontab_and_job_runs_sql() -> None:
    cron = (ROOT / "scripts" / "nightly_export.cron").read_text(encoding="utf-8")
    assert "15 6 * * *" in cron
    assert "nightly_export.py" in cron
    assert "fastapi" not in cron.lower()
    sql = (ROOT / "services" / "migrations" / "001_job_runs.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS job_runs" in sql
    assert "target_date" in sql
    assert "(job_name, target_date)" in sql
    assert "CREATE TABLE IF NOT EXISTS reporting" not in sql
    assert "ALTER TABLE" not in sql.upper()


def test_target_date_override_and_yesterday_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARGET_DATE", "2026-11-18")
    assert nightly_export.resolve_target_date() == date(2026, 11, 18)
    monkeypatch.delenv("TARGET_DATE")
    now = datetime(2026, 11, 23, 6, 15, tzinfo=timezone.utc)
    assert nightly_export.resolve_target_date(now) == DAY


def test_csv_contains_only_the_target_day(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    calls: list[date] = []
    buffer = StringIO()
    nightly_export.configure_logging(buffer)
    outcome = nightly_export.run_nightly_export(engine, DAY, tmp_path, lambda day: calls.append(day))
    assert outcome == "completed"
    assert calls == [DAY]
    csv_path = tmp_path / "telemetry_2026-11-22.csv"
    body = csv_path.read_text(encoding="utf-8")
    assert body.splitlines()[0].startswith("id,timestamp,")
    assert "evt-1" in body
    assert "evt-2" in body
    assert "evt-3" not in body
    assert "next day" not in body
    rows = _rows(engine, DAY)
    assert len(rows) == 1
    assert rows[0]["status"] == "completed"
    assert str(rows[0]["target_date"]) == "2026-11-22"
    assert rows[0]["error_message"] in (None, "")
    log = buffer.getvalue()
    assert "nightly_export pending" in log
    assert "nightly_export processing" in log
    assert "nightly_export completed" in log
    for line in log.splitlines():
        assert line.startswith("202")
        assert "Z INFO nightly_export" in line


def test_existing_csv_is_not_rewritten(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    csv_path = tmp_path / "telemetry_2026-11-22.csv"
    csv_path.write_text("already,here\n", encoding="utf-8")
    outcome = nightly_export.run_nightly_export(engine, DAY, tmp_path, lambda _day: None)
    assert outcome == "completed"
    assert csv_path.read_text(encoding="utf-8") == "already,here\n"


def test_completed_day_skips_export_and_pipeline(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    calls: list[str] = []
    buffer = StringIO()
    nightly_export.configure_logging(buffer)
    assert nightly_export.run_nightly_export(engine, DAY, tmp_path, lambda _day: calls.append("run")) == "completed"
    assert nightly_export.run_nightly_export(engine, DAY, tmp_path, lambda _day: calls.append("run")) == "skipped"
    assert calls == ["run"]
    assert "skipped as duplicate" in buffer.getvalue()
    with engine.begin() as connection:
        assert job_runner.has_completed_for_date(connection, job_runner.JOB_NAME, DAY) is True
        assert job_runner.has_completed_for_date(connection, job_runner.JOB_NAME, date(2026, 11, 21)) is False


def test_another_day_still_runs(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    calls: list[date] = []
    earlier = date(2026, 11, 21)
    nightly_export.run_nightly_export(engine, DAY, tmp_path, lambda day: calls.append(day))
    outcome = nightly_export.run_nightly_export(engine, earlier, tmp_path, lambda day: calls.append(day))
    assert outcome == "completed"
    assert calls == [DAY, earlier]
    assert (tmp_path / "telemetry_2026-11-21.csv").exists()


def test_failure_ends_failed_and_can_be_retried(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    buffer = StringIO()
    nightly_export.configure_logging(buffer)

    def explode(_day: date) -> None:
        raise RuntimeError("pipeline down")

    assert nightly_export.run_nightly_export(engine, DAY, tmp_path, explode) == "failed"
    rows = _rows(engine, DAY)
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert rows[0]["error_message"] == "pipeline down"
    assert rows[0]["finished_at"]
    with engine.begin() as connection:
        assert job_runner.has_processing_lock(connection, job_runner.JOB_NAME) is False
    log = buffer.getvalue()
    assert "Z ERROR nightly_export failed pipeline down" in log

    assert nightly_export.run_nightly_export(engine, DAY, tmp_path, lambda _day: None) == "completed"
    finished = _rows(engine, DAY)
    assert [row["status"] for row in finished] == ["failed", "completed"]
    csv_path = tmp_path / "telemetry_2026-11-22.csv"
    assert "evt-1" in csv_path.read_text(encoding="utf-8")


def test_processing_row_aborts_a_second_instance(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        job_id = job_runner.create_job_run(connection, job_runner.JOB_NAME, DAY)
        assert job_runner.update_job_run(connection, job_id, "processing") == 1
    buffer = StringIO()
    nightly_export.configure_logging(buffer)
    calls: list[date] = []
    outcome = nightly_export.run_nightly_export(engine, date(2026, 11, 21), tmp_path, lambda day: calls.append(day))
    assert outcome == "aborted"
    assert calls == []
    assert "nightly_export processing aborted" in buffer.getvalue()
    with engine.begin() as connection:
        rows = job_runner.query_job_runs(connection)
    assert len(rows) == 1
    assert rows[0]["status"] == "processing"


def test_two_instances_cannot_both_be_processing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    started = threading.Event()
    release = threading.Event()
    outcomes: list[str] = []
    buffer = StringIO()
    nightly_export.configure_logging(buffer)

    def slow(_day: date) -> None:
        started.set()
        assert release.wait(timeout=5)

    def first() -> None:
        outcomes.append(nightly_export.run_nightly_export(engine, DAY, tmp_path, slow))

    worker = threading.Thread(target=first)
    worker.start()
    assert started.wait(timeout=5)
    second = nightly_export.run_nightly_export(engine, DAY, tmp_path, lambda _day: outcomes.append("second-pipeline"))
    release.set()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert second == "aborted"
    assert "second-pipeline" not in outcomes
    assert outcomes == ["completed"]
    assert "aborted" in buffer.getvalue()
    rows = _rows(engine)
    assert [row["status"] for row in rows] == ["completed"]
    with engine.begin() as connection:
        assert job_runner.has_processing_lock(connection) is False


def test_processing_status_is_exclusive(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        first = job_runner.create_job_run(connection, job_runner.JOB_NAME, DAY)
        second = job_runner.create_job_run(connection, job_runner.JOB_NAME, date(2026, 11, 21))
    with engine.begin() as connection:
        assert job_runner.update_job_run(connection, first, "processing") == 1
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            job_runner.update_job_run(connection, second, "processing")
    with engine.begin() as connection:
        rows = job_runner.query_job_runs(connection)
    assert [row["status"] for row in rows] == ["processing", "pending"]


def test_pipeline_command_uses_the_milestone_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Result:
        returncode = 0
        stderr = ""
        stdout = ""

    def fake_run(args: list[str], **kwargs: object) -> Result:
        captured["args"] = args
        captured["cwd"] = kwargs.get("cwd")
        return Result()

    monkeypatch.setattr(nightly_export.subprocess, "run", fake_run)
    nightly_export.run_pipeline(DAY)
    args = captured["args"]
    assert isinstance(args, list)
    assert str(args[1]).endswith("data/pipelines/pipeline.py")
    assert args[2] == "2026-11-22"
    assert captured["cwd"] == str(ROOT)
    assert "telemetry_kpi_daily" not in " ".join(args)

    class Failed:
        returncode = 1
        stderr = "connection refused"
        stdout = ""

    monkeypatch.setattr(nightly_export.subprocess, "run", lambda *_args, **_kwargs: Failed())
    with pytest.raises(RuntimeError, match="connection refused"):
        nightly_export.run_pipeline(DAY)


def test_main_uses_target_date(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    monkeypatch.setenv("TARGET_DATE", "2026-11-18")
    monkeypatch.setattr(job_runner, "get_engine", lambda: engine)
    monkeypatch.setattr(nightly_export, "RAW_DIR", tmp_path)
    monkeypatch.setattr(nightly_export, "run_pipeline", lambda _day: None)
    buffer = StringIO()
    original_configure = nightly_export.configure_logging

    def configure(stream: object = None) -> None:
        original_configure(buffer)

    monkeypatch.setattr(nightly_export, "configure_logging", configure)
    assert nightly_export.main() == 0
    rows = _rows(engine, date(2026, 11, 18))
    assert len(rows) == 1
    assert rows[0]["status"] == "completed"
    assert (tmp_path / "telemetry_2026-11-18.csv").exists()
    assert "nightly_export completed" in buffer.getvalue()


def test_main_returns_nonzero_when_the_run_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    monkeypatch.setenv("TARGET_DATE", "2026-11-18")
    monkeypatch.setattr(job_runner, "get_engine", lambda: engine)
    monkeypatch.setattr(nightly_export, "RAW_DIR", tmp_path)

    def explode(_day: date) -> None:
        raise RuntimeError("pipeline down")

    monkeypatch.setattr(nightly_export, "run_pipeline", explode)
    nightly_export.configure_logging(StringIO())
    assert nightly_export.main() == 1
    rows = _rows(engine, date(2026, 11, 18))
    assert rows[-1]["status"] == "failed"
    assert rows[-1]["error_message"] == "pipeline down"
