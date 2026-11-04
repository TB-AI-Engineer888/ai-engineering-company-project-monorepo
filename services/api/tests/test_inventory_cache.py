from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

ROOT = Path(__file__).resolve().parents[3]
API_DIR = ROOT / "services" / "api"
load_dotenv(API_DIR / ".env")

sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(API_DIR))

import database
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

import models
from main import app
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
        json={"email": email, "password": "correct-horse", "name": "Cache Tester"},
    )
    assert created.status_code == 201
    response = client.post("/auth/login", json={"email": email, "password": "correct-horse"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_catalog_reads_are_cached_until_a_delivery_is_logged() -> None:
    _sqlite_engine()
    client = TestClient(app)
    headers = _auth_headers(client, "cache-check@healthcore.test")
    created = client.post(
        "/inventory/products",
        headers=headers,
        json={
            "name": "Alcohol prep pad",
            "sku": "HCR-CACHE-001",
            "category": "consumables",
            "unit": "box",
            "country": "US",
        },
    )
    assert created.status_code == 201

    product_calls = {"n": 0}
    order_calls = {"n": 0}
    real_products = router.load_product_rows
    real_orders = router.load_order_rows

    def count_products(session):
        product_calls["n"] += 1
        return real_products(session)

    def count_orders(session):
        order_calls["n"] += 1
        return real_orders(session)

    router.load_product_rows = count_products
    router.load_order_rows = count_orders
    try:
        first = client.get("/inventory/products", headers=headers)
        second = client.get("/inventory/products", headers=headers)
        assert first.status_code == 200
        assert second.json() == first.json()
        assert product_calls["n"] == 1

        orders_first = client.get("/inventory/orders", headers=headers)
        orders_second = client.get("/inventory/orders", headers=headers)
        assert orders_first.status_code == 200
        assert orders_second.json() == orders_first.json()
        assert order_calls["n"] == 1

        supply_id = first.json()[0]["id"]
        delivered = client.post(
            "/inventory/orders/inbound",
            headers=headers,
            json={
                "supply_id": supply_id,
                "quantity": 4,
                "vendor_name": "MedLine Industries",
                "clinic_id": 1,
            },
        )
        assert delivered.status_code == 201
        refreshed = client.get("/inventory/products", headers=headers)
        assert refreshed.status_code == 200
        assert refreshed.json()[0]["current_stock"] == 4
        assert product_calls["n"] == 2
    finally:
        router.load_product_rows = real_products
        router.load_order_rows = real_orders
        inventory_cache.clear()


def test_rejected_consumption_does_not_clear_the_catalog() -> None:
    _sqlite_engine()
    client = TestClient(app)
    headers = _auth_headers(client, "cache-reject@healthcore.test")
    created = client.post(
        "/inventory/products",
        headers=headers,
        json={
            "name": "Gauze pad",
            "sku": "HCR-CACHE-002",
            "category": "wound_care",
            "unit": "box",
            "country": "UK",
        },
    )
    assert created.status_code == 201
    listed = client.get("/inventory/products", headers=headers)
    assert listed.status_code == 200

    calls = {"n": 0}
    real_products = router.load_product_rows

    def count_products(session):
        calls["n"] += 1
        return real_products(session)

    router.load_product_rows = count_products
    try:
        again = client.get("/inventory/products", headers=headers)
        assert again.status_code == 200
        assert calls["n"] == 0
        rejected = client.post(
            "/inventory/orders/outbound",
            headers=headers,
            json={
                "supply_id": listed.json()[0]["id"],
                "quantity": 5,
                "consumption_type": "clinical_use",
                "clinic_id": 2,
            },
        )
        assert rejected.status_code == 400
        still_cached = client.get("/inventory/products", headers=headers)
        assert still_cached.json()[0]["current_stock"] == 0
        assert calls["n"] == 0
    finally:
        router.load_product_rows = real_products
        inventory_cache.clear()


def test_profile_stays_personal_and_uncached() -> None:
    _sqlite_engine()
    client = TestClient(app)
    first = _auth_headers(client, "ada-profile@healthcore.test")
    second_user = client.post(
        "/users",
        json={"email": "ben-profile@healthcore.test", "password": "correct-horse", "name": "Ben Profile"},
    )
    assert second_user.status_code == 201
    second_login = client.post(
        "/auth/login",
        json={"email": "ben-profile@healthcore.test", "password": "correct-horse"},
    )
    second = {"Authorization": f"Bearer {second_login.json()['access_token']}"}
    ada = client.get("/profiles/me", headers=first)
    ben = client.get("/profiles/me", headers=second)
    assert ada.status_code == 200
    assert ben.status_code == 200
    assert ada.json()["name"] == "Cache Tester"
    assert ben.json()["name"] == "Ben Profile"
    assert ada.json() != ben.json()
