from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MedicalSupply(SQLModel, table=True):
    __tablename__ = "medical_supplies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: str = Field(index=True, unique=True)
    category: str
    unit: str
    country: str

    deliveries: List["SupplyDelivery"] = Relationship(back_populates="supply")
    consumptions: List["SupplyConsumption"] = Relationship(back_populates="supply")


class SupplyDelivery(SQLModel, table=True):
    __tablename__ = "supply_deliveries"

    id: Optional[int] = Field(default=None, primary_key=True)
    supply_id: int = Field(foreign_key="medical_supplies.id")
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime = Field(default_factory=_utc_now)
    user_uuid: str

    supply: Optional[MedicalSupply] = Relationship(back_populates="deliveries")


class SupplyConsumption(SQLModel, table=True):
    __tablename__ = "supply_consumptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    supply_id: int = Field(foreign_key="medical_supplies.id")
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime = Field(default_factory=_utc_now)
    user_uuid: str

    supply: Optional[MedicalSupply] = Relationship(back_populates="consumptions")
