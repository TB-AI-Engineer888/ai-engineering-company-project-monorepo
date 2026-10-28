from __future__ import annotations

from sqlmodel import Session, col, func, select

from models import MedicalSupply, SupplyConsumption, SupplyDelivery


def current_stock(session: Session, supply_id: int) -> int:
    inbound = session.exec(
        select(func.coalesce(func.sum(SupplyDelivery.quantity), 0)).where(
            col(SupplyDelivery.supply_id) == supply_id
        )
    ).one()
    outbound = session.exec(
        select(func.coalesce(func.sum(SupplyConsumption.quantity), 0)).where(
            col(SupplyConsumption.supply_id) == supply_id
        )
    ).one()
    return int(inbound) - int(outbound)


def stock_by_supply_id(session: Session) -> dict[int, int]:
    inbound_rows = session.exec(
        select(SupplyDelivery.supply_id, func.coalesce(func.sum(SupplyDelivery.quantity), 0)).group_by(
            SupplyDelivery.supply_id
        )
    ).all()
    outbound_rows = session.exec(
        select(
            SupplyConsumption.supply_id,
            func.coalesce(func.sum(SupplyConsumption.quantity), 0),
        ).group_by(SupplyConsumption.supply_id)
    ).all()
    totals = {int(supply_id): int(total) for supply_id, total in inbound_rows}
    for supply_id, total in outbound_rows:
        totals[int(supply_id)] = totals.get(int(supply_id), 0) - int(total)
    return totals


def to_supply_read(supply: MedicalSupply, stock: int) -> dict[str, object]:
    return {
        "id": supply.id,
        "name": supply.name,
        "sku": supply.sku,
        "category": supply.category,
        "unit": supply.unit,
        "country": supply.country,
        "current_stock": stock,
    }
