# Milestone — Backend: Inventory Management with ORM & Dual Database

Company: HealthCore
Path: 05-backend-inventory-orm/healthcore-BRIEFING.md

HealthCore is an outpatient healthcare services company operating 12 clinics across the USA (Texas, Florida, Georgia) and the UK (London, Manchester). Supply entries are deliveries from vendors. Supply exits are clinical consumptions logged by clinic staff. Stock is always the net of entries minus exits. Direct modification is not allowed. All routes are under /inventory. User UUIDs come from TinyDB. Access must be authenticated.

## MedicalSupply

id int PK
name str
sku str
category str: ppe, wound_care, diagnostics, medications, consumables
unit str: box, unit, pack, vial
country str: US or UK
current_stock int: computed, not stored. SUM(SupplyDelivery.quantity) - SUM(SupplyConsumption.quantity)

## SupplyDelivery

id int PK
supply_id int FK to MedicalSupply
quantity int
vendor_name str
clinic_id int 1-12, not a foreign key
created_at datetime
user_uuid str from TinyDB

## SupplyConsumption

id int PK
supply_id int FK to MedicalSupply
quantity int
consumption_type str: clinical_use or expiry_waste
clinic_id int 1-12
created_at datetime
user_uuid str from TinyDB

An outbound order that would make stock negative is rejected before it is saved, with HTTP 400 and the message: Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}.

## Seed supplies

Nitrile gloves (box of 100), HCR-PPE-001, ppe, box, US
Surgical mask (pack of 50), HCR-PPE-002, ppe, pack, UK
Adhesive wound dressing, HCR-WND-001, wound_care, box, US
Rapid strep test kit, HCR-DIAG-001, diagnostics, unit, US
Blood glucose test strips (50), HCR-DIAG-002, diagnostics, box, UK
0.9% Saline solution 500ml, HCR-MED-001, medications, vial, US
