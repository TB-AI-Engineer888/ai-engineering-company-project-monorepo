from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SupplyCategory = Literal["ppe", "wound_care", "diagnostics", "medications", "consumables"]
SupplyUnit = Literal["box", "unit", "pack", "vial"]
SupplyCountry = Literal["US", "UK"]
ConsumptionType = Literal["clinical_use", "expiry_waste"]
OrderKind = Literal["inbound", "outbound"]


class MedicalSupplyCreate(BaseModel):
    name: str
    sku: str
    category: SupplyCategory
    unit: SupplyUnit
    country: SupplyCountry


class MedicalSupplyRead(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int


class MedicalSupplySummary(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str


class SupplyDeliveryCreate(BaseModel):
    supply_id: int
    quantity: int = Field(gt=0)
    vendor_name: str
    clinic_id: int = Field(ge=1, le=12)


class SupplyDeliveryRead(BaseModel):
    id: int
    supply_id: int
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime
    user_uuid: str


class SupplyConsumptionCreate(BaseModel):
    supply_id: int
    quantity: int = Field(gt=0)
    consumption_type: ConsumptionType
    clinic_id: int = Field(ge=1, le=12)


class SupplyConsumptionRead(BaseModel):
    id: int
    supply_id: int
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime
    user_uuid: str


class InventoryOrderRead(BaseModel):
    order_kind: OrderKind
    id: int
    supply_id: int
    quantity: int
    clinic_id: int
    created_at: datetime
    user_uuid: str
    vendor_name: str | None = None
    consumption_type: str | None = None
    supply: MedicalSupplySummary
