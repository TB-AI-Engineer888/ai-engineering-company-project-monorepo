# Caching report

HealthCore backoffice and inventory API. Measurements below were taken on a local SQLite database with the timing taken around `load_product_rows` and `load_order_rows`. Each figure is from 15 runs after one warmup. The small set is the existing clinic seed. The large set is that seed plus `services/seed_clinic_load.py` (30,000 additional supplies, 5 deliveries and 3 consumptions each).

## Frontend decisions

The public clinic site in `uis/healthcore-website` is static HTML, so lazy loading and `useMemo` are applied in the Next.js backoffice.

**Lazy loaded**

- `IncidentAnalyzer` on `/incidents`, through `next/dynamic`. The operations overview only links to this route. The analyzer pulls in the file dropzone and the analysis summary, and neither is needed for the first paint of the overview or the supply list. The route heading is not blocked on that chunk. Loading state: "Loading the incident analyzer…".
- `OrdersTable` on `/backoffice/inventory/orders`, through `next/dynamic`. The order history is a client table of every delivery and consumption. Staff open it from the overview; it is not on the first screen. The page heading renders with the route, and the table chunk loads after. Loading state: "Loading supply orders…".

**Memoized**

`ProductsTable` sorts the medical-supply catalog with `compareSuppliesByNeed` inside `useMemo`. The dependency array is `[supplies]`.

The sort is not a display-string format. Out-of-stock rows come first, then low stock (1–10), then healthy stock (11 or more), and ties break on the supply name. After the load seed that catalog is 30,006 supplies. `useMemo` runs the sort only when `supplies` changes. A later render of the table that still holds the same array, such as the render that clears the loading flag, does not sort again.

Estimated benefit: the O(n log n) band-and-name sort is skipped on those extra renders. The network read of the catalog is still the slow part.

## Backend decisions

Every route, with cost, how often the backoffice calls it, and how often the data changes.

| Route | Cost | How often it is called | How often the data changes | Cached |
| --- | --- | --- | --- | --- |
| `GET /health` | A static JSON object | Liveness checks | Never | No |
| `GET /` | A static JSON object | Rare | Never | No |
| `POST /auth/login` | Password check | Once per session | Credentials change rarely | No. Not a read |
| `GET /auth/me` | One user plus that user's profile | Each signed-in page load | When that profile changes | No. Per person |
| `POST /users` | Inserts a user | Registration | On each registration | No. Write |
| `GET /users` | Every user record | Occasional admin use | On registration and edits | No. Sensitive staff list |
| `GET /users/{user_id}` | One user | Occasional | When that user changes | No. Per person |
| `PUT /users/{user_id}` | Update | Occasional | On each edit | No. Write |
| `DELETE /users/{user_id}` | Delete | Rare | On each delete | No. Write |
| `GET /profiles/me` | One profile | Account page | When that person edits it | No. Per person |
| `PUT /profiles/me` | Update | Account save | On each save | No. Write |
| `GET /api/incidents/sample` | Sends one sample file | Occasional | The sample file is static | No |
| `POST /api/incidents/analyze` | Parses an uploaded CSV | Each upload | Every file is different | No |
| `GET /api/incidents/results` | Last upload held in process memory | After an analysis | Replaced by the next upload | No. Session result |
| `GET /api/incidents/results/export` | Last upload as CSV | After an analysis | Replaced by the next upload | No. Session result |
| `GET /inventory/products` | All supplies plus grouped sums of every delivery and consumption | Every visit to Medical supplies | When a supply, delivery, or consumption is recorded | Yes. 60 seconds |
| `POST /inventory/products` | Inserts one supply | When a supply is added | On each insert | No. Clears the inventory cache |
| `GET /inventory/products/{supply_id}` | One supply and that supply's stock | Not used by the supplies page | When that supply's movements change | No. See below |
| `POST /inventory/orders/inbound` | Inserts one delivery | When a shipment is logged | On each delivery | No. Clears the inventory cache |
| `POST /inventory/orders/outbound` | Stock check, then one consumption | When use or waste is logged | On each consumption | No. Clears the inventory cache |
| `GET /inventory/orders` | Every delivery and consumption, with the supply row, sorted in Python | Every visit to Supply orders | When a delivery or consumption is recorded | Yes. 45 seconds |

**`GET /inventory/products`**

- Cost, measured: 0.50 ms median (minimum 0.44 ms) with 6 supplies, 7 deliveries, and 3 consumptions. After the load seed (30,006 supplies, 150,007 deliveries, 90,003 consumptions) the minimum of 15 runs was 367.73 ms and the median was 452.43 ms. Every run stayed above 200 ms. The work is two grouped sums across every movement, then one row per supply.
- Call frequency: the Medical supplies screen loads this on each visit, and staff return to that screen through a shift. Same path, no query string, same body for every signed-in staff member.
- Stability: the catalog changes when someone adds a supply or logs a movement, not on each read.
- TTL: 60 seconds.
- Invalidation: `POST /inventory/products`, `POST /inventory/orders/inbound`, and `POST /inventory/orders/outbound` clear every `inventory:` key after the commit. A rejected consumption does not write and does not clear the cache.
- Cache key: `inventory:products`. It is not keyed by user. The JSON has no profile and no session. Authentication still runs before a cached body is returned, so a signed-out request stays 401.
- After the load seed, a cache hit that rebuilds the 30,006 product models was 53.32 ms median (minimum 51.60 ms), against 452.43 ms for the query.

**`GET /inventory/orders`**

- Cost, measured: 1.12 ms median (minimum 0.97 ms) on the small seed (10 movement rows). After the load seed (240,010 order rows) the minimum of 15 runs was 6,457.89 ms and the median was 6,675.67 ms. Every run stayed above 200 ms. This is the slow repeated read in the API.
- Call frequency: the Supply orders screen loads this list each time it is opened, often the same URL in a short window while staff review the clinic.
- Stability: the history changes only when a delivery or consumption is stored.
- TTL: 45 seconds.
- Invalidation: the same three writes clear `inventory:orders` together with the product list, because a delivery changes stock and the history at the same time.
- Cache key: `inventory:orders`. Shared across staff. The rows include the `user_uuid` of the person who recorded the movement. That identifier is already part of the order history shown to every signed-in staff member on this screen; it is not the caller's profile. Authentication still runs first.
- After the load seed, a cache hit that rebuilds the 240,010 order models was 2,785.93 ms median (minimum 2,203.16 ms), against 6,675.67 ms for the query.

The timing middleware from the project brief is on the API (`api.timing`). It logs `METHOD path → status | milliseconds` for every request. The table above uses the query medians, which exclude login cost so the before and after figures are the inventory work itself.

Row counts from the load seed: supplies 6 → 30,006, deliveries 7 → 150,007, consumptions 3 → 90,003. Names, categories, units, countries, vendors, clinics 1–12, and timestamps all vary. The startup seed is unchanged, and this loader does not run when the API starts.

## Tradeoffs acknowledged

`GET /inventory/orders` keeps a result for 45 seconds, and `GET /inventory/products` for 60 seconds. A cached stock total can be stale for that long if a write happens in another process, or if a future write path forgets to clear the cache. That window is acceptable for browsing clinic supplies between shipments. It is not acceptable for deciding whether a consumption can be recorded. `POST /inventory/orders/outbound` does not trust the cache: it reads `current_stock` from the database and rejects a quantity the clinic does not have. Logging a delivery or a consumption in this process also clears both keys immediately, so the next read on this API is not waiting on the TTL.

A bank balance, or a patient's own chart, would not get this treatment. A shared supply count used to review the storeroom can.

## What was not cached and why

`GET /profiles/me` was the personal route considered for a cache and rejected. Two staff members loading their own account receive different names. A shared key would hand one person's profile to the next caller. Keying it by user id would be safe and was still skipped: it is a single-row read, it changes when that person saves the account form, and the account page is not the screen being reloaded dozens of times a minute.

`GET /inventory/products/{supply_id}` was the inventory route considered and rejected. It is one primary-key read plus that supply's stock, and the supplies screen never calls it. The list endpoint already covers the repeated, aggregated read. Caching the single-supply route would add a second invalidation key for little time saved.

`GET /api/incidents/results` was rejected because it is the last uploaded file held in memory, not a stable clinic record.
