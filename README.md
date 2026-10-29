# Frontend Performance Audit

Search for **Frontend Performance Audit**. The deliverables are on `main`:

| What | Where |
| --- | --- |
| Initial scores and root causes | [AUDIT.md](./AUDIT.md) |
| Corrections and before/after scores | [REPORT.md](./REPORT.md) |
| Lighthouse screenshots | [audit/before](./audit/before) and [audit/after](./audit/after) |

The public site is `uis/healthcore-website`. The backoffice is `uis/backoffice`. The shared field added for this audit is `uis/backoffice/src/components/form-field.tsx`.

---

# Milestone — Backend: Inventory Management with ORM & Dual Database

https://github.com/TB-AI-Engineer888/ai-engineering-company-project-monorepo

Company: HealthCore. This is the project.

| What | Where |
| --- | --- |
| Briefing | `05-backend-inventory-orm/healthcore-BRIEFING.md` |
| Routes, all under `/inventory` | `services/routers/inventory.py` |
| Tables: MedicalSupply, SupplyDelivery, SupplyConsumption | `services/models.py` |
| Request and response schemas | `services/schemas.py` |
| TinyDB for login, Supabase for inventory | `services/database.py` |
| Stock math | `services/inventory_stock.py` |
| Seed data | `services/seed_inventory.py` |
| App entry | `services/api/main.py` |
| Medical supplies page | `uis/backoffice` route `/backoffice/inventory/products` |
| Delivery form | `/backoffice/inventory/orders/inbound` |
| Consumption form | `/backoffice/inventory/orders/outbound` |
| Order history | `/backoffice/inventory/orders` |

Routes: `GET /inventory/products`, `POST /inventory/products`, `GET /inventory/products/{id}`, `POST /inventory/orders/inbound`, `POST /inventory/orders/outbound`, `GET /inventory/orders`.

Stock is deliveries minus consumptions. It is not stored. Login stays in TinyDB. Inventory stays in Supabase.

---

# AI Engineering Company Project — Student Template

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

_Base template for transversal projects in the AI Engineering Career Program — 4Geeks Academy._

> _Instrucciones disponibles en español en [README.es.md](./README.es.md)._

---

## Purpose

This repository is the **starter template** for transversal projects. You will work on real company scenarios (Brasaland, TrackFlow, Nexova), building deliverables that map to course milestones (Web, Programming, Backend, Telemetry, RAG, Agents, Workflows, Real-time).

- Create a template from this repository.
- Replace the placeholder `CONTEXT.md` with your assigned company context.
- Use `skills/` and the directory-level `README.md` files as working guidance.

---

## Current status of the template

The repository currently provides a **base folder structure and documentation skeleton**. It does not include runnable apps or global scripts yet.

- `CONTEXT.md` is a placeholder and must be replaced with your assigned company context.
- There is no root `AGENTS.md` yet.
- Shared package metadata exists in `packages/shared/package.json` (`@repo/shared-types`), but no workspace runner is configured at root.

---

## Repository structure

```text
ai-engineering-company-project-monorepo/
├── README.md
├── README.es.md
├── CONTEXT.md                # Placeholder to be replaced with assigned context
├── agents/                   # Agent patterns/templates and tools docs
├── data/                     # raw, process, pipelines, eval
├── docs/                     # Project and architecture documentation
├── infra/                    # Docker, Terraform, deployment configs
├── internal/                 # CLIs, packaged migration scripts, internal utilities
├── mcps/                     # Model Context Protocol (MCP) Servers
├── packages/
│   └── shared/               # Shared package (@repo/shared-types)
├── scripts/                  # Script conventions/documentation
├── services/                 # APIs and background workers
├── shared/                   # Shared assets/conventions at repo level
├── skills/                   # Reusable agent skills
├── uis/                      # User interfaces (React, Next.js, Streamlit, HTML)
└── workflows/                # Automation/orchestration documentation
```

---

## How to start

1. **Use this repository as a template** and create your own project repo.
2. **Clone** your repository (or open it in Codespaces).
3. **Replace** `CONTEXT.md` with the full context for your assigned company.
4. **Review** each top-level folder `README.md` to understand intended responsibilities (`uis/`, `services/`, `data/`, `skills/`, etc.).
5. **Start implementing** milestone deliverables in `uis/` and `services/`, reusing `packages/shared/` and `data/` as needed.

---

## Milestones (reference)

| Milestone | Focus        | Typical deliverables                        |
| --------- | ------------ | ------------------------------------------- |
| 0         | Prework      | Environment setup, first prompts            |
| 1         | Web          | Corporate website, forms, SEO               |
| 2         | Programming  | Business logic, scoring, calculations       |
| 3         | AI-driven UI | AI-generated interfaces                     |
| 4         | Next.js      | Portals, loyalty app, operations UI         |
| 5         | Backend      | Central API (locations, menus, sales, etc.) |
| 6         | Telemetry    | Data pipeline, dashboards                   |
| 7         | RAG & Memory | Semantic knowledge base, search             |
| 8         | Agents       | Support, onboarding, training agents        |
| 9         | Workflows    | n8n automations                             |
| 10        | Real-time    | Live dashboards, alerts, streaming          |

---

## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

This template was built as part of the 4Geeks Academy AI Engineering Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) and [@alezanchezr](https://x.com/alesanchezr) and many other contributors. Find out more about our [AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering), and [other courses](https://4geeksacademy.com/en/program-comparison).

You can find other templates and resources like this at the [4Geeks Academy GitHub page](https://github.com/4geeksacademy).

_This template is maintained by 4Geeks Academy for the AI Engineering track. For exclusive use in the programme._
