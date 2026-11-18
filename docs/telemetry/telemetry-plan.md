# HealthCore telemetry plan

This document is the contract for instrumenting the inventory system in this repository. A developer should be able to emit every event from the code that exists today, plus the gaps named in section 11, without a follow-up design conversation.

The catalogue contains **18 events**. **5 are mandatory**, taken from the HealthCore briefing with those `event_type` values unchanged. **13 are identified opportunities** found in the running backoffice and API.

The wire format for each event is the draft-07 document at `events.<event_type>.schema` in [`event-schemas.json`](./event-schemas.json). Metadata fields in that file (`classification`, `hypothesis`, `decision`, `delivery`, `throttle`, `sensitive_data`, `allowlist`) describe the event. They are not part of the emitted object.

## 1. Regulatory boundary

HealthCore events describe supplies and stock. HIPAA and UK GDPR still apply, because this system sits next to clinics. The property allowlist is the control. Each schema sets `additionalProperties` to false on the envelope and on `properties`.

These values are excluded from every event, including test fixtures:

- Patient names, medical record numbers, NHS numbers, diagnoses, dates of birth, and appointment identifiers
- Staff email, personal name, phone, and address
- Passwords, password hashes, bearer tokens, and `SECRET_KEY`
- Uploaded filenames, CSV bodies, and incident free text
- IP addresses and URL query strings

`userId` is the staff `uuid` already stored on `supply_deliveries.user_uuid` and `supply_consumptions.user_uuid`. It is an internal key. The telemetry store does not join it to email or to a profile name. Dr. Okonkwo's later report aggregates by clinic and by country. Claire's control alert for a rejected stock edit uses the clinic, and the operational database can resolve the uuid at alert time.

`department` is a clinical area. The allowed values are `primary_care`, `specialty_care`, `chronic_care`, and `general_consultation`.

## 2. System this plan instruments

The running system is the HealthCore API and backoffice in this fork.

| Piece | Where it lives | What telemetry has to know |
| --- | --- | --- |
| Supply master | `MedicalSupply` in `services/models.py` | `id`, `sku`, `category`, `unit`, `country`. There is no expiry column and no stock column. |
| Receipt | `SupplyDelivery`, `POST /inventory/orders/inbound` | `quantity`, `vendor_name`, `clinic_id`, `user_uuid`. This is the inbound order. |
| Consumption | `SupplyConsumption`, `POST /inventory/orders/outbound` | `quantity`, `consumption_type` (`clinical_use` or `expiry_waste`), `clinic_id`, `user_uuid`. |
| Stock figure used by the API | `current_stock()` in `services/inventory_stock.py` | Inbound sum minus outbound sum for a `supply_id`, across every clinic. |
| Low-stock band in the UI | `LOW_STOCK_AT_OR_BELOW = 10` in `uis/backoffice/src/lib/stock-level.ts` | Healthy is 11 or more, low is 1 through 10, out is 0. |
| Clinics | `CLINIC_IDS` 1 through 12 | The select shows `Clinic {id}`. There is no clinic table and no country on the clinic. |
| Users | TinyDB via `services/api/users.py` | Numeric `id` is the JWT `sub`. `uuid` is the staff key used on orders. Roles are `admin`, `manager`, and `user`. |
| Session | JWT from `POST /auth/login`, stored at `healthcore.session.token` | The token has `sub` and `exp`. It has no `jti`. The token is not a telemetry identifier. |
| Cache | `inventory_cache` in `services/ttl_cache.py` | Products live 60 seconds. Orders live 45 seconds. Writes call `invalidate_prefix`. |
| Latency log | `timing_middleware` in `services/api/main.py` | Logs method, raw path, status, and milliseconds. The raw path is not the telemetry route. |
| Pages | `uis/backoffice/src/app` | `/`, `/login`, `/register`, `/account/profile`, `/backoffice/inventory/products`, `/backoffice/inventory/orders`, `/backoffice/inventory/orders/inbound`, `/backoffice/inventory/orders/outbound`, `/incidents`. |

Stock for a threshold is the sum of deliveries minus the sum of consumptions **for the same `clinic_id` and the same `product_id`**. The global `current_stock()` total remains the figure the existing 400 response uses, and outbound events record it separately as `global_stock_after`. Seed data shows why the split matters: SKU `HCR-PPE-001` is received at clinic 1 and clinic 3. A shortage at clinic 3 can sit inside a healthy global total.

That split is the hardest design decision in the plan. The briefing asks how often a clinic runs short. The function the API uses today cannot answer that, because it adds every clinic together.

## 3. Clinic directory

Use this directory for `country` until a clinic table exists. It has 9 US clinics and 3 UK clinics, which matches the company profile, and it agrees with the seed: US supplies are delivered to clinics 1 through 5, and UK supplies are delivered to clinics 10 and 11. If operations already assigns these ids differently, replace this table before the first event is emitted. Do not read `country` for an order event from `MedicalSupply.country`.

| clinic_id | country | region |
| --- | --- | --- |
| 1 | US | Texas |
| 2 | US | Texas |
| 3 | US | Texas |
| 4 | US | Florida |
| 5 | US | Florida |
| 6 | US | Florida |
| 7 | US | Georgia |
| 8 | US | Georgia |
| 9 | US | Georgia |
| 10 | UK | London |
| 11 | UK | London |
| 12 | UK | Manchester |

`country_mismatch` on an inbound event is true when the product's stored country differs from this directory. The event still reports the clinic country.

## 4. Category map

`product_category` on an event uses the briefing vocabulary. The database stores a different set. Map at emit time.

| Stored `MedicalSupply.category` | Event `product_category` |
| --- | --- |
| `medications` | `medication` |
| `ppe` | `ppe` |
| `consumables` | `consumable` |
| `wound_care` | `consumable` |
| `diagnostics` | `consumable` |

Wound-care material and diagnostic kits are consumable supplies in the briefing's four-way split. The stored value stays on the product row for the screen labels. It is not written to the event.

## 5. Event envelope

Every event is one JSON object with these fields, and no others.

| Field | Rule |
| --- | --- |
| `eventId` | UUID generated for this event. |
| `timestamp` | ISO 8601 UTC, with a `Z` suffix, set when the event is emitted. |
| `sessionId` | UUID created in the browser at login and stored in `sessionStorage` under `healthcore.session.id`. Sent on API calls as `X-Session-Id`. Cleared on logout. Null when no session exists. Never the JWT. |
| `userId` | Staff `uuid`. Null only for the events whose schema says null. Never an email. |
| `event_type` | The name in this catalogue, `entity_action` form. The five mandatory names are the briefing names. |
| `schemaVersion` | Integer `1`. |
| `requestId` | UUID created at the start of an API request and returned as `X-Request-Id`. Browser events that follow a response reuse that id when they have one, and generate a UUID otherwise. |
| `properties` | Object whose keys are exactly the allowlist for that `event_type`. |

Server-emitted inventory events are produced inside the API. Browser events are posted to `POST /telemetry/events`, which validates the body against that event's schema and rejects any `event_type` whose emitter is `server`. A browser cannot file a receipt into the telemetry stream.

A failure to emit does not change the HTTP status of a committed order. Emit after the business decision is final. Retry from a local spool. Do not roll back a delivery because the spool is unavailable.

## 6. Catalogue

| event_type | classification | category | emitter | delivery | decision |
| --- | --- | --- | --- | --- | --- |
| `inbound_order_created` | mandatory | business | server | batch | To consolidate purchasing across clinics and negotiate better vendor terms |
| `outbound_order_created` | mandatory | business | server | batch | To adjust automatic replenishment of critical supplies per clinic |
| `stock_threshold_triggered` | mandatory | business | server | stream | To prioritise urgent restocking and escalate to Marcus (Clinical Operations) |
| `direct_stock_edit_rejected` | mandatory | business | server | stream | To reinforce training or permissions at the clinic where this happens most |
| `supply_expiry_flagged` | mandatory | business | server | batch | To prioritise use or controlled disposal of that batch before expiry |
| `product_registered` | identified opportunity | business | server | batch | To spot a clinic country whose catalogue is missing a critical category before a stockout shows it |
| `incident_analysis_completed` | identified opportunity | business | server | batch | To keep or retire the analyser once inventory telemetry is carrying the operational questions |
| `login_succeeded` | identified opportunity | authentication | server | stream | To revoke unused privileged roles and to confirm inventory stays reachable during clinic hours |
| `login_failed` | identified opportunity | authentication | server | stream | To reset access for a clinic that is locked out, or to investigate repeated failures against the login form |
| `session_expired` | identified opportunity | authentication | server | stream | To change ACCESS_TOKEN_EXPIRE_MINUTES, and to see accounts closed while someone is still in the backoffice |
| `account_registered` | identified opportunity | authentication | server | batch | To keep open self-service registration or replace it with an invite |
| `outbound_order_rejected` | identified opportunity | errors | server | stream | To restock that supply, or to replace the global 400 check with a clinic-scoped check if the rejections do not match clinic shortages |
| `inventory_validation_failed` | identified opportunity | errors | server | batch | To fix the field that operators trip over, or to correct seed and master data when unknown products dominate |
| `client_exception_captured` | identified opportunity | errors | browser | stream | To patch the section that is breaking the receipt or consumption flow in the current shift |
| `api_latency_recorded` | identified opportunity | performance | server | stream | To investigate any inventory write that stays at or above 500 milliseconds |
| `inventory_cache_summarised` | identified opportunity | performance | server | batch | To shorten a TTL, or to bypass the cache on the product list while any clinic of that product is below its minimum |
| `backoffice_section_viewed` | identified opportunity | navigation | browser | batch | To put the sections that are actually used on the first screen, and to question sections that are never opened |
| `backoffice_flow_abandoned` | identified opportunity | navigation | browser | batch | To change the step that accounts for the abandonments before adding more fields to the form |

## 7. Event specifications

### `inbound_order_created`

- Classification: mandatory
- Category: business
- Emitter: server
- Delivery: batch

We capture `inbound_order_created` because we need to know how much and what supply is being purchased, by clinic and vendor, which allows us to make the decision to consolidate purchasing across clinics and negotiate better vendor terms.

**Where it is emitted.** Emit from create_inbound_order in services/routers/inventory.py after session.commit() succeeds on POST /inventory/orders/inbound.

**Why this delivery mode.** Vendor consolidation is a purchasing review. A daily batch is soon enough for that decision. The stockout decision is a separate stream event.

**Throttle.** One event for each committed inbound order. No sampling.

**Sensitive data.** vendor_name is the organisation on the delivery, which the purchasing decision needs. The pattern rejects free text long enough to carry a sentence. No staff name, email, or patient field is accepted.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `clinic_id` | integer | yes | no | Clinic that owns this stock movement. Values are 1 through 12. |
| `country` | string | yes | no | Country of that clinic from the clinic directory in this plan: US or UK. |
| `product_id` | integer | yes | no | medical_supplies.id of the supply. |
| `product_category` | string | yes | no | Briefing category after the stored-category map: medication, ppe, consumable, or equipment. |
| `quantity` | integer | yes | no | Supply units this event is about. The event description says which quantity. |
| `order_id` | integer | yes | no | supply_deliveries.id of the committed receipt. |
| `vendor_name` | string | yes | no | Vendor organisation recorded on the delivery. |
| `sku` | string | yes | no | medical_supplies.sku, copied so the batch can be read without a join. |
| `unit` | string | yes | no | Unit stored on the supply: box, unit, pack, or vial. |
| `country_mismatch` | boolean | yes | no | True when medical_supplies.country differs from the clinic country. The event still uses the clinic country. |

### `outbound_order_created`

- Classification: mandatory
- Category: business
- Emitter: server
- Delivery: batch

We capture `outbound_order_created` because we need to know which supplies are consumed most, and at what rate, by clinic and department, which allows us to make the decision to adjust automatic replenishment of critical supplies per clinic.

**Where it is emitted.** Emit from create_outbound_order in services/routers/inventory.py after session.commit() succeeds on POST /inventory/orders/outbound. Refuse to emit when department is absent.

**Why this delivery mode.** Replenishment quantities are set from a consumption rate. The daily batch answers that. A same-shift shortage is stock_threshold_triggered, which is stream.

**Throttle.** One event for each committed outbound order. No sampling.

**Sensitive data.** department is one of four clinical-area codes. consumption_type is clinical_use or expiry_waste. Neither field has room for a person.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `clinic_id` | integer | yes | no | Clinic that owns this stock movement. Values are 1 through 12. |
| `country` | string | yes | no | Country of that clinic from the clinic directory in this plan: US or UK. |
| `product_id` | integer | yes | no | medical_supplies.id of the supply. |
| `product_category` | string | yes | no | Briefing category after the stored-category map: medication, ppe, consumable, or equipment. |
| `quantity` | integer | yes | no | Supply units this event is about. The event description says which quantity. |
| `department` | string | yes | no | Clinical area that consumed the supply. Never a patient, staff name, or record number. |
| `order_id` | integer | yes | no | supply_consumptions.id of the committed consumption. |
| `consumption_type` | string | yes | no | Value stored on the consumption row. |
| `sku` | string | yes | no | medical_supplies.sku. |
| `clinic_stock_after` | integer | yes | no | Units of this product remaining at this clinic after the commit. Sum deliveries and consumptions for this clinic_id and product_id only. |
| `global_stock_after` | integer | yes | no | Value current_stock() returns for this product after the commit. The live 400 check uses this global total. |

### `stock_threshold_triggered`

- Classification: mandatory
- Category: business
- Emitter: server
- Delivery: stream

We capture `stock_threshold_triggered` because we need to know how often a clinic runs short of a critical supply (for example PPE or medication), which allows us to make the decision to prioritise urgent restocking and escalate to Marcus (Clinical Operations).

**Where it is emitted.** After a successful outbound commit, recompute clinic-scoped stock. The minimum is 10 until a per-product minimum exists, matching LOW_STOCK_AT_OR_BELOW in uis/backoffice/src/lib/stock-level.ts. Band low is 1 through 10. Band out is 0.

**Why this delivery mode.** Marcus acts during the same shift. A nightly batch can miss a clinic that runs out of PPE this afternoon.

**Throttle.** Emit on the crossing. While stock stays below the minimum, emit at most once more per clinic_id, product_id, and band per UTC day. A jump from healthy stock to zero emits one event with band out.

**Sensitive data.** Counts and identifiers of supplies and clinics only.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `clinic_id` | integer | yes | no | Clinic that owns this stock movement. Values are 1 through 12. |
| `country` | string | yes | no | Country of that clinic from the clinic directory in this plan: US or UK. |
| `product_id` | integer | yes | no | medical_supplies.id of the supply. |
| `product_category` | string | yes | no | Briefing category after the stored-category map: medication, ppe, consumable, or equipment. |
| `quantity` | integer | yes | no | Supply units this event is about. The event description says which quantity. |
| `threshold_quantity` | integer | yes | no | Minimum that was crossed. Use 10 until a product-level minimum is stored. |
| `band` | string | yes | no | low when clinic stock is 1 through 10. out when clinic stock is 0. |
| `stock_before` | integer | yes | no | Clinic-scoped units immediately before this order. |
| `trigger_order_id` | integer | yes | no | supply_consumptions.id that caused the crossing. |
| `trigger_order_kind` | const outbound | yes | no | Stock falls only when an outbound order commits. |

### `direct_stock_edit_rejected`

- Classification: mandatory
- Category: business
- Emitter: server
- Delivery: stream

We capture `direct_stock_edit_rejected` because we need to know if staff are attempting to bypass supply traceability controls, which allows us to make the decision to reinforce training or permissions at the clinic where this happens most.

**Where it is emitted.** On POST /inventory/products, POST /inventory/orders/inbound, and POST /inventory/orders/outbound, read the raw JSON first. If the object contains current_stock, stock, quantity_on_hand, or on_hand, return 403 and emit this event. The create models today drop unknown keys, so the check has to see the raw object. Also reject PUT or PATCH /inventory/products/{supply_id} and POST /inventory/stock, which are not implemented, with the same 403 and the same event.

**Why this delivery mode.** The person is blocked on this request and may try another path during the same shift. The clinic lead needs the rejection the same day, which a nightly batch can miss.

**Throttle.** One event for each rejected request. No sampling. A repeated attempt is itself the signal.

**Sensitive data.** Record the attempted supply quantity and the route template. Do not copy any other body field. A free-text note is not on the allowlist.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `attempted_method` | string | yes | no | HTTP method of the rejected call. |
| `attempted_route` | string | yes | no | Route template, with identifiers replaced. Example: /inventory/products/{supply_id}. |
| `rejection_reason` | const stock_mutable_only_through_orders | yes | no | Fixed reason. Stock changes only through SupplyDelivery or SupplyConsumption. |
| `quantity` | integer | yes | no | Attempted stock quantity. Use 0 when the forbidden key was present without a number. |
| `clinic_id` | nullable | yes | no | Clinic id when the body included a valid clinic_id. Otherwise null. |
| `country` | nullable | yes | no | Clinic country when clinic_id resolved. Otherwise null. |
| `product_id` | nullable | yes | no | Supply id when the body or the path included one. Otherwise null. |
| `product_category` | nullable | yes | no | Mapped briefing category when the supply row exists. Otherwise null. |

### `supply_expiry_flagged`

- Classification: mandatory
- Category: business
- Emitter: server
- Delivery: batch

We capture `supply_expiry_flagged` because we need to know which supplies are about to expire before they become waste or a compliance risk, which allows us to make the decision to prioritise use or controlled disposal of that batch before expiry.

**Where it is emitted.** Requires a SupplyBatch row (product_id, clinic_id, lot_id, expires_on) referenced by the inbound order. expires_on is stored on that batch, which belongs to the product. A receipt of a batch already inside the window writes the event in that request. A daily sweep writes the event for every batch with days_to_expiry of 30 or less and remaining quantity above zero.

**Why this delivery mode.** Disposal and use-first planning is a morning operations list. The event is written when the batch is received and again by the daily sweep, and the purchasing batch consumes it the same day. Shelving control reads expires_on on the batch row at receipt time.

**Throttle.** At most one event per lot_id and clinic_id per UTC day.

**Sensitive data.** lot_id allows only letters, digits, dot, underscore, and hyphen, with a maximum of 40 characters, so a name or sentence cannot be stored in it.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `clinic_id` | integer | yes | no | Clinic that owns this stock movement. Values are 1 through 12. |
| `country` | string | yes | no | Country of that clinic from the clinic directory in this plan: US or UK. |
| `product_id` | integer | yes | no | medical_supplies.id of the supply. |
| `product_category` | string | yes | no | Briefing category after the stored-category map: medication, ppe, consumable, or equipment. |
| `quantity` | integer | yes | no | Supply units this event is about. The event description says which quantity. |
| `lot_id` | string | yes | no | Batch code stored on SupplyBatch. |
| `expires_on` | string | yes | no | Expiry date stored on the batch, YYYY-MM-DD. |
| `days_to_expiry` | integer | yes | no | Whole UTC days from today until expires_on. Negative means already expired. |
| `trigger` | string | yes | no | receipt when the inbound request created an in-window batch. daily_sweep for the morning job. |

### `product_registered`

- Classification: identified opportunity
- Category: business
- Emitter: server
- Delivery: batch

We capture `product_registered` because we need to know which supply categories the catalogue is growing in, and in which country, which allows us to make the decision to spot a clinic country whose catalogue is missing a critical category before a stockout shows it.

**Where it is emitted.** Emit from create_product in services/routers/inventory.py after session.commit() on POST /inventory/products returns 201.

**Why this delivery mode.** Catalogue review is periodic. The register action itself is confirmed by the HTTP 201 the user already sees.

**Throttle.** One event for each committed product. No sampling.

**Sensitive data.** The product name is omitted. Names are operationally useful and also a place a person could type a patient. sku, category, unit, and country answer the catalogue decision.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `product_id` | integer | yes | no | medical_supplies.id of the new row. |
| `sku` | string | yes | no | SKU stored on the new supply. |
| `product_category` | string | yes | no | Briefing category after the stored-category map. |
| `unit` | string | yes | no | Unit stored on the supply. |
| `country` | string | yes | no | Country stored on the product. A product is not tied to one clinic. |
| `quantity` | const 0 | yes | no | A new product has no stock until an inbound order. Always 0. |

### `incident_analysis_completed`

- Classification: identified opportunity
- Category: business
- Emitter: server
- Delivery: batch

We capture `incident_analysis_completed` because we need to know how often staff run the incident analyser and how large those extracts are, which allows us to make the decision to keep or retire the analyser once inventory telemetry is carrying the operational questions.

**Where it is emitted.** Emit from analyze_incidents in services/api/main.py after analyze_csv_bytes returns. source_kind is sample only when the client used the sample endpoint's file; otherwise upload.

**Why this delivery mode.** The user already has the HTTP response. Whether the tool is still used is a periodic product decision.

**Throttle.** One event for each successful POST /api/incidents/analyze. Failures are inventory-unrelated validation and are excluded.

**Sensitive data.** The filename, the CSV body, and every incident cell are excluded. A filename or a cell can carry a person. row_count and duration_ms describe the job without the contents.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `source_kind` | string | yes | no | upload for a caller-supplied file. sample for the bundled sample CSV. |
| `row_count` | integer | yes | no | Data rows accepted by the analyser. |
| `duration_ms` | number | yes | no | Server time spent inside analyze_csv_bytes. |

### `login_succeeded`

- Classification: identified opportunity
- Category: authentication
- Emitter: server
- Delivery: stream

We capture `login_succeeded` because we need to know which staff roles open the backoffice, and whether clinic staff can sign in during operating hours, which allows us to make the decision to revoke unused privileged roles and to confirm inventory stays reachable during clinic hours.

**Where it is emitted.** Emit from login in services/api/routers.py after authenticate succeeds. Return uuid and role from authenticate for the emitter. The HTTP body remains access_token and token_type.

**Why this delivery mode.** A locked-out clinic cannot record consumption. The same shift is the window in which access has to be restored.

**Throttle.** One event for each successful POST /auth/login. No sampling.

**Sensitive data.** Role is an application permission, not a person. Email stays out of the event. userId is the staff uuid.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `role` | string | yes | no | users.role of the account that signed in. |

### `login_failed`

- Classification: identified opportunity
- Category: authentication
- Emitter: server
- Delivery: stream

We capture `login_failed` because we need to know how many sign-in attempts fail, and whether the cause is an unknown account, a bad password, or an inactive account, which allows us to make the decision to reset access for a clinic that is locked out, or to investigate repeated failures against the login form.

**Where it is emitted.** authenticate in services/api/users.py currently raises one ValueError for an unknown user, an inactive user, and a bad password. Split those internal causes. The HTTP detail stays Incorrect email or password.

**Why this delivery mode.** A clinic that cannot sign in cannot record receipts or consumption. That is a same-shift operations problem.

**Throttle.** Every failure is emitted. Sampling would hide a burst.

**Sensitive data.** The attempted email, password, and IP address are excluded. failure_reason is one of three codes. userId and sessionId are null because no session exists.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `failure_reason` | string | yes | no | Internal cause. The client still receives one generic 401 message. |

### `session_expired`

- Classification: identified opportunity
- Category: authentication
- Emitter: server
- Delivery: stream

We capture `session_expired` because we need to know whether working sessions die because the token lapsed or because the account was deactivated, which allows us to make the decision to change ACCESS_TOKEN_EXPIRE_MINUTES, and to see accounts closed while someone is still in the backoffice.

**Where it is emitted.** Emit from get_current_user in services/api/deps.py. ExpiredSignatureError maps to token_expired. A token whose user is inactive maps to inactive_user. Other JWT failures stay a 401 without this event, because they are not an expired session.

**Why this delivery mode.** A session that dies in the middle of a receipt is a same-shift failure. The client already redirects to /login on 401.

**Throttle.** One event per rejected request whose token was present and unusable. A missing Authorization header does not emit this event.

**Sensitive data.** The token is not copied. userId is the uuid when the subject still resolves to a user, and null when it does not.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `reason` | string | yes | no | Why the presented token was refused. |

### `account_registered`

- Classification: identified opportunity
- Category: authentication
- Emitter: server
- Delivery: batch

We capture `account_registered` because we need to know whether clinic staff create their own accounts or only the seeded administrator is in use, which allows us to make the decision to keep open self-service registration or replace it with an invite.

**Where it is emitted.** Emit from register_user in services/api/routers.py after create_user and create_profile succeed. The public route always assigns role user.

**Why this delivery mode.** Registration volume is a periodic access-policy decision. The new user already receives the HTTP 201.

**Throttle.** One event for each created account. No sampling.

**Sensitive data.** The request carries email, password, name, phone, and address. None of those are on the allowlist. userId is the new uuid. sessionId is null because the client does not start a session in registerAccount.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `role` | const user | yes | no | Role assigned by the public registration route. |

### `outbound_order_rejected`

- Classification: identified opportunity
- Category: errors
- Emitter: server
- Delivery: stream

We capture `outbound_order_rejected` because we need to know which clinic and supply combinations ask for more stock than the global total allows, which allows us to make the decision to restock that supply, or to replace the global 400 check with a clinic-scoped check if the rejections do not match clinic shortages.

**Where it is emitted.** Emit from create_outbound_order when body.quantity is greater than current_stock(). Do not also emit inventory_validation_failed for that same rejection.

**Why this delivery mode.** The operator is blocked on this attempt. Same-shift restock is the decision the rejection is for.

**Throttle.** One event for each 400 insufficient-stock response. No sampling.

**Sensitive data.** Department is the clinical-area code once the field exists on the form. The API error string is not copied, because it includes the supply name and the two quantities are already structured.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `clinic_id` | integer | yes | no | Clinic that owns this stock movement. Values are 1 through 12. |
| `country` | string | yes | no | Country of that clinic from the clinic directory in this plan: US or UK. |
| `product_id` | integer | yes | no | medical_supplies.id of the supply. |
| `product_category` | string | yes | no | Briefing category after the stored-category map: medication, ppe, consumable, or equipment. |
| `quantity` | integer | yes | no | Supply units this event is about. The event description says which quantity. |
| `department` | string | yes | no | Clinical area that consumed the supply. Never a patient, staff name, or record number. |
| `available_global` | integer | yes | no | current_stock() value the handler compared against the request. |
| `rejection_reason` | const insufficient_stock | yes | no | Fixed reason for this event. |

### `inventory_validation_failed`

- Classification: identified opportunity
- Category: errors
- Emitter: server
- Delivery: batch

We capture `inventory_validation_failed` because we need to know which inventory fields fail validation most often, by route, which allows us to make the decision to fix the field that operators trip over, or to correct seed and master data when unknown products dominate.

**Where it is emitted.** Emit for duplicate SKU on create_product (400), an unknown supply on either order route (404 from _get_supply), and a 422 from the inventory body models. reason_code selects the case. field_name is the model field when one is known.

**Why this delivery mode.** The caller already sees the 400 or 404. Which field fails most is a backlog decision, reviewed with the other daily operational events.

**Throttle.** One event per rejected request. Requests that emit direct_stock_edit_rejected or outbound_order_rejected do not also emit this event.

**Sensitive data.** The rejected value is excluded. A vendor string or a SKU typo is a place a person could be typed. Only the field name and the reason code are kept.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `route_template` | string | yes | no | Route template of the rejected call. |
| `method` | string | yes | no | Inventory writes that this event covers are POST. |
| `http_status` | integer | yes | no | Status returned to the client. |
| `reason_code` | string | yes | no | Why the write was rejected. |
| `field_name` | nullable | yes | no | Model field that failed, or null when the failure is not a single field. |

### `client_exception_captured`

- Classification: identified opportunity
- Category: errors
- Emitter: browser
- Delivery: stream

We capture `client_exception_captured` because we need to know which backoffice sections throw during clinic hours, which allows us to make the decision to patch the section that is breaking the receipt or consumption flow in the current shift.

**Where it is emitted.** Register window error and unhandledrejection listeners in the backoffice layout. POST the event to /telemetry/events.

**Why this delivery mode.** A broken order form stops stock from being recorded. That is visible the same shift, or the clinic works around it.

**Throttle.** Suppress a repeat of the same section and error_name for 60 seconds in that browser tab.

**Sensitive data.** The stack, the URL query, and the raw message are excluded. message_scrubbed has emails removed, runs of 6 or more digits replaced with [redacted], and is cut at 200 characters.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `section` | string | yes | no | Backoffice section mounted when the exception was thrown. |
| `error_name` | string | yes | no | Error constructor name, such as TypeError or ApiError. |
| `message_scrubbed` | string | yes | yes | Message after the scrubber. May be empty when the message was only an email or a long digit run. |

### `api_latency_recorded`

- Classification: identified opportunity
- Category: performance
- Emitter: server
- Delivery: stream

We capture `api_latency_recorded` because we need to know which API routes are slow enough to stall a receipt or a consumption during clinic hours, which allows us to make the decision to investigate any inventory write that stays at or above 500 milliseconds.

**Where it is emitted.** Extend timing_middleware in services/api/main.py. Replace numeric path segments with the template names already used by the routers, such as {supply_id} and {user_id}.

**Why this delivery mode.** A slow inventory write is happening to someone at a clinic now. The slow cases are the ones worth seeing within minutes.

**Throttle.** Always emit when duration_ms is 500 or more. Otherwise emit about 1 in 20 requests. Draw the sample before logging. Record the route template, never the raw path and never the query string.

**Sensitive data.** Method, template, status, and duration only. The Authorization header and the body are excluded.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `method` | string | yes | no | Request method. |
| `route_template` | string | yes | no | Path template after identifier replacement. |
| `status_code` | integer | yes | no | HTTP status of the response. |
| `duration_ms` | number | yes | no | Server duration measured by timing_middleware. |
| `slow` | boolean | yes | no | True when duration_ms is 500 or more. |

### `inventory_cache_summarised`

- Classification: identified opportunity
- Category: performance
- Emitter: server
- Delivery: batch

We capture `inventory_cache_summarised` because we need to know whether the 60 second product cache and the 45 second order cache are hiding a stock change operators need to see, which allows us to make the decision to shorten a TTL, or to bypass the cache on the product list while any clinic of that product is below its minimum.

**Where it is emitted.** Add hit, miss, and invalidation counters to TtlCache in services/ttl_cache.py. Keys are inventory:products (60 seconds) and inventory:orders (45 seconds). A scheduler emits the previous hour and resets the counters. userId and sessionId are null.

**Why this delivery mode.** A single cache hit does not change a decision. The hourly ratio of hits, misses, and invalidations does.

**Throttle.** One event per cache key per completed hour. This replaces per-request cache events, which were discarded.

**Sensitive data.** Counts and the two known cache keys. No cached row is copied.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `cache_key` | string | yes | no | TTL key that was counted. |
| `hits` | integer | yes | no | Successful gets in the window. |
| `misses` | integer | yes | no | Gets that found nothing or an expired entry. |
| `invalidations` | integer | yes | no | Keys removed by invalidate_prefix after a write. |
| `window_start` | string | yes | no | Inclusive UTC start of the hour. |
| `window_end` | string | yes | no | Exclusive UTC end of the hour. |

### `backoffice_section_viewed`

- Classification: identified opportunity
- Category: navigation
- Emitter: browser
- Delivery: batch

We capture `backoffice_section_viewed` because we need to know which sections operators open, and which inventory steps they reach, which allows us to make the decision to put the sections that are actually used on the first screen, and to question sections that are never opened.

**Where it is emitted.** Listen to App Router path changes. Map the path to the section enum before sending. POST /telemetry/events.

**Why this delivery mode.** Section popularity is a weekly design question. The operator does not wait on this event.

**Throttle.** Debounce route changes by 1 second so a redirect does not emit two sections. One event per section entry after that pause.

**Sensitive data.** The section code is an enum. The full URL, query string, and document title are excluded.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `section` | string | yes | no | Section that was opened. |
| `previous_section` | nullable | yes | no | Previous section in this tab, or null when the tab has no previous section. |

### `backoffice_flow_abandoned`

- Classification: identified opportunity
- Category: navigation
- Emitter: browser
- Delivery: batch

We capture `backoffice_flow_abandoned` because we need to know which step of a receipt or a consumption is where operators stop, which allows us to make the decision to change the step that accounts for the abandonments before adding more fields to the form.

**Where it is emitted.** Instrument InboundOrderForm and OutboundOrderForm. Record the last step whose control became valid. Do not copy the control's value. POST /telemetry/events.

**Why this delivery mode.** Form friction is reviewed with the weekly navigation batch. The operator is no longer on the form.

**Throttle.** One event when the form route unmounts and the tab saw no 201 for that form. Ignore unmounts shorter than 2 seconds.

**Sensitive data.** Step names are an enum. Quantity, vendor, and supply choice are excluded so a typed name cannot ride along in this event.

| Property | Type | Required | Sensitive | Description |
| --- | --- | --- | --- | --- |
| `flow` | string | yes | no | Form that was left. |
| `last_completed_step` | string | yes | no | Last step that had a value. The value itself is not stored. |
| `time_on_form_seconds` | integer | yes | no | Seconds the form stayed mounted. Values under 2 seconds are not emitted. |

### Worked envelope

`inbound_order_created` on the wire looks like this. The same envelope wraps every other event. Only `properties` changes, and the schema for that event is the check.

```json
{
  "eventId": "11111111-1111-4111-8111-111111111111",
  "timestamp": "2026-11-18T15:04:00Z",
  "sessionId": "44444444-4444-4444-8444-444444444444",
  "userId": "22222222-2222-4222-8222-222222222222",
  "event_type": "inbound_order_created",
  "schemaVersion": 1,
  "requestId": "33333333-3333-4333-8333-333333333333",
  "properties": {
    "clinic_id": 1,
    "country": "US",
    "product_id": 1,
    "product_category": "ppe",
    "quantity": 40,
    "order_id": 15,
    "vendor_name": "MedLine Industries",
    "sku": "HCR-PPE-001",
    "unit": "box",
    "country_mismatch": false
  }
}
```

## 8. Delivery strategy

Stream means someone may act during the current clinic shift. Batch means the decision is a review: daily for purchasing, replenishment, and expiry, hourly for the cache, weekly for navigation.

| Delivery | Events | Decision that sets the pace |
| --- | --- | --- |
| Stream | `stock_threshold_triggered`, `direct_stock_edit_rejected`, `login_succeeded`, `login_failed`, `session_expired`, `outbound_order_rejected`, `client_exception_captured`, `api_latency_recorded` | Same-shift restock, access, a blocked order, a broken page, or a slow write |
| Batch | `inbound_order_created`, `outbound_order_created`, `supply_expiry_flagged`, `product_registered`, `incident_analysis_completed`, `account_registered`, `inventory_validation_failed`, `inventory_cache_summarised`, `backoffice_section_viewed`, `backoffice_flow_abandoned` | Purchasing, replenishment rates, morning expiry list, catalogue and registration policy, validation backlog, hourly cache health, weekly navigation |

Batch events are still written at the moment the fact occurs. The daily or hourly job is the consumer, not a delay before the event exists. An inbound receipt that arrives already inside the expiry window writes `supply_expiry_flagged` in that request with `trigger` `receipt`, and the morning sweep writes `trigger` `daily_sweep`. Both travel on the batch pipeline because the disposal list is a morning decision. The receipt screen reads `expires_on` on the batch row if it needs to warn the receiver immediately.

## 9. Throttle and debounce

| Event | Rule |
| --- | --- |
| `stock_threshold_triggered` | On the crossing, then at most once per clinic, product, and band per UTC day while it stays below the minimum. A fall from healthy to zero emits a single `out` event. |
| `supply_expiry_flagged` | At most once per lot and clinic per UTC day. |
| `api_latency_recorded` | Always at 500 milliseconds or more. Otherwise about 1 in 20. |
| `inventory_cache_summarised` | One row per cache key per hour. |
| `backoffice_section_viewed` | One second debounce on route changes. |
| `backoffice_flow_abandoned` | Ignore mounts shorter than 2 seconds. One event per abandoned form. |
| `client_exception_captured` | Suppress the same section and error name for 60 seconds in the tab. |
| Every other event | One event per fact. No sampling. |

## 10. Risks and exclusions

Discarded events:

| Discarded | Why |
| --- | --- |
| A separate waste event for `expiry_waste` | That consumption is already `outbound_order_created` with `consumption_type` `expiry_waste`. A second event would double-count the units. |
| A cache event on every hit | The decision only needs the hourly ratio. Per-request hits would dominate the volume and the cost. |
| Profile updates | `PUT /profiles/me` carries name, phone, and address. Those are personal data, and they do not answer a supply decision. |
| Password changes and the raw value of `PUT /users/{user_id}` | The body can contain a password and an email. Access changes that matter here are login success, login failure, session expiry, and registration. |
| Incident file contents and the uploaded filename | Both can carry a person. `incident_analysis_completed` keeps the row count, the duration, and whether the file was the sample. |
| IP address and the raw JWT | They do not identify a clinic or a supply decision, and they are credentials or personal-network data. |
| Keystroke and field-value events | The abandon event stores the step name. Storing the typed vendor or quantity would recreate a free-text channel. |
| Patient-linked consumption | The briefing forbids it. Department is the only clinical context. |
| Using telemetry as the shelving lock for expiry | The batch row's `expires_on` is what the receipt screen reads. Telemetry is the morning list. |
| Emitting the global `current_stock()` total as the threshold | It hides one clinic's shortage behind another clinic's surplus. |

Remaining risks:

- The clinic directory is a documented table, not a database table. A wrong id-to-country assignment would put a US receipt in the UK rollup. Replace the table with a clinic table before the executive report trusts country totals.
- `message_scrubbed` can still contain an unusual personal string that is not an email and not a long digit run. The 200 character cap and the closed allowlist limit the damage. The stack is dropped.
- `vendor_name` is free enough for a real organisation and tight enough to reject a sentence. A vendor that uses characters outside the pattern has to be stored in the operational row under a normalised form, or the inbound event will fail validation and must not be silently rewritten.
- Server clocks need to be UTC. `days_to_expiry` and the daily debounce both use UTC dates. A clinic-local date would double-fire around midnight for UK and US sites.

## 11. What to build first

The design files do not change the application. The implementation order below is the one that makes each mandatory event true.

1. Add `X-Request-Id` on every API response and `X-Session-Id` from `sessionStorage` key `healthcore.session.id`, created at login and cleared by `logout`.
2. Add `country_for_clinic(clinic_id)` from the directory in section 3, and the category map in section 4.
3. On the three inventory write routes, inspect the raw JSON. A body that contains `current_stock`, `stock`, `quantity_on_hand`, or `on_hand` returns 403 and emits `direct_stock_edit_rejected`. Apply the same 403 to `PUT` or `PATCH /inventory/products/{supply_id}` and to `POST /inventory/stock`.
4. Add `department` to `SupplyConsumptionCreate` using the four-value enum. `outbound_order_created` and `outbound_order_rejected` wait until that field is present.
5. Add a `SupplyBatch` row with `product_id`, `clinic_id`, `lot_id`, and `expires_on`, and point the inbound order at it. Expiry lives on the batch that belongs to the product.
6. After each outbound commit, compute clinic-scoped stock and apply the threshold rule. Keep `current_stock()` as the source of the existing 400 and of `global_stock_after`.
7. Teach `authenticate` to distinguish `unknown_user`, `bad_password`, and `inactive_user` internally, while the HTTP body stays `Incorrect email or password`. Teach `get_current_user` to recognise an expired signature.
8. Add hit, miss, and invalidation counters to `TtlCache`, and normalise paths inside `timing_middleware` before the latency sample.
9. Send browser events only to `POST /telemetry/events`, and reject server event types on that route.
10. Point `emit` at a single spool. Mandatory events and the opportunities in this catalogue share it, so the later capture project has one contract.

## 12. Counts

- Total events: 18
- Mandatory, from the HealthCore briefing: 5
- Identified opportunities: 13
- Categories: business (7), authentication (4), errors (3), performance (2), navigation (2)

