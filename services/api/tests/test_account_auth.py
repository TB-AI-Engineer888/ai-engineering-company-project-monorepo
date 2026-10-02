from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services" / "api"))

_TMP = Path(tempfile.mkdtemp())
os.environ["AUTH_DB_PATH"] = str(_TMP / "auth.db")
os.environ["AUTH_OUTBOX_PATH"] = str(_TMP / "outbox.json")
os.environ["APP_URL"] = "http://127.0.0.1:43123"
os.environ.pop("RESEND_API_KEY", None)

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _outbox() -> list[dict]:
    path = Path(os.environ["AUTH_OUTBOX_PATH"])
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def test_forgot_password_unknown_email_is_200_and_sends_nothing() -> None:
    response = client.post("/auth/forgot-password", json={"email": "missing@healthcore.test"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert _outbox() == []
    assert "not registered" not in response.text.lower()
    assert "not found" not in response.text.lower()


def test_forgot_password_writes_reset_link_for_known_user() -> None:
    client.post(
        "/auth/register",
        json={"email": "ada@healthcore.test", "password": "correct-horse"},
    )
    response = client.post("/auth/forgot-password", json={"email": "ada@healthcore.test"})
    assert response.status_code == 200
    messages = _outbox()
    assert len(messages) == 1
    assert messages[0]["to"] == "ada@healthcore.test"
    assert messages[0]["reset_url"].startswith("http://127.0.0.1:43123/reset-password?token=")
    assert messages[0]["reset_url"] in messages[0]["text"]


def test_reset_updates_password_and_rejects_reuse_and_expiry() -> None:
    client.post(
        "/auth/register",
        json={"email": "bea@healthcore.test", "password": "correct-horse"},
    )
    client.post("/auth/forgot-password", json={"email": "bea@healthcore.test"})
    token = _outbox()[-1]["reset_url"].split("token=", 1)[1]
    updated = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "new-password"},
    )
    assert updated.status_code == 200
    reused = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "another-password"},
    )
    assert reused.status_code == 400
    old_login = client.post(
        "/auth/login",
        json={"email": "bea@healthcore.test", "password": "correct-horse"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/auth/login",
        json={"email": "bea@healthcore.test", "password": "new-password"},
    )
    assert new_login.status_code == 200

    client.post("/auth/forgot-password", json={"email": "bea@healthcore.test"})
    expired_token = _outbox()[-1]["reset_url"].split("token=", 1)[1]
    import sqlite3

    connection = sqlite3.connect(os.environ["AUTH_DB_PATH"])
    connection.execute("UPDATE password_reset_tokens SET expires_at = 1 WHERE used_at IS NULL")
    connection.commit()
    connection.close()
    expired = client.post(
        "/auth/reset-password",
        json={"token": expired_token, "new_password": "third-password"},
    )
    assert expired.status_code == 400


def test_change_password_rejects_wrong_current_password() -> None:
    registered = client.post(
        "/auth/register",
        json={"email": "cio@healthcore.test", "password": "correct-horse"},
    )
    token = registered.json()["token"]
    wrong = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "nope-nope", "new_password": "changed-pass"},
    )
    assert wrong.status_code == 400
    changed = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "correct-horse", "new_password": "changed-pass"},
    )
    assert changed.status_code == 200
    login = client.post(
        "/auth/login",
        json={"email": "cio@healthcore.test", "password": "changed-pass"},
    )
    assert login.status_code == 200


def test_resend_payload_contains_reset_link(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _urlopen(request, timeout=20):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr("account_auth.urllib.request.urlopen", _urlopen)
    client.post(
        "/auth/register",
        json={"email": "dee@healthcore.test", "password": "correct-horse"},
    )
    before = len(_outbox())
    response = client.post("/auth/forgot-password", json={"email": "dee@healthcore.test"})
    assert response.status_code == 200
    assert len(_outbox()) == before
    body = captured["body"]
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["auth"] == "Bearer re_test_key"
    assert isinstance(body, dict)
    assert body["to"] == ["dee@healthcore.test"]
    assert "http://127.0.0.1:43123/reset-password?token=" in body["text"]
    assert "http://127.0.0.1:43123/reset-password?token=" in body["html"]
