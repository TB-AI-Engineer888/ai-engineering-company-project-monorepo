# HealthCore inventory

The Milestone 5 API lives here.

- `routers/inventory.py` — `/inventory` routes
- `models.py` — MedicalSupply, SupplyDelivery, SupplyConsumption
- `schemas.py` — request and response models
- `database.py` — TinyDB and Supabase
- `inventory_stock.py` — computed stock
- `seed_inventory.py` — HealthCore seed records
- `api/main.py` — existing FastAPI app, inventory router registered

# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

> _Spanish version: [README.es.md](./README.es.md)._
