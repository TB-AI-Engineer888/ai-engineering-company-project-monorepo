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
from jose import jwt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services" / "api"))

from main import app  # noqa: E402
from security import ALGORITHM  # noqa: E402
from settings import signing_secret, telemetry_endpoint  # noqa: E402
from users import create_user  # noqa: E402

client = TestClient(app)


def test_telemetry_batch_returns_the_count() -> None:
    response = client.post(
        "/telemetry/events",
        json={
            "events": [
                {
                    "eventId": "11111111-1111-1111-1111-111111111111",
                    "timestamp": "2026-11-18T12:00:00.000Z",
                    "sessionId": None,
                    "userId": None,
                    "event_type": "login_failed",
                    "schemaVersion": 1,
                    "requestId": "22222222-2222-2222-2222-222222222222",
                    "properties": {"failure_reason": "bad_password"},
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json() == {"received": 1}
    assert telemetry_endpoint() == "http://127.0.0.1:9/telemetry/events"


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
