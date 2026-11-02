# Serialization audit

Company: HealthCore  
Repository: `TB-AI-Engineer888/ai-engineering-company-project-monorepo`  
App: `services/api` FastAPI (`HealthCore Incident Analyzer API`)  
Branch: `feature/serialization-audit`

This audit covers every route registered on `main` by `services/api/main.py`. Password-reset routes exist only on the unmerged `feature/password-reset` branch (`POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/change-password`) and were **not** added here. No new third-party signup was required.

TinyDB `User.id` is the integer document id already used by tests and the backoffice. `User.uuid` is a separate UUID string stored for inventory `user_uuid`. Those identities were not rewritten.

Legend: ✅ serialized · ⚠️ partial · ❌ raw document / untyped dict

## Endpoint inventory

| Method | Path | Purpose | Before | After |
| ------ | ---- | ------- | ------ | ----- |
| GET | `/health` | Liveness | ⚠️ | ✅ |
| GET | `/` | Service index | ⚠️ | ✅ |
| POST | `/users` | Register | ❌ | ✅ |
| GET | `/users` | List users | ❌ | ✅ |
| GET | `/users/{user_id}` | User detail | ❌ | ✅ |
| PUT | `/users/{user_id}` | Update user | ❌ | ✅ |
| DELETE | `/users/{user_id}` | Delete user | ⚠️ | ✅ |
| GET | `/profiles/me` | Current profile | ❌ | ✅ |
| PUT | `/profiles/me` | Update profile | ❌ | ✅ |
| POST | `/auth/login` | Login | ⚠️ | ✅ |
| GET | `/auth/me` | Current session | ⚠️ | ✅ |
| GET | `/inventory/products` | List medical supplies | ✅ | ✅ |
| POST | `/inventory/products` | Create supply | ✅ | ✅ |
| GET | `/inventory/products/{supply_id}` | Supply detail | ✅ | ✅ |
| POST | `/inventory/orders/inbound` | Log delivery | ✅ | ✅ |
| POST | `/inventory/orders/outbound` | Log consumption | ✅ | ✅ |
| GET | `/inventory/orders` | List deliveries and consumptions | ✅ | ✅ |
| POST | `/api/incidents/analyze` | Analyze incident CSV | ❌ | ✅ |
| GET | `/api/incidents/results` | Last analysis JSON | ❌ | ✅ |
| GET | `/api/incidents/sample` | Download sample CSV | ⚠️ | ✅ |
| GET | `/api/incidents/results/export` | Download results CSV | ⚠️ | ✅ |

## Findings (before implementation)

Auth routes were reviewed first.

### POST `/users` — ❌ Not serialized

- **Today:** No `response_model`. Returned `public_user` plus nested profile, including `email`. Password hash was already stripped by `public_user`, but the register body echoed email.
- **Who calls it:** `uis/backoffice` `registerAccount`, then the form logs in with the typed email. The UI does not read email from this response.
- **Target input:** `UserCreate` (`email`, `password`, optional `name`, `phone`, `address`). Role from the client is ignored.
- **Target output:** `UserCreatedResponse` (`id`, `role`, `is_active`, `profile`) **without** `email`, `hashed_password`, or tokens.

### POST `/auth/login` — ⚠️ Partially serialized

- **Today:** Returned `{access_token, token_type}` (correct shape) with no `response_model`. Accepts JSON `LoginRequest` or form `username`/`password`.
- **Target input:** `LoginRequest` (`email`, `password`) or the existing form fields.
- **Target output:** `TokenResponse` only. No email, no password.

### GET `/auth/me` — ⚠️ Partially serialized

- **Today:** Untyped dict. Email is required by the profile view (`fetchMe`). `hashed_password` was not copied into the body, but that depended on hand-built keys.
- **Target output:** `MeResponse` with `id`, `email`, `role`, `uuid`, nested `profile` (`id`, `user_id`, `name`, `phone`, `address`). **Email is allowed here.**

### GET `/users` — ❌ Not serialized

- **Today:** List of `public_user` dicts including `email`, `is_active`, `created_at`.
- **Who calls it:** No backoffice list screen. Inventory tests used it only to recover `uuid`.
- **Target output:** `UserListItem` (`id`, `role`, `uuid`). Flat. No email, no nested profile.

### GET `/users/{user_id}` and PUT `/users/{user_id}` — ❌ Not serialized

- **Today:** `public_user` dict. PUT input already used `UserUpdate`.
- **Who calls it:** Authenticated self/admin only. No public list.
- **Target input (PUT):** `UserUpdate` (`email`, `password`, `role`) — not the response schema.
- **Target output:** `UserPublic` (`id`, `email`, `is_active`, `role`, `created_at`, `uuid`). Email stays on this authenticated detail/write confirmation only. Password fields never leave.

### DELETE `/users/{user_id}` — ⚠️ Partially serialized

- **Today:** `{"status": "deleted"}` without `response_model`.
- **Target output:** `DeleteStatus`.

### GET `/profiles/me` and PUT `/profiles/me` — ❌ / ⚠️

- **Today:** `public_profile` dict. PUT already used `ProfileUpdate`.
- **Who calls it:** Account profile form (`name`, `phone`, `address`).
- **Target input (PUT):** `ProfileUpdate`.
- **Target output:** `ProfileRead`. Display name lives on `Profile.name`, not on `User`.

### GET `/health` and GET `/` — ⚠️ Partially serialized

- **Today:** Small untyped dicts.
- **Target output:** `HealthStatus`, `ServiceInfo`.

### Incident JSON — ❌ Not serialized

- **Today:** `JSONResponse(result.to_dict())` and a raw dict. Shape was stable in tests but unpublished.
- **Who calls it:** Incident analyzer UI. PHI (`PAT-######`) must stay out of the payload (`to_dict` already strips it).
- **Target output:** `AnalysisResultRead` (metrics and invalid-row summaries only).

### Incident CSV downloads — ⚠️ Partially serialized

- **Today:** `FileResponse` / `Response` CSV. Not ORM objects.
- **Target:** Keep CSV (`response_class` + `text/csv` OpenAPI). A JSON `response_model` would be the wrong contract.

### Inventory routes — ✅ Already serialized

- Already had named input/output models in `services/schemas.py` and `response_model` on every route.
- List products: `MedicalSupplyRead` with computed `current_stock`, no nested orders.
- Product writes: `MedicalSupplyCreate` ≠ `MedicalSupplyRead`.
- Orders: inbound/outbound use separate create vs read models. List embeds `MedicalSupplySummary` (flat product card), not a TinyDB user. User is `user_uuid` only.

## Decisions log

| Endpoint | Relationship handling |
| -------- | --------------------- |
| POST `/users` | Nested `profile` (`name`, `phone`, `address`, ids). No email. |
| GET `/auth/me` | Nested `profile` or `null`. Email on the user projection. |
| GET `/users` | No profile. `uuid` only, for inventory `user_uuid`. |
| GET `/users/{user_id}`, PUT `/users/{user_id}` | No nested profile. Email allowed (authenticated detail). |
| GET `/inventory/orders` | Embed `supply` summary. Do not embed TinyDB user — only `user_uuid`. |
| GET `/inventory/products` | Flat supply + `current_stock`. No order nesting. |
| Incident JSON | Aggregates only. No patient identifiers. |

## Consumers used to choose fields

| Consumer | Fields read |
| -------- | ----------- |
| `uis/backoffice/src/lib/auth.ts` `registerAccount` | Ignored after POST; form already has email. |
| `login` | `access_token` only. |
| `fetchMe` | `email`, `profile.name/phone/address`. |
| `updateProfile` | `name`, `phone`, `address`. |
| `uis/backoffice/src/lib/inventory.ts` | Product list/detail: id, name, sku, category, unit, country, current_stock. Orders: order_kind, ids, quantity, clinic_id, created_at, user_uuid, vendor_name, consumption_type, nested supply summary. |
| `uis/backoffice` incident analyzer | Analysis metrics from `to_dict()`. CSV export download. |
| Existing pytest | Auth, users, profiles, inventory stock, incident sample metrics. |

## Post-implementation checklist

- [x] All endpoints marked ✅
- [x] Every JSON route declares `response_model=...`
- [x] CSV routes declare `text/csv` in OpenAPI (`response_class` + `responses=`)
- [x] Write routes use separate body models (not the response schema)
- [x] Register, login: no email, no password fields
- [x] `GET /auth/me` still returns the caller's email
- [x] List `/users` is a flat projection
- [x] Inventory schemas unchanged in shape
- [x] Existing tests updated only where they asserted the old over-exposed register/list bodies
