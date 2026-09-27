from __future__ import annotations

import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services" / "api"))

from main import app  # noqa: E402

client = TestClient(app)


def test_register_login_me_and_profile_update() -> None:
    created = client.post(
        "/users",
        json={
            "email": "priya.nair@healthcore.example",
            "password": "clinic-pass-1",
            "name": "Priya Nair",
            "phone": "+44 20 7946 0000",
            "address": "London",
        },
    )
    assert created.status_code == 201
    assert created.json()["email"] == "priya.nair@healthcore.example"
    assert created.json()["profile"]["name"] == "Priya Nair"
    assert "password" not in created.text

    logged = client.post(
        "/auth/login",
        json={"email": "priya.nair@healthcore.example", "password": "clinic-pass-1"},
    )
    assert logged.status_code == 200
    token = logged.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "priya.nair@healthcore.example"
    assert me.json()["profile"]["phone"] == "+44 20 7946 0000"

    updated = client.put(
        "/profiles/me",
        headers=headers,
        json={"name": "Priya Nair", "phone": "+44 20 7946 0999", "address": "Manchester"},
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "priya.nair@healthcore.example"
    assert updated.json()["profile"]["address"] == "Manchester"
    assert updated.json()["profile"]["phone"] == "+44 20 7946 0999"


def test_register_returns_field_errors() -> None:
    response = client.post("/users", json={"email": "not-an-email", "password": "short"})
    assert response.status_code == 400
    fields = response.json()["fields"]
    assert "email" in fields
    assert "password" in fields


def test_login_failure_is_401_without_token() -> None:
    response = client.post(
        "/auth/login",
        json={"email": "missing@healthcore.example", "password": "clinic-pass-1"},
    )
    assert response.status_code == 401
    assert "token" not in response.json()


def test_invalid_token_is_401() -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_protected_analyze_clears_with_401() -> None:
    response = client.post(
        "/api/incidents/analyze",
        files={"file": ("empty.csv", io.BytesIO(b"a,b\n"), "text/csv")},
    )
    assert response.status_code == 401
