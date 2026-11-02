from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("TINYDB_PATH", str(Path(tempfile.mkdtemp()) / "tinydb.json"))
os.environ.setdefault("SECRET_KEY", "test-signing-secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services" / "api"))

from main import app

client = TestClient(app)

JSON_SUCCESS = {
    ("GET", "/"),
    ("GET", "/health"),
    ("POST", "/users"),
    ("GET", "/users"),
    ("GET", "/users/{user_id}"),
    ("PUT", "/users/{user_id}"),
    ("DELETE", "/users/{user_id}"),
    ("GET", "/profiles/me"),
    ("PUT", "/profiles/me"),
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("GET", "/inventory/products"),
    ("POST", "/inventory/products"),
    ("GET", "/inventory/products/{supply_id}"),
    ("POST", "/inventory/orders/inbound"),
    ("POST", "/inventory/orders/outbound"),
    ("GET", "/inventory/orders"),
    ("POST", "/api/incidents/analyze"),
    ("GET", "/api/incidents/results"),
}

CSV_SUCCESS = {
    ("GET", "/api/incidents/sample"),
    ("GET", "/api/incidents/results/export"),
}


def test_every_route_declares_a_success_schema() -> None:
    spec = app.openapi()
    seen: set[tuple[str, str]] = set()
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            key = (method.upper(), path)
            seen.add(key)
            responses = operation.get("responses", {})
            success = responses.get("200") or responses.get("201")
            assert success is not None, f"{key} has no 200/201 response"
            content = success.get("content", {})
            assert content, f"{key} has no response content"
            if key in CSV_SUCCESS:
                assert "text/csv" in content, f"{key} should publish text/csv"
            else:
                assert "application/json" in content, f"{key} should publish application/json"
                schema = content["application/json"].get("schema") or {}
                assert schema, f"{key} is missing a JSON schema"
    assert JSON_SUCCESS | CSV_SUCCESS <= seen


def test_register_and_login_do_not_echo_email() -> None:
    registered = client.post(
        "/users",
        json={"email": "schema@healthcore.test", "password": "correct-horse", "name": "Schema"},
    )
    assert registered.status_code == 201
    body = registered.json()
    assert "email" not in body
    assert "hashed_password" not in body
    assert body["role"] == "user"

    login = client.post("/auth/login", json={"email": "schema@healthcore.test", "password": "correct-horse"})
    assert login.status_code == 200
    token = login.json()
    assert set(token) == {"access_token", "token_type"}
    assert "email" not in token

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "schema@healthcore.test"
    assert "hashed_password" not in me.json()


def test_user_list_is_a_flat_projection() -> None:
    client.post("/users", json={"email": "list@healthcore.test", "password": "correct-horse", "name": "List"})
    login = client.post("/auth/login", json={"email": "list@healthcore.test", "password": "correct-horse"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    listed = client.get("/users", headers=headers)
    assert listed.status_code == 200
    for row in listed.json():
        assert set(row) == {"id", "role", "uuid"}
