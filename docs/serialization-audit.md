# Serialization audit

This file lists every FastAPI route in `services/api`, its serialization state before the change, and the schema used after.

States used on the assignment page:

- Already serialized: explicit `response_model` and an appropriate schema
- Partially serialized: a response exists but it is incomplete, over-exposes fields, or has no `response_model`
- Not serialized: raw document, ORM row, or untyped dict

## Endpoint inventory

| Method | Path | Purpose | Before | After |
| ------ | ---- | ------- | ------ | ----- |
| GET | `/health` | Liveness | Partially serialized | Already serialized |
| GET | `/` | Service index | Partially serialized | Already serialized |
| POST | `/users` | Register | Not serialized | Already serialized |
| GET | `/users` | List users | Not serialized | Already serialized |
| GET | `/users/{user_id}` | User detail | Not serialized | Already serialized |
| PUT | `/users/{user_id}` | Update user | Not serialized | Already serialized |
| DELETE | `/users/{user_id}` | Delete user | Partially serialized | Already serialized |
| GET | `/profiles/me` | Current profile | Not serialized | Already serialized |
| PUT | `/profiles/me` | Update profile | Not serialized | Already serialized |
| POST | `/auth/login` | Login | Partially serialized | Already serialized |
| GET | `/auth/me` | Current session | Partially serialized | Already serialized |
| GET | `/inventory/products` | List medical supplies | Already serialized | Already serialized |
| POST | `/inventory/products` | Create supply | Already serialized | Already serialized |
| GET | `/inventory/products/{supply_id}` | Supply detail | Already serialized | Already serialized |
| POST | `/inventory/orders/inbound` | Log delivery | Already serialized | Already serialized |
| POST | `/inventory/orders/outbound` | Log consumption | Already serialized | Already serialized |
| GET | `/inventory/orders` | List deliveries and consumptions | Already serialized | Already serialized |
| POST | `/api/incidents/analyze` | Analyze incident CSV | Not serialized | Already serialized |
| GET | `/api/incidents/results` | Last analysis JSON | Not serialized | Already serialized |
| GET | `/api/incidents/sample` | Download sample CSV | Partially serialized | Already serialized |
| GET | `/api/incidents/results/export` | Download results CSV | Partially serialized | Already serialized |

## Findings

### POST `/users` — Not serialized

- Before: no `response_model`. Returned `public_user` plus profile, including `email`.
- Input: `UserCreate` (`email`, `password`, optional `name`, `phone`, `address`).
- Output: `UserCreatedResponse` (`id`, `role`, `is_active`, `profile`). No email, no password fields.

### POST `/auth/login` — Partially serialized

- Before: `{access_token, token_type}` with no `response_model`.
- Input: `LoginRequest` (`email`, `password`) or the existing form fields.
- Output: `TokenResponse`. No email, no password.

### GET `/auth/me` — Partially serialized

- Before: untyped dict.
- Output: `MeResponse` (`id`, `email`, `role`, `uuid`, nested `profile`). Email is allowed here.

### GET `/users` — Not serialized

- Before: list of `public_user` dicts including `email`.
- Output: `UserListItem` (`id`, `role`, `uuid`). No nested profile.

### GET `/users/{user_id}` and PUT `/users/{user_id}` — Not serialized

- Before: `public_user` dict. PUT already used `UserUpdate`.
- Input (PUT): `UserUpdate` (`email`, `password`, `role`).
- Output: `UserPublic` (`id`, `email`, `is_active`, `role`, `created_at`, `uuid`). No password fields.

### DELETE `/users/{user_id}` — Partially serialized

- Before: `{"status": "deleted"}` with no `response_model`.
- Output: `DeleteStatus`.

### GET `/profiles/me` and PUT `/profiles/me`

- Before: `public_profile` dict. PUT already used `ProfileUpdate`.
- Input (PUT): `ProfileUpdate`.
- Output: `ProfileRead`. Display name is `Profile.name`.

### GET `/health` and GET `/`

- Before: small untyped dicts.
- Output: `HealthStatus`, `ServiceInfo`.

### Incident JSON

- Before: untyped dict from `to_dict()`.
- Output: `AnalysisResultRead`.

### Incident CSV downloads

- Before: CSV file responses with no published schema.
- Output: CSV download (`text/csv`).

### Inventory routes — Already serialized

- Already used named create and read models and `response_model` on every route.
- List products: `MedicalSupplyRead` with computed `current_stock`.
- Orders list embeds `MedicalSupplySummary`. User is `user_uuid` only.

## Relationship decisions

| Endpoint | Decision |
| -------- | -------- |
| POST `/users` | Nested `profile`. No email. |
| GET `/auth/me` | Nested `profile` or null. Email on the user. |
| GET `/users` | No profile. `uuid` only. |
| GET `/users/{user_id}`, PUT `/users/{user_id}` | No nested profile. |
| GET `/inventory/orders` | Embed supply summary. User is `user_uuid` only. |
| GET `/inventory/products` | Flat supply plus `current_stock`. |
| Incident JSON | Aggregates only. |

All endpoints above are marked Already serialized after implementation.
