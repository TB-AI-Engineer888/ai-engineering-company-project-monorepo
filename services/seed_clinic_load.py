from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlmodel import Session, func, select

_SERVICES_DIR = Path(__file__).resolve().parent
_API_DIR = _SERVICES_DIR / "api"
for _path in (str(_SERVICES_DIR), str(_API_DIR)):
    if _path not in sys.path:
        sys.path.append(_path)

from models import MedicalSupply, SupplyConsumption, SupplyDelivery

CATEGORIES = ("ppe", "wound_care", "diagnostics", "medications", "consumables")
UNITS = ("box", "unit", "pack", "vial")
COUNTRIES = ("US", "UK")
ITEM_NAMES = (
    "Nitrile gloves",
    "Surgical masks",
    "Gauze pads",
    "Adhesive dressings",
    "Saline vials",
    "Glucose strips",
    "Strep test kits",
    "Alcohol prep pads",
    "Elastic bandages",
    "Disposable gowns",
    "Thermometer covers",
    "Sharps containers",
)
VENDORS = (
    "MedLine Industries",
    "Bound Tree Medical",
    "Cardinal Health UK",
    "Henry Schein",
    "McKesson Medical",
)
CONSUMPTION_TYPES = ("clinical_use", "expiry_waste")
LOAD_USER = "healthcore-load-staff"
STARTED = datetime(2024, 1, 8, 13, 0, tzinfo=timezone.utc)


def load_clinic_history(
    session: Session,
    *,
    supply_count: int = 30_000,
    deliveries_per_supply: int = 5,
    consumptions_per_supply: int = 3,
) -> dict[str, int]:
    if supply_count < 1:
        raise ValueError("supply_count must be at least 1")

    before_supplies = int(session.exec(select(func.count()).select_from(MedicalSupply)).one())
    before_deliveries = int(session.exec(select(func.count()).select_from(SupplyDelivery)).one())
    before_consumptions = int(session.exec(select(func.count()).select_from(SupplyConsumption)).one())

    supplies: list[MedicalSupply] = []
    for index in range(supply_count):
        supplies.append(
            MedicalSupply(
                name=f"{ITEM_NAMES[index % len(ITEM_NAMES)]} {index + 1}",
                sku=f"HCR-LOAD-{index + 1:04d}",
                category=CATEGORIES[index % len(CATEGORIES)],
                unit=UNITS[index % len(UNITS)],
                country=COUNTRIES[index % len(COUNTRIES)],
            )
        )
    session.add_all(supplies)
    session.flush()

    deliveries: list[SupplyDelivery] = []
    consumptions: list[SupplyConsumption] = []
    for index, supply in enumerate(supplies):
        delivered = 0
        for delivery_index in range(deliveries_per_supply):
            quantity = 8 + ((index + delivery_index) % 25)
            delivered += quantity
            deliveries.append(
                SupplyDelivery(
                    supply_id=supply.id,
                    quantity=quantity,
                    vendor_name=VENDORS[(index + delivery_index) % len(VENDORS)],
                    clinic_id=(index + delivery_index) % 12 + 1,
                    created_at=STARTED + timedelta(hours=index * 3 + delivery_index),
                    user_uuid=LOAD_USER,
                )
            )
        for consumption_index in range(consumptions_per_supply):
            consumptions.append(
                SupplyConsumption(
                    supply_id=supply.id,
                    quantity=1 + ((index + consumption_index) % 4),
                    consumption_type=CONSUMPTION_TYPES[(index + consumption_index) % len(CONSUMPTION_TYPES)],
                    clinic_id=(index + consumption_index) % 12 + 1,
                    created_at=STARTED + timedelta(hours=index * 3 + deliveries_per_supply + consumption_index),
                    user_uuid=LOAD_USER,
                )
            )
        if delivered < consumptions_per_supply * 4:
            raise RuntimeError(f"Load seed would overdraw {supply.sku}")

    session.add_all(deliveries)
    session.add_all(consumptions)
    session.commit()

    after_supplies = int(session.exec(select(func.count()).select_from(MedicalSupply)).one())
    after_deliveries = int(session.exec(select(func.count()).select_from(SupplyDelivery)).one())
    after_consumptions = int(session.exec(select(func.count()).select_from(SupplyConsumption)).one())
    return {
        "supplies_before": before_supplies,
        "deliveries_before": before_deliveries,
        "consumptions_before": before_consumptions,
        "supplies_after": after_supplies,
        "deliveries_after": after_deliveries,
        "consumptions_after": after_consumptions,
    }


def _median_ms(samples: list[float]) -> float:
    ordered = sorted(samples)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


if __name__ == "__main__":
    import json
    import time
    from statistics import median

    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, create_engine

    from schemas import InventoryOrderRead, MedicalSupplyRead
    from seed_inventory import SEED_CONSUMPTIONS, SEED_DELIVERIES, SEED_SUPPLIES
    from ttl_cache import TtlCache

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "healthcore_inventory_router",
        _SERVICES_DIR / "routers" / "inventory.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def plant_small(session: Session) -> None:
        by_sku: dict[str, MedicalSupply] = {}
        for row in SEED_SUPPLIES:
            supply = MedicalSupply(**row)
            session.add(supply)
            session.flush()
            by_sku[supply.sku] = supply
        for row in SEED_DELIVERIES:
            supply = by_sku[row["sku"]]
            session.add(
                SupplyDelivery(
                    supply_id=supply.id,
                    quantity=row["quantity"],
                    vendor_name=row["vendor_name"],
                    clinic_id=row["clinic_id"],
                    user_uuid=LOAD_USER,
                )
            )
        session.flush()
        for row in SEED_CONSUMPTIONS:
            supply = by_sku[row["sku"]]
            session.add(
                SupplyConsumption(
                    supply_id=supply.id,
                    quantity=row["quantity"],
                    consumption_type=row["consumption_type"],
                    clinic_id=row["clinic_id"],
                    user_uuid=LOAD_USER,
                )
            )
        session.commit()

    def sample(session: Session, repeats: int = 15) -> dict[str, float]:
        module.load_product_rows(session)
        module.load_order_rows(session)
        product_ms: list[float] = []
        order_ms: list[float] = []
        for _ in range(repeats):
            started = time.perf_counter()
            module.load_product_rows(session)
            product_ms.append((time.perf_counter() - started) * 1000)
            started = time.perf_counter()
            module.load_order_rows(session)
            order_ms.append((time.perf_counter() - started) * 1000)
        return {
            "products_min_ms": round(min(product_ms), 2),
            "products_ms": round(median(product_ms), 2),
            "orders_min_ms": round(min(order_ms), 2),
            "orders_ms": round(median(order_ms), 2),
        }

    with Session(engine) as session:
        plant_small(session)
        small_counts = {
            "supplies": int(session.exec(select(func.count()).select_from(MedicalSupply)).one()),
            "deliveries": int(session.exec(select(func.count()).select_from(SupplyDelivery)).one()),
            "consumptions": int(session.exec(select(func.count()).select_from(SupplyConsumption)).one()),
        }
        small_ms = sample(session)
        grown = load_clinic_history(session)
        large_ms = sample(session)
        products = module.load_product_rows(session)
        orders = module.load_order_rows(session)

    cache = TtlCache()
    cache.set("inventory:products", [row.model_dump(mode="json") for row in products], 60)
    cache.set("inventory:orders", [row.model_dump(mode="json") for row in orders], 45)
    hit_products: list[float] = []
    hit_orders: list[float] = []
    for _ in range(15):
        started = time.perf_counter()
        [MedicalSupplyRead.model_validate(row) for row in cache.get("inventory:products")]
        hit_products.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        [InventoryOrderRead.model_validate(row) for row in cache.get("inventory:orders")]
        hit_orders.append((time.perf_counter() - started) * 1000)

    print(
        json.dumps(
            {
                "small_counts": small_counts,
                "small_ms": small_ms,
                "grown": grown,
                "large_ms": large_ms,
                "cache_hit_ms": {
                    "products_min_ms": round(min(hit_products), 2),
                    "products_ms": round(_median_ms(hit_products), 2),
                    "orders_min_ms": round(min(hit_orders), 2),
                    "orders_ms": round(_median_ms(hit_orders), 2),
                },
                "product_rows": len(products),
                "order_rows": len(orders),
            },
            indent=2,
        )
    )
