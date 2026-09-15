# HealthCore Backend Architecture Proposal

**Audience:** HealthCore Digital, James Osei (CTO)  
**Status:** Proposed  
**Scope:** Structure of the company HTTP API before the first endpoints are implemented

---

## 1. Purpose

HealthCore operates a public US website and a patient enquiry form. Engineering needs a shared backend design so the API, the public site, and a future internal backoffice use the same domains and rules.

This proposal covers:

1. Architectural pattern and rationale
2. Repository and Python package layout
3. FastAPI routers and endpoints by domain
4. How the website and API communicate (HTTP, configuration, CORS)
5. Risks if the structure is not followed

---

## 2. System context

HealthCore is an outpatient network founded in 2011 in Austin: 12 clinics (9 in Texas, Florida, and Georgia; 3 in London and Manchester), about 200 staff, and about $28M annual revenue. Dr. Sandra Okonkwo is CEO. HealthCore Digital builds internal systems. The technology team is six people in Austin, led by James Osei.

The public site (`uis/healthcore-website`) currently presents:

- Services: primary care, chronic disease, specialists, preventive health, women's health, paediatrics, mental health
- Six US clinics (Austin Central, Austin North, San Antonio, Miami, Orlando, Atlanta) with phone and hours
- A bilingual (EN/ES) patient enquiry form (`application.html`): name, date of birth, contact, preferred clinic, date and time of day, service, first visit, optional patient ID, insurance provider and member ID, health concern, consent. The form is not live booking; front desk confirms by phone.

| Capability | Current state | Backend implication |
| --- | --- | --- |
| Access | US phone booking; UK front-desk diary | 22% no-show rate; no shared online booking |
| Enquiry | Client-side form only | First API slice stores and lists enquiries, not a full EHR |
| Clinical records | Separate US and UK EHR products | Unified history is an adapter behind the data layer, not the first public API |
| Billing | US claims (14% denial); UK private pay and a small NHS contract | Pricing and denial rules belong in services, not in the website |
| Compliance | HIPAA (US) and UK GDPR | Enquiry fields are regulated data |
| Leadership | Weekly reports, several days late | No-show and denial KPIs come from one API |

First API consumers: the public site, front-desk and operations staff (internal UI), and the Austin technology team.

---

## 3. Pattern: layered architecture, one FastAPI application

**Decision:** layered architecture (presentation, application, data) as a single FastAPI application under `services/`, with routers split by HealthCore domain.

### 3.1 Rationale

The public HTML site already owns presentation. FastAPI should not render that site. Clinics, enquiries, appointments, and later claims share location and patient identity. No-show and denial rates are aggregations over those records. A six-person team can operate one API. Multiple independently deployed services would duplicate CORS, validation, and access control before the first enquiry is stored.

| Layer | Responsibility | Example | Out of scope for this layer |
| --- | --- | --- | --- |
| Presentation (routers) | Paths, status codes, request and response shapes | `POST /api/v1/enquiries` | Clinic evening-hour policy |
| Application (services) | Use cases and rules | An enquiry is not a confirmed appointment; consent is required; US vs UK residency | Raw HTTP parsing or SQL |
| Data (models / repositories) | Persistence | Save an enquiry; list clinics | Billing policy |

```text
uis/healthcore-website
        |
        |  HTTP JSON
        v
FastAPI router     (presentation)
        |
        v
Domain service     (enquiry, clinic, later claims and no-shows)
        |
        v
Repository         (store; database when persistence is introduced)
```

### 3.2 Alternatives considered

**MVC as the system pattern.** MVC assumes a View in the same process. HealthCore's View is already `uis/healthcore-website`. Path operations used as "controllers" without a service layer would embed consent, insurance, and clinic hours in HTTP handlers.

**Serverless as the system pattern.** The first API is a shared access and operations surface. Dashboard KPIs join clinics, enquiries, and later appointments and claims. Separate functions for "list Miami hours" and "submit enquiry" would duplicate models, CORS, and audit behavior. A reminder worker is appropriate after booking records exist.

**Multiple public services.** US EHR, UK EHR, and billing remain behind data-layer adapters. They are not three public HTTP APIs in the first delivery.

---

## 4. FastAPI conventions used

Layout follows FastAPI [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/):

- `app/` as a Python package
- `main.py` creates the application and includes routers; path operations are not all in `main.py`
- One `APIRouter` module per domain, included with `prefix` and `tags`
- Shared dependencies in `dependencies.py`

Configuration follows FastAPI [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/): Pydantic Settings in `app/core/config.py`, values from the environment (and optionally `.env`).

Cross-origin access follows FastAPI [CORS](https://fastapi.tiangolo.com/tutorial/cors/): origin is scheme, host, and port; `CORSMiddleware` on the API; explicit allow-list (not `"*"` with credentials).

| Convention | Application here |
| --- | --- |
| `APIRouter` and `include_router` | Routers for clinics, enquiries, appointments, patients, claims, staff, dashboard |
| Settings module | `CORS_ALLOWED_ORIGINS`, later `DATABASE_URL` |
| CORS middleware | `main.py` or `core/cors.py` |
| Thin path operations | Routers call services; access rules live in services |

---

## 5. Folders and modules

Public UI already lives at `uis/healthcore-website`. Internal operations UI belongs at `uis/backoffice`. The HTTP API belongs at `services/api`. Cross-cutting design belongs in `docs/`.

```text
├── CONTEXT.md
├── docs/
│   └── ARCHITECTURE_PROPOSAL.md
├── uis/
│   ├── healthcore-website/
│   └── backoffice/
├── services/
│   └── api/
└── docker-compose.yml
```

Separation:

1. Patient-facing UI in `uis/`. Rules and stored health data in `services/`. Shared design in `docs/`.
2. Domains: clinics, enquiries, appointments, patients, claims, staff, executive metrics.
3. Layers: routers, services, schemas, repositories. Routers do not import database drivers. Services do not import `APIRouter`.

```text
services/api/
├── pyproject.toml
├── .env.example
└── app/
    ├── __init__.py
    ├── main.py
    ├── dependencies.py
    ├── core/
    │   ├── config.py
    │   └── cors.py
    ├── routers/
    │   ├── clinics.py
    │   ├── enquiries.py
    │   ├── appointments.py
    │   ├── patients.py
    │   ├── claims.py
    │   ├── staff.py
    │   └── dashboard.py
    ├── schemas/
    ├── services/
    └── models/
```

`services/api` is its own Python project (`venv` or `uv`, `pyproject.toml`). The website does not share that environment.

---

## 6. Routers and endpoints

`main.py` includes routers, for example:

```python
app.include_router(clinics.router, prefix="/api/v1/clinics", tags=["clinics"])
```

| Router | Domain | Routes (first slice) | Service rules |
| --- | --- | --- | --- |
| `clinics.py` | Locations | `GET /`, `GET /{clinic_id}` | Hours, phone, country; public list is US clinics today |
| `enquiries.py` | Patient enquiry | `POST /`, staff `GET /`, `GET /{id}` | Consent required; not a booked slot; fields aligned with `application.html` |
| `appointments.py` | Booking | `GET /`, `POST /` when booking exists | No-show and reminders; distinct from enquiries |
| `patients.py` | Identity | Authorized `GET /{id}` | Full charts are not public |
| `claims.py` | Revenue cycle | `GET /`, `GET /{id}` | Denial status; US vs UK billing |
| `staff.py` | Workforce | Internal `GET /` | Not on the public origin |
| `dashboard.py` | KPIs | `GET /summary` | Network no-show rate, denial rate, volume by location |

`GET /health` may sit on the application object (process liveness).

Enquiry changes land in `routers/enquiries.py` and `services/enquiries.py`. Dashboard reads other services; it does not duplicate clinic schemas.

---

## 7. Website and API as separate runtimes

One git repository. Two processes.

| | `uis/healthcore-website` | `services/api` |
| --- | --- | --- |
| Stack | HTML, Tailwind CDN, `validation.js` | Python, FastAPI, Pydantic |
| Runtime | Static hosting | uvicorn / `fastapi run` |
| Knowledge | Layout, EN/ES copy, form fields | Rules, storage, later EHR adapters |
| Config | Public API base URL | Secrets, CORS origins, database URL |

The site uses HTTP JSON. Enquiry submit becomes `POST /api/v1/enquiries`.

### Configuration

Backend (`services/api/.env` untracked; `.env.example` tracked):

| Variable | Role |
| --- | --- |
| `APP_ENV` | `local` or `production` |
| `CORS_ALLOWED_ORIGINS` | Exact website and backoffice origins |
| `API_PUBLIC_URL` | Canonical API URL |
| `DATABASE_URL` | When a database is introduced |

Settings load through `app/core/config.py`. The website exposes only a public API base URL. Database and EHR credentials stay on the server.

### CORS

The website origin and the API origin differ in local development and typically in production.

1. `CORSMiddleware` uses `CORS_ALLOWED_ORIGINS`.
2. Origins are exact (scheme, host, port). Wildcard plus credentials is not used.
3. Methods match the form: `GET`, `POST`, `OPTIONS`; later `PATCH` for staff.
4. Missing `Access-Control-Allow-Origin` is an API configuration defect.

The public origin is the US marketing site. UK clinic records and GDPR access payloads are not served on that origin merely because a `patients` router exists.

---

## 8. Technical decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| HTTP framework | FastAPI | OpenAPI, Pydantic, `APIRouter` |
| Application shape | One app in `services/api` | Shared clinics and enquiries; small team |
| Isolation | Local `venv` or `uv` | Website and API interpreters stay separate |
| Validation | Pydantic schemas per domain | Enquiry without consent fails at the boundary |
| Configuration | Environment and Pydantic Settings | Origins and secrets stay out of git |
| Public UI path | `uis/healthcore-website` | Existing production site |
| Protected data | Service layer; auth dependency when added | Do not log insurance member IDs in the browser |

---

## 9. Risks

1. **All routes in `main.py`.** Domain boundaries disappear and CORS mixes with billing logic. `main.py` only constructs the app, middleware, and `include_router`.
2. **Enquiry modeled as an appointment.** Capacity and no-show metrics become wrong. `enquiries` and `appointments` stay separate routers.
3. **Rules only in `validation.js`.** Backoffice and reminder jobs would diverge. The service is authoritative; the script is UX only.
4. **CORS wildcard or CORS "fixed" in HTML.** Staff tools and protected data become unsafe or blocked. Origins come from environment variables.
5. **API code under `uis/healthcore-website`.** UI and Python tooling collide. The API stays under `services/api/`.
6. **Patient records without jurisdiction.** HIPAA and UK GDPR differ. Every patient-touching record carries clinic country; public routers expose only what the US site already collects.

---

## 10. Follow-up

When endpoints ship, update this document if a decision changes (for example, extracting a claims worker from the API process). Domain vocabulary stays aligned with `CONTEXT.md` (clinic, enquiry, claim, no-show).
