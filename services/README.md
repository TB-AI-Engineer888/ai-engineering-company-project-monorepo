# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

> _Spanish version: [README.es.md](./README.es.md)._

## Account API

`services/api` serves password reset and password change for HealthCore accounts.

Set these variables in a `.env` file at the repository root. Do not commit `.env`. Names are listed in `services/api/.env.example`.

- `RESEND_API_KEY` — Resend API key used to send the reset email.
- `RESEND_FROM` — sender address. `HealthCore <onboarding@resend.dev>` works before a custom domain is verified.
- `APP_URL` — UI origin placed in the reset link. Local default: `http://127.0.0.1:43123`.

Run the API with `python services/api/run.py` (port 43180). Run the backoffice from `uis/backoffice` (port 43123).
