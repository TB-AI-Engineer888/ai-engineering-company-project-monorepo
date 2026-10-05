from __future__ import annotations

import io
import os
import re
import sys
import tempfile
from pathlib import Path

os.environ["TINYDB_PATH"] = str(Path(tempfile.mkdtemp()) / "tinydb.json")
os.environ.setdefault("SECRET_KEY", "test-signing-secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services" / "api"))

from main import app  # noqa: E402

SAMPLE = ROOT / "scripts" / "incidents-healthcore.csv"
client = TestClient(app)


def _token(email: str = "analyst@healthcore.test", password: str = "correct-horse") -> str:
    client.post(
        "/users",
        json={"email": email, "password": password, "name": "Analyst"},
    )
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(email: str = "analyst@healthcore.test") -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(email)}"}
PHI = re.compile(r"PAT-\d{6}", re.IGNORECASE)


def test_analyze_sample_returns_context_metrics() -> None:
    with SAMPLE.open("rb") as handle:
        response = client.post(
            "/api/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
            headers=_auth(),
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
    with SAMPLE.open("rb") as handle:
        client.post(
            "/api/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
            headers=_auth("export@healthcore.test"),
        )
    response = client.get("/api/incidents/results/export", headers=_auth("export-read@healthcore.test"))
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "results.csv" in response.headers["content-disposition"]
    assert response.text.splitlines()[0] == "metric,value,percentage"
    assert "satisfaction.average,3.58" in response.text
    assert "PAT-" not in response.text


def test_empty_upload_is_400() -> None:
    response = client.post(
        "/api/incidents/analyze",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        headers=_auth("empty@healthcore.test"),
    )
    assert response.status_code == 400
    assert "empty" in response.json()["error"].lower()


def test_wrong_extension_is_400() -> None:
    response = client.post(
        "/api/incidents/analyze",
        files={"file": ("notes.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        headers=_auth("pdf@healthcore.test"),
    )
    assert response.status_code == 400
    assert "not a CSV" in response.json()["error"]


def test_missing_columns_is_400() -> None:
    response = client.post(
        "/api/incidents/analyze",
        files={"file": ("bad.csv", io.BytesIO(b"hello,world\n1,2\n"), "text/csv")},
        headers=_auth("bad@healthcore.test"),
    )
    assert response.status_code == 400
    assert "Incorrect CSV format" in response.json()["error"]


def test_auth_flow_and_route_protection() -> None:
    denied = client.get("/api/incidents/results")
    assert denied.status_code == 401

    malformed = client.get("/api/incidents/results", headers={"Authorization": "Bearer not-a-token"})
    assert malformed.status_code == 401

    registered = client.post(
        "/users",
        json={
            "email": "owner@healthcore.test",
            "password": "owner-pass",
            "name": "Owner",
            "phone": "555-0100",
            "address": "Austin",
            "role": "admin",
        },
    )
    assert registered.status_code == 201
    assert registered.json()["role"] == "user"
    assert "hashed_password" not in registered.json()
    assert registered.json()["profile"]["name"] == "Owner"

    other = client.post(
        "/users",
        json={"email": "other@healthcore.test", "password": "other-pass", "name": "Other"},
    )
    assert other.status_code == 201
    other_id = other.json()["id"]

    login = client.post("/auth/login", json={"email": "owner@healthcore.test", "password": "owner-pass"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "owner@healthcore.test"
    assert me.json()["profile"]["phone"] == "555-0100"

    forbidden = client.put(f"/users/{other_id}", json={"email": "taken@healthcore.test"}, headers=headers)
    assert forbidden.status_code == 403

    profile = client.put("/profiles/me", json={"name": "Owner Updated"}, headers=headers)
    assert profile.status_code == 200
    assert profile.json()["name"] == "Owner Updated"

    stored = client.get("/users", headers=headers)
    assert stored.status_code == 200
    assert all("hashed_password" not in row for row in stored.json())

    form_login = client.post(
        "/auth/login",
        data={"username": "owner@healthcore.test", "password": "owner-pass"},
    )
    assert form_login.status_code == 200
    assert form_login.json()["token_type"] == "bearer"

    for path in ("/", "/api/incidents/sample", "/api/incidents/results", "/api/incidents/results/export"):
        assert client.get(path).status_code == 401
    assert client.post("/api/incidents/analyze").status_code == 401
    assert client.get("/health").status_code == 200
