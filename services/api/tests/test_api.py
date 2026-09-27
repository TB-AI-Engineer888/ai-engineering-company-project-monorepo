from __future__ import annotations

import io
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services" / "api"))

from main import app  # noqa: E402

SAMPLE = ROOT / "scripts" / "incidents-healthcore.csv"
client = TestClient(app)
PHI = re.compile(r"PAT-\d{6}", re.IGNORECASE)
_ACCOUNT = 0


def auth_headers() -> dict[str, str]:
    global _ACCOUNT
    _ACCOUNT += 1
    email = f"analyst{_ACCOUNT}@healthcore.example"
    password = "clinic-pass-1"
    created = client.post(
        "/users",
        json={"email": email, "password": password, "name": "Analyst"},
    )
    assert created.status_code == 201
    logged = client.post("/auth/login", json={"email": email, "password": password})
    assert logged.status_code == 200
    return {"Authorization": f"Bearer {logged.json()['token']}"}


def test_analyze_without_session_is_401() -> None:
    with SAMPLE.open("rb") as handle:
        response = client.post(
            "/api/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
        )
    assert response.status_code == 401


def test_analyze_sample_returns_context_metrics() -> None:
    with SAMPLE.open("rb") as handle:
        response = client.post(
            "/api/incidents/analyze",
            headers=auth_headers(),
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 100
    assert payload["valid_count"] == 94
    assert payload["invalid_count"] == 6
    assert payload["avg_satisfaction_closed"] == 3.58
    assert payload["by_status"]["CLOSED"] == 52
    assert payload["by_category"]["APPOINTMENT"] == 30
    assert payload["by_country"]["US"] == 61
    assert payload["by_country"]["UK"] == 33
    assert PHI.search(response.text) is None


def test_export_after_analyze() -> None:
    headers = auth_headers()
    with SAMPLE.open("rb") as handle:
        client.post(
            "/api/incidents/analyze",
            headers=headers,
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
        )
    response = client.get("/api/incidents/results/export", headers=headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "results.csv" in response.headers["content-disposition"]
    assert response.text.splitlines()[0] == "metric,value,percentage"
    assert "satisfaction.average,3.58" in response.text
    assert "PAT-" not in response.text


def test_empty_upload_is_400() -> None:
    response = client.post(
        "/api/incidents/analyze",
        headers=auth_headers(),
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["error"].lower()


def test_wrong_extension_is_400() -> None:
    response = client.post(
        "/api/incidents/analyze",
        headers=auth_headers(),
        files={"file": ("notes.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert response.status_code == 400
    assert "not a CSV" in response.json()["error"]


def test_missing_columns_is_400() -> None:
    response = client.post(
        "/api/incidents/analyze",
        headers=auth_headers(),
        files={"file": ("bad.csv", io.BytesIO(b"hello,world\n1,2\n"), "text/csv")},
    )
    assert response.status_code == 400
    assert "Incorrect CSV format" in response.json()["error"]
