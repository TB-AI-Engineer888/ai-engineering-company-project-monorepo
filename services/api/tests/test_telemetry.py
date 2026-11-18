from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("TINYDB_PATH", str(Path(tempfile.mkdtemp()) / "tinydb.json"))
os.environ.setdefault("SECRET_KEY", "test-signing-secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ["TELEMETRY_ENDPOINT"] = "http://127.0.0.1:9/telemetry/events"

import pytest
from fastapi.testclient import TestClient
from jose import jwt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services" / "api"))

from main import app  # noqa: E402
import telemetry_storage  # noqa: E402
from security import ALGORITHM  # noqa: E402
from settings import signing_secret, telemetry_endpoint  # noqa: E402
from users import create_user  # noqa: E402

client = TestClient(app)

LOGIN_FAILED = {
    "eventId": "11111111-1111-1111-1111-111111111111",
    "timestamp": "2026-11-18T12:00:00.000Z",
    "sessionId": None,
    "userId": None,
    "event_type": "login_failed",
    "schemaVersion": 1,
    "requestId": "22222222-2222-2222-2222-222222222222",
    "properties": {"failure_reason": "bad_password"},
}

INBOUND = {
    "eventId": "11111111-1111-4111-8111-111111111111",
    "timestamp": "2026-11-18T15:04:00Z",
    "sessionId": "44444444-4444-4444-8444-444444444444",
    "userId": "22222222-2222-4222-8222-222222222222",
    "event_type": "inbound_order_created",
    "schemaVersion": 1,
    "requestId": "33333333-3333-4333-8333-333333333333",
    "properties": {
        "clinic_id": 1,
        "country": "US",
        "product_id": 1,
        "product_category": "ppe",
        "quantity": 40,
        "order_id": 15,
        "vendor_name": "MedLine Industries",
        "sku": "HCR-PPE-001",
        "unit": "box",
        "country_mismatch": False,
    },
}


@pytest.fixture(autouse=True)
def stored_batches(monkeypatch: pytest.MonkeyPatch) -> list[list[dict]]:
    batches: list[list[dict]] = []
    monkeypatch.setattr(telemetry_storage, "insert_telemetry_rows", lambda rows: batches.append(list(rows)))
    return batches


def test_telemetry_batch_returns_the_count(stored_batches: list[list[dict]]) -> None:
    response = client.post(
        "/telemetry/events",
        json={"events": [LOGIN_FAILED]},
    )
    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}
    assert telemetry_endpoint() == "http://127.0.0.1:9/telemetry/events"
    assert stored_batches[0][0]["event_type"] == "login_failed"
    assert stored_batches[0][0]["service"] == "backoffice"
    assert stored_batches[0][0]["level"] == "warn"
    assert json.loads(stored_batches[0][0]["tags"]) == {"failure_reason": "bad_password"}


def test_mixed_batch_stores_valid_events_and_counts_rejections(stored_batches: list[list[dict]]) -> None:
    invalid = {**LOGIN_FAILED, "properties": {"failure_reason": "bad_password", "email": "ada@healthcore.test"}}
    response = client.post("/telemetry/events", json={"events": [INBOUND, invalid, "not-an-event"]})
    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 1, "rejected": 2}
    assert len(stored_batches) == 1
    stored = stored_batches[0]
    assert len(stored) == 1
    assert stored[0]["event_type"] == "inbound_order_created"
    assert stored[0]["level"] == "info"
    assert stored[0]["value"] == 40
    tags = json.loads(stored[0]["tags"])
    assert tags["country"] == "US"
    assert tags["product_category"] == "ppe"
    assert "email" not in tags


def test_telemetry_rejects_a_body_without_events() -> None:
    response = client.post("/telemetry/events", json={"event_type": "login_failed"})
    assert response.status_code == 422


def test_failed_login_keeps_one_message_and_a_reason() -> None:
    create_user("ada@healthcore.test", "correct-horse")
    response = client.post(
        "/auth/login",
        json={"email": "ada@healthcore.test", "password": "wrong-horse"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "Incorrect email or password"
    assert body["failure_reason"] == "bad_password"
    assert "ada@healthcore.test" not in response.text


def test_unknown_login_does_not_name_the_email() -> None:
    response = client.post(
        "/auth/login",
        json={"email": "missing@healthcore.test", "password": "correct-horse"},
    )
    assert response.status_code == 401
    assert response.json()["failure_reason"] == "unknown_user"
    assert "missing@healthcore.test" not in response.text


def test_expired_token_exposes_the_reason_header() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    token = jwt.encode(
        {"sub": str(user["id"]), "exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
        signing_secret(),
        algorithm=ALGORITHM,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.headers.get("x-auth-reason") == "token_expired"
    assert response.json()["error"] == "Not authenticated"
