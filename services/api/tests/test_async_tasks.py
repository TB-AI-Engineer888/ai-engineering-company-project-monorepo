from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

ROOT = Path(__file__).resolve().parents[3]
API_DIR = ROOT / "services" / "api"
load_dotenv(API_DIR / ".env")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(API_DIR))

import database
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

import models
from main import app
from models import DeadLetterTask, MedicalSupply, SupplyDelivery
from services.celery_app import (
    enqueue_order_list,
    load_inventory_orders,
    read_task,
    retry_countdown,
)
from ttl_cache import inventory_cache

router = sys.modules["healthcore_inventory_router"]


def _sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database._engine = engine
    SQLModel.metadata.create_all(engine)
    inventory_cache.clear()
    return engine


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    created = client.post(
        "/users",
        json={"email": email, "password": "correct-horse", "name": "Queue Tester"},
    )
    assert created.status_code == 201
    response = client.post("/auth/login", json={"email": email, "password": "correct-horse"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_retry_countdown_increases_and_is_not_immediate() -> None:
    assert load_inventory_orders.max_retries == 3
    assert load_inventory_orders.acks_late is True
    assert retry_countdown(0) == 1
    assert retry_countdown(1) == 2
    assert retry_countdown(2) == 4
    assert retry_countdown(0) < retry_countdown(1) < retry_countdown(2)


def test_message_contains_only_the_order_reference(monkeypatch) -> None:
    seen: dict[str, tuple] = {}

    class _Result:
        id = "task-1"

    def delay(reference: str) -> _Result:
        seen["args"] = (reference,)
        return _Result()

    monkeypatch.setattr(load_inventory_orders, "delay", delay)
    assert enqueue_order_list() == "task-1"
    assert seen["args"] == ("inventory:orders",)


def test_orders_endpoint_returns_task_id_without_the_rows(monkeypatch) -> None:
    monkeypatch.setattr(router, "enqueue_order_list", lambda: "task-123")
    client = TestClient(app)
    headers = _auth_headers(client, "orders-async@healthcore.test")
    response = client.get("/inventory/orders", headers=headers)
    assert response.status_code == 202
    assert response.json() == {"task_id": "task-123"}


def test_task_status_uses_celery_state_names(monkeypatch) -> None:
    class _Result:
        def __init__(self, state: str, result):
            self.state = state
            self.result = result

    states = {
        "pending-id": _Result("PENDING", None),
        "started-id": _Result("STARTED", None),
        "success-id": _Result("SUCCESS", [{"id": 7}]),
        "failure-id": _Result("FAILURE", RuntimeError("db down")),
    }

    def fake_result(task_id: str, app=None):
        return states[task_id]

    monkeypatch.setattr("services.celery_app.AsyncResult", fake_result)
    assert read_task("pending-id") == {"task_id": "pending-id", "status": "pending", "result": None}
    assert read_task("started-id") == {"task_id": "started-id", "status": "started", "result": None}
    assert read_task("success-id") == {"task_id": "success-id", "status": "success", "result": [{"id": 7}]}
    assert read_task("failure-id") == {"task_id": "failure-id", "status": "failure", "result": None}

    client = TestClient(app)
    headers = _auth_headers(client, "task-status@healthcore.test")

    def fake_read(task_id: str) -> dict:
        return {"task_id": task_id, "status": "success", "result": [{"id": 7}]}

    monkeypatch.setattr("services.celery_app.read_task", fake_read)
    response = client.get("/tasks/success-id", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"task_id": "success-id", "status": "success", "result": [{"id": 7}]}
    assert client.get("/tasks/success-id").status_code == 401


def test_order_task_reads_the_database_and_logs_the_result(caplog) -> None:
    engine = _sqlite_engine()
    with Session(engine) as session:
        supply = MedicalSupply(
            name="Gauze",
            sku="HCR-ASYNC-001",
            category="wound_care",
            unit="box",
            country="US",
        )
        session.add(supply)
        session.commit()
        session.refresh(supply)
        session.add(
            SupplyDelivery(
                supply_id=supply.id,
                quantity=3,
                vendor_name="MedLine",
                clinic_id=1,
                user_uuid="user-1",
            )
        )
        session.commit()

    load_inventory_orders.push_request(id="task-ok", retries=0)
    try:
        with caplog.at_level(logging.INFO, logger="healthcore.tasks"):
            rows = load_inventory_orders.run("inventory:orders")
    finally:
        load_inventory_orders.pop_request()

    assert rows[0]["supply"]["sku"] == "HCR-ASYNC-001"
    assert rows[0]["quantity"] == 3
    assert "task_id=task-ok" in caplog.text
    assert "attempt=1" in caplog.text
    assert "status=success" in caplog.text
    assert "duration_ms=" in caplog.text


def test_exhausted_retries_are_stored_in_the_dead_letter_table(caplog) -> None:
    engine = _sqlite_engine()
    load_inventory_orders.push_request(id="task-dead", retries=3)
    try:
        with caplog.at_level(logging.ERROR, logger="healthcore.tasks"):
            with pytest.raises(ValueError, match="Unknown reference"):
                load_inventory_orders.run("missing-reference")
    finally:
        load_inventory_orders.pop_request()

    with Session(engine) as session:
        row = session.exec(select(DeadLetterTask)).one()
    assert row.task_id == "task-dead"
    assert row.attempt_number == 4
    assert "Unknown reference: missing-reference" in row.error
    assert row.timestamp is not None
    assert "task_id=task-dead" in caplog.text
    assert "attempt=4" in caplog.text
    assert "status=failure" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "Unknown reference: missing-reference" in caplog.text
