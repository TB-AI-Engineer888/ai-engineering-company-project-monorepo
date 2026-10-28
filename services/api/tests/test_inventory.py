from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
API_DIR = ROOT / "services" / "api"
load_dotenv(API_DIR / ".env")

sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(API_DIR))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _auth_headers(email: str) -> dict[str, str]:
    client.post(
        "/users",
        json={"email": email, "password": "correct-horse", "name": "Inventory Tester"},
    )
    response = client.post("/auth/login", json={"email": email, "password": "correct-horse"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_inventory_requires_authentication() -> None:
    assert client.get("/inventory/products").status_code == 401
    assert client.get("/inventory/orders").status_code == 401


def test_seeded_products_include_country_and_computed_stock() -> None:
    headers = _auth_headers("seed-check@healthcore.test")
    response = client.get("/inventory/products", headers=headers)
    assert response.status_code == 200
    rows = {item["sku"]: item for item in response.json()}
    assert rows["HCR-PPE-001"]["country"] == "US"
    assert rows["HCR-PPE-002"]["country"] == "UK"
    assert rows["HCR-PPE-001"]["current_stock"] == 55
    assert rows["HCR-PPE-002"]["current_stock"] == 17
    assert rows["HCR-WND-001"]["current_stock"] == 11
    assert rows["HCR-DIAG-001"]["current_stock"] == 12
    assert rows["HCR-DIAG-002"]["current_stock"] == 10
    assert rows["HCR-MED-001"]["current_stock"] == 18


def test_invalid_consumption_type_is_rejected() -> None:
    headers = _auth_headers("type-check@healthcore.test")
    products = client.get("/inventory/products", headers=headers).json()
    supply_id = next(item["id"] for item in products if item["sku"] == "HCR-MED-001")
    response = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 1,
            "consumption_type": "lost",
            "clinic_id": 1,
        },
    )
    assert response.status_code == 422


def test_outbound_over_stock_is_rejected_before_write() -> None:
    headers = _auth_headers("overstock@healthcore.test")
    products = {
        item["sku"]: item for item in client.get("/inventory/products", headers=headers).json()
    }
    saline = products["HCR-MED-001"]
    before = client.get("/inventory/orders", headers=headers).json()
    response = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={
            "supply_id": saline["id"],
            "quantity": saline["current_stock"] + 5,
            "consumption_type": "clinical_use",
            "clinic_id": 4,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == (
        f"Insufficient stock for supply '{saline['name']}'. "
        f"Available: {saline['current_stock']}, requested: {saline['current_stock'] + 5}."
    )
    after = client.get("/inventory/orders", headers=headers).json()
    assert len(after) == len(before)


def test_orders_store_tinydb_user_uuid() -> None:
    headers = _auth_headers("uuid-check@healthcore.test")
    me = client.get("/users", headers=headers).json()
    tester = next(row for row in me if row["email"] == "uuid-check@healthcore.test")
    assert tester["uuid"]
    created_supply = client.post(
        "/inventory/products",
        headers=headers,
        json={
            "name": "Alcohol prep pad",
            "sku": "HCR-TEST-UUID",
            "category": "consumables",
            "unit": "box",
            "country": "US",
        },
    )
    assert created_supply.status_code in {201, 400}
    products = {
        item["sku"]: item for item in client.get("/inventory/products", headers=headers).json()
    }
    created = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": products["HCR-TEST-UUID"]["id"],
            "quantity": 2,
            "vendor_name": "Bound Tree Medical",
            "clinic_id": 6,
        },
    )
    assert created.status_code == 201
    assert created.json()["user_uuid"] == tester["uuid"]
    assert created.json()["clinic_id"] == 6
