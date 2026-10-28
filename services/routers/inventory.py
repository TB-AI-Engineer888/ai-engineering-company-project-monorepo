from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

_SERVICES_DIR = Path(__file__).resolve().parents[1]
_API_DIR = _SERVICES_DIR / "api"
for _path in (str(_SERVICES_DIR), str(_API_DIR)):
    if _path not in sys.path:
        sys.path.append(_path)

from database import get_db
from deps import get_current_user
from inventory_stock import current_stock, stock_by_supply_id, to_supply_read
from models import MedicalSupply, SupplyConsumption, SupplyDelivery
from schemas import (
    InventoryOrderRead,
    MedicalSupplyCreate,
    MedicalSupplyRead,
    MedicalSupplySummary,
    SupplyConsumptionCreate,
    SupplyConsumptionRead,
    SupplyDeliveryCreate,
    SupplyDeliveryRead,
)

inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])


def _require_uuid(user: dict) -> str:
    user_uuid = user.get("uuid")
    if not user_uuid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return str(user_uuid)


def _get_supply(session: Session, supply_id: int) -> MedicalSupply:
    supply = session.get(MedicalSupply, supply_id)
    if supply is None:
        raise HTTPException(status_code=404, detail="Medical supply not found")
    return supply


def _supply_summary(supply: MedicalSupply) -> MedicalSupplySummary:
    return MedicalSupplySummary(
        id=supply.id,
        name=supply.name,
        sku=supply.sku,
        category=supply.category,
        unit=supply.unit,
        country=supply.country,
    )


@inventory_router.get("/products", response_model=list[MedicalSupplyRead])
def list_products(
    _: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[MedicalSupplyRead]:
    supplies = session.exec(select(MedicalSupply).order_by(MedicalSupply.id)).all()
    stocks = stock_by_supply_id(session)
    return [
        MedicalSupplyRead(**to_supply_read(supply, stocks.get(supply.id or 0, 0)))
        for supply in supplies
    ]


@inventory_router.post("/products", response_model=MedicalSupplyRead, status_code=201)
def create_product(
    body: MedicalSupplyCreate,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> MedicalSupplyRead:
    _require_uuid(user)
    existing = session.exec(select(MedicalSupply).where(MedicalSupply.sku == body.sku)).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail=f"SKU '{body.sku}' is already registered")
    supply = MedicalSupply(
        name=body.name,
        sku=body.sku,
        category=body.category,
        unit=body.unit,
        country=body.country,
    )
    session.add(supply)
    session.commit()
    session.refresh(supply)
    return MedicalSupplyRead(**to_supply_read(supply, 0))


@inventory_router.get("/products/{supply_id}", response_model=MedicalSupplyRead)
def read_product(
    supply_id: int,
    _: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> MedicalSupplyRead:
    supply = _get_supply(session, supply_id)
    return MedicalSupplyRead(**to_supply_read(supply, current_stock(session, supply_id)))


@inventory_router.post("/orders/inbound", response_model=SupplyDeliveryRead, status_code=201)
def create_inbound_order(
    body: SupplyDeliveryCreate,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SupplyDeliveryRead:
    user_uuid = _require_uuid(user)
    _get_supply(session, body.supply_id)
    delivery = SupplyDelivery(
        supply_id=body.supply_id,
        quantity=body.quantity,
        vendor_name=body.vendor_name,
        clinic_id=body.clinic_id,
        user_uuid=user_uuid,
    )
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    return SupplyDeliveryRead(
        id=delivery.id,
        supply_id=delivery.supply_id,
        quantity=delivery.quantity,
        vendor_name=delivery.vendor_name,
        clinic_id=delivery.clinic_id,
        created_at=delivery.created_at,
        user_uuid=delivery.user_uuid,
    )


@inventory_router.post("/orders/outbound", response_model=SupplyConsumptionRead, status_code=201)
def create_outbound_order(
    body: SupplyConsumptionCreate,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SupplyConsumptionRead:
    user_uuid = _require_uuid(user)
    supply = _get_supply(session, body.supply_id)
    available = current_stock(session, body.supply_id)
    if body.quantity > available:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient stock for supply '{supply.name}'. "
                f"Available: {available}, requested: {body.quantity}."
            ),
        )
    consumption = SupplyConsumption(
        supply_id=body.supply_id,
        quantity=body.quantity,
        consumption_type=body.consumption_type,
        clinic_id=body.clinic_id,
        user_uuid=user_uuid,
    )
    session.add(consumption)
    session.commit()
    session.refresh(consumption)
    return SupplyConsumptionRead(
        id=consumption.id,
        supply_id=consumption.supply_id,
        quantity=consumption.quantity,
        consumption_type=consumption.consumption_type,
        clinic_id=consumption.clinic_id,
        created_at=consumption.created_at,
        user_uuid=consumption.user_uuid,
    )


@inventory_router.get("/orders", response_model=list[InventoryOrderRead])
def list_orders(
    _: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[InventoryOrderRead]:
    deliveries = session.exec(
        select(SupplyDelivery)
        .options(selectinload(SupplyDelivery.supply))
        .order_by(SupplyDelivery.created_at, SupplyDelivery.id)
    ).all()
    consumptions = session.exec(
        select(SupplyConsumption)
        .options(selectinload(SupplyConsumption.supply))
        .order_by(SupplyConsumption.created_at, SupplyConsumption.id)
    ).all()

    orders: list[InventoryOrderRead] = []
    for delivery in deliveries:
        if delivery.supply is None:
            continue
        orders.append(
            InventoryOrderRead(
                order_kind="inbound",
                id=delivery.id,
                supply_id=delivery.supply_id,
                quantity=delivery.quantity,
                clinic_id=delivery.clinic_id,
                created_at=delivery.created_at,
                user_uuid=delivery.user_uuid,
                vendor_name=delivery.vendor_name,
                consumption_type=None,
                supply=_supply_summary(delivery.supply),
            )
        )
    for consumption in consumptions:
        if consumption.supply is None:
            continue
        orders.append(
            InventoryOrderRead(
                order_kind="outbound",
                id=consumption.id,
                supply_id=consumption.supply_id,
                quantity=consumption.quantity,
                clinic_id=consumption.clinic_id,
                created_at=consumption.created_at,
                user_uuid=consumption.user_uuid,
                vendor_name=None,
                consumption_type=consumption.consumption_type,
                supply=_supply_summary(consumption.supply),
            )
        )
    orders.sort(key=lambda row: (row.created_at, row.order_kind, row.id))
    return orders
