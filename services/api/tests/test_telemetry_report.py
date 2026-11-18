from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("TINYDB_PATH", str(Path(tempfile.mkdtemp()) / "tinydb.json"))
os.environ.setdefault("SECRET_KEY", "test-signing-secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ["TELEMETRY_ENDPOINT"] = "http://127.0.0.1:9/telemetry/events"

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "services" / "api"))

from main import app  # noqa: E402
from telemetry import analysis, report  # noqa: E402

client = TestClient(app)


def test_report_defaults_to_seven_days(monkeypatch) -> None:
    seen: list[tuple[datetime, datetime]] = []

    def capture(start_date: datetime, end_date: datetime) -> list[dict]:
        seen.append((start_date, end_date))
        return []

    monkeypatch.setattr(analysis, "events_per_day", capture)
    monkeypatch.setattr(analysis, "error_rate_by_type", capture)
    monkeypatch.setattr(analysis, "latency_per_day", capture)
    monkeypatch.setattr(analysis, "auth_failure_rate", capture)
    report.clear_cache()

    response = client.get("/telemetry/report")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"period", "metrics"}
    assert set(body["metrics"]) == {
        "events_per_day",
        "error_rate_by_type",
        "latency_per_day",
        "auth_failure_rate",
    }
    start, end = seen[0]
    assert end - start == timedelta(days=7)
    assert start.tzinfo is not None and end.tzinfo is not None
    assert body["period"]["from"].endswith("Z")
    assert body["period"]["to"].endswith("Z")


def test_report_cache_skips_a_second_calculation(monkeypatch) -> None:
    calls = {"n": 0}

    def counting(start_date: datetime, end_date: datetime) -> list[dict]:
        calls["n"] += 1
        return [{"date": "2026-11-18", "event_type": "login_failed", "event_count": 4}]

    monkeypatch.setattr(analysis, "events_per_day", counting)
    monkeypatch.setattr(analysis, "error_rate_by_type", lambda start_date, end_date: [])
    monkeypatch.setattr(analysis, "latency_per_day", lambda start_date, end_date: [])
    monkeypatch.setattr(analysis, "auth_failure_rate", lambda start_date, end_date: [])
    report.clear_cache()

    params = {"start_date": "2026-11-11T00:00:00Z", "end_date": "2026-11-18T00:00:00Z"}
    first = client.get("/telemetry/report", params=params)
    second = client.get("/telemetry/report", params=params)
    assert first.status_code == 200
    assert second.json() == first.json()
    assert calls["n"] == 1

    later = client.get(
        "/telemetry/report",
        params={"start_date": "2026-11-12T00:00:00Z", "end_date": "2026-11-18T00:00:00Z"},
    )
    assert later.status_code == 200
    assert calls["n"] == 2


def test_report_rejects_a_single_bound() -> None:
    response = client.get("/telemetry/report", params={"start_date": "2026-11-11T00:00:00Z"})
    assert response.status_code == 422


def test_report_rejects_an_inverted_window() -> None:
    response = client.get(
        "/telemetry/report",
        params={"start_date": "2026-11-18T00:00:00Z", "end_date": "2026-11-11T00:00:00Z"},
    )
    assert response.status_code == 422
