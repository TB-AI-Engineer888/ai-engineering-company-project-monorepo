from __future__ import annotations

import sys
from pathlib import Path

from sqlmodel import Session, select

_SERVICES_DIR = Path(__file__).resolve().parent
_API_DIR = _SERVICES_DIR / "api"
for _path in (str(_SERVICES_DIR), str(_API_DIR)):
    if _path not in sys.path:
        sys.path.append(_path)

from inventory_stock import current_stock
from models import MedicalSupply, SupplyConsumption, SupplyDelivery
from users import Role, create_user, get_user_by_email


SEED_SUPPLIES = [
    {
        "name": "Nitrile gloves (box of 100)",
        "sku": "HCR-PPE-001",
        "category": "ppe",
        "unit": "box",
        "country": "US",
    },
    {
        "name": "Surgical mask (pack of 50)",
        "sku": "HCR-PPE-002",
        "category": "ppe",
        "unit": "pack",
        "country": "UK",
    },
    {
        "name": "Adhesive wound dressing",
        "sku": "HCR-WND-001",
        "category": "wound_care",
        "unit": "box",
        "country": "US",
    },
    {
        "name": "Rapid strep test kit",
        "sku": "HCR-DIAG-001",
        "category": "diagnostics",
        "unit": "unit",
        "country": "US",
    },
    {
        "name": "Blood glucose test strips (50)",
        "sku": "HCR-DIAG-002",
        "category": "diagnostics",
        "unit": "box",
        "country": "UK",
    },
    {
        "name": "0.9% Saline solution 500ml",
        "sku": "HCR-MED-001",
        "category": "medications",
        "unit": "vial",
        "country": "US",
    },
]

SEED_DELIVERIES = [
    {"sku": "HCR-PPE-001", "quantity": 40, "vendor_name": "MedLine Industries", "clinic_id": 1},
    {"sku": "HCR-PPE-001", "quantity": 25, "vendor_name": "Bound Tree Medical", "clinic_id": 3},
    {"sku": "HCR-PPE-002", "quantity": 20, "vendor_name": "Cardinal Health UK", "clinic_id": 10},
    {"sku": "HCR-WND-001", "quantity": 15, "vendor_name": "MedLine Industries", "clinic_id": 2},
    {"sku": "HCR-DIAG-001", "quantity": 12, "vendor_name": "Bound Tree Medical", "clinic_id": 5},
    {"sku": "HCR-DIAG-002", "quantity": 10, "vendor_name": "Cardinal Health UK", "clinic_id": 11},
    {"sku": "HCR-MED-001", "quantity": 18, "vendor_name": "MedLine Industries", "clinic_id": 4},
]

SEED_CONSUMPTIONS = [
    {"sku": "HCR-PPE-001", "quantity": 10, "consumption_type": "clinical_use", "clinic_id": 1},
    {"sku": "HCR-PPE-002", "quantity": 3, "consumption_type": "expiry_waste", "clinic_id": 10},
    {"sku": "HCR-WND-001", "quantity": 4, "consumption_type": "clinical_use", "clinic_id": 2},
]


def _seed_user_uuid() -> str:
    user = get_user_by_email("inventory.admin@healthcore.test")
    if user is None:
        user = create_user(
            "inventory.admin@healthcore.test",
            "healthcore-inventory-seed",
            Role.admin,
        )
    user_uuid = user.get("uuid")
    if not user_uuid:
        raise RuntimeError("TinyDB user is missing uuid")
    return str(user_uuid)


def seed_inventory(session: Session) -> None:
    existing = session.exec(select(MedicalSupply).where(MedicalSupply.sku == "HCR-PPE-001")).first()
    if existing is not None:
        return

    user_uuid = _seed_user_uuid()
    supplies_by_sku: dict[str, MedicalSupply] = {}
    for row in SEED_SUPPLIES:
        found = session.exec(select(MedicalSupply).where(MedicalSupply.sku == row["sku"])).first()
        if found is None:
            found = MedicalSupply(**row)
            session.add(found)
            session.flush()
        supplies_by_sku[found.sku] = found

    for row in SEED_DELIVERIES:
        supply = supplies_by_sku[row["sku"]]
        session.add(
            SupplyDelivery(
                supply_id=supply.id,
                quantity=row["quantity"],
                vendor_name=row["vendor_name"],
                clinic_id=row["clinic_id"],
                user_uuid=user_uuid,
            )
        )

    session.flush()

    for row in SEED_CONSUMPTIONS:
        supply = supplies_by_sku[row["sku"]]
        available = current_stock(session, supply.id)
        if row["quantity"] > available:
            raise RuntimeError(f"Seed consumption for {row['sku']} exceeds available stock")
        session.add(
            SupplyConsumption(
                supply_id=supply.id,
                quantity=row["quantity"],
                consumption_type=row["consumption_type"],
                clinic_id=row["clinic_id"],
                user_uuid=user_uuid,
            )
        )

    session.commit()
