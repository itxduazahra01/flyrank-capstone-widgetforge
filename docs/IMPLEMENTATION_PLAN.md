# Implementation Plan — Embeddable Widget & Lead-Capture Platform

## 1. Outcome and scope

Build a local-first, multi-tenant platform where an authenticated owner creates a widget and receives an embed snippet. A visitor can load that widget from any permitted external origin, submit it safely, and the owner can inspect the stored, geo-enriched submission and aggregate statistics.

Recommended implementation lane: **Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, Docker Compose, and pytest**. This keeps request validation, OpenAPI documentation, dependency injection, and async I/O straightforward while satisfying every capstone requirement at no cost.

The core product includes:

- Authenticated, tenant-isolated widget CRUD and dashboard APIs.
- A versioned public JavaScript bundle plus a small public widget-config endpoint.
- A CORS-enabled, validated public submission API.
- Per-IP and per-widget rate limiting, honeypot spam detection, payload limits, and idempotent submission handling.
- IP-to-geo enrichment with provider A → provider B fallback, without blocking storage if both fail.
- A non-critical notification side effect that runs off the request path and cannot turn a successful submission into a failure.
- A plain second-origin customer test page, deterministic automated tests, and evaluator-ready documentation/evidence.

Explicit non-goals for the first release:

- A drag-and-drop form-builder UI, production CDN/hosting, real transactional email, CAPTCHA, real-time dashboard updates, targeting rules, and GDPR workflow. The API supports one or two widget types only; prove the platform pattern before expanding it.

## 2. Architectural decisions

| Concern | Decision | Why |
|---|---|---|
| API framework | FastAPI with route/controller, service, repository, and model/schema layers | Keeps HTTP concerns separate from business logic and persistence. |
| Persistence | PostgreSQL in Docker Compose; Alembic migrations | Meets real-persistence/migration requirements and supports tenant-safe indexed queries. |
| Authentication | JWT bearer tokens for seeded demo users | A simple, demonstrable authenticated owner path; ownership comes from the token, never a request body. |
| Tenant boundary | `tenant_id` on widgets and submissions; every owner query filters by authenticated tenant | Makes tenant isolation database-query invariant rather than a UI convention. |
| Public identity | Opaque UUID widget public IDs | Avoids exposing sequential primary keys in snippets and public endpoints. |
| Validation | Pydantic models, field definitions held in widget configuration, request-size middleware | Rejects malformed/unknown/oversized input before business logic. |
| Spam control | Hidden honeypot field plus timing-neutral generic response | Deterministic, free bot defence. |
| Rate limiting | Redis-free in-memory sliding/fixed window limiter keyed by `IP + widget_public_id`, injectable fake for tests | Meets local scope; expose its limitation in README. Use Redis only as an optional stretch/production replacement. |
| Geo enrichment | `GeoProvider` interface; ip-api provider first, ipapi.co second | Providers are swappable and deterministic fakes can prove fallback behaviour. |
| Side effect/background job | Persist an `outbox_event` with the submission, then FastAPI background worker processes it with retry/status fields | Storage remains durable before notification; side effect is off request path and failures are observable. |
| Idempotency | Required/accepted `Idempotency-Key` header on public submissions, unique per widget | Browser/network retries return the original result rather than creating duplicate leads. |
| Widget delivery | Static `widget.v1.js` served with immutable cache headers; config endpoint has a short TTL and ETag | Mirrors CDN behaviour locally without a CDN. |

## 3. Repository layout

Create the capstone as its own public repository named `flyrank-capstone-widget-platform`. Within that repository, use this layout:

```text
.
├── app/
│   ├── api/                 # FastAPI routes and HTTP dependencies
│   │   ├── auth.py
│   │   ├── widgets.py       # authenticated owner endpoints
│   │   ├── public.py        # config, submission, CORS/preflight
│   │   └── dashboard.py
│   ├── core/                # settings, JWT, CORS policy, logging, errors
│   ├── db/                  # engine/session, ORM models, repositories, migrations
│   ├── schemas/             # Pydantic request/response contracts
│   ├── services/            # widget, submission, dashboard business logic
│   ├── integrations/        # geo providers and notifier implementations
│   ├── workers/             # outbox processing/retry logic
│   ├── static/widget.v1.js  # browser bundle loaded by customer sites
│   └── main.py
├── alembic/                 # generated migration history
├── customer-site/index.html # plain HTML page served on a second local port
├── scripts/seed_demo.py     # reproducible tenants/users/widgets/demo rows
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── capstone.yaml
├── EVIDENCE.md
└── BUILDLOG.md
```

Keep `app/api` thin: it parses HTTP, invokes one service, and maps known errors to JSON responses. Repositories contain SQL only. Services own authorization checks, idempotency, enrichment orchestration, and transaction boundaries. Integration adapters never import route code.

## 4. Data model and migrations

Use UUID primary keys (or internal UUIDs plus a distinct public UUID). All timestamps are UTC `timestamptz` values.

### `tenants`

`id`, `name`, `created_at`.

### `users`

`id`, `tenant_id` FK, `email` (unique), `password_hash`, `created_at`.

Seed at least Tenant A/Alice and Tenant B/Bob for isolation demonstrations.

### `widgets`

`id`, `public_id` (unique), `tenant_id` FK, `widget_type`, `title`, `description`, `form_fields` JSONB, `button_text`, `display_options` JSONB, `is_active`, `config_version`, `created_at`, `updated_at`.

- Start with `signup` and optionally `contact`; require one form definition schema for each type.
- `form_fields` stores allowed field names, labels, input types, `required`, and bounded validation constraints. Do not accept arbitrary server-side fields merely because a client sends them.
- Increment `config_version` on public-config-affecting updates. It becomes the ETag/version input.
- Index `(tenant_id, created_at)` and unique `public_id`.

### `submissions`

`id`, `tenant_id` FK, `widget_id` FK, `idempotency_key`, `payload` JSONB, `source_origin`, `ip_hash` (not raw IP unless there is a clear local-demo reason), `geo_country`, `geo_city`, `geo_provider`, `spam_status`, `created_at`.

- Unique constraint on `(widget_id, idempotency_key)` when a key is supplied.
- Index `(tenant_id, created_at)`, `(widget_id, created_at)`, and `(tenant_id, geo_country)` for dashboard queries.
- Persist only the submitted fields allowed by the widget. Exclude the honeypot field from stored payloads.

### `outbox_events`

`id`, `event_type`, `submission_id` FK, `status` (`pending|processing|sent|failed`), `attempt_count`, `last_error` (sanitized), `available_at`, `created_at`, `updated_at`.

Create this row in the same transaction as a successful submission. Index `(status, available_at)` for efficient worker polling. A retry cap (for example 3 attempts) and an error log/alert fulfils the shared background-job requirement while retaining a clear local implementation.

## 5. API contract

Use `/api/v1` for authenticated APIs and `/public/v1` for browser-facing APIs. Return JSON errors consistently:

```json
{"error":{"code":"validation_error","message":"...","details":[...]}}
```

| Method and route | Auth | Behaviour / success | Key failure responses |
|---|---|---|---|
| `POST /api/v1/auth/login` | no | Returns demo JWT | `401` invalid credentials |
| `POST /api/v1/widgets` | bearer JWT | Create a widget and return embed snippet | `401`, `422` |
| `GET /api/v1/widgets` | bearer JWT | List only caller tenant widgets | `401` |
| `GET /api/v1/widgets/{id}` | bearer JWT | Return owned widget | `401`, `404` (including other tenant's ID) |
| `PATCH /api/v1/widgets/{id}` | bearer JWT | Update owned widget; bump config version | `401`, `404`, `422` |
| `DELETE /api/v1/widgets/{id}` | bearer JWT | Soft-disable or delete owned widget | `401`, `404` |
| `GET /api/v1/widgets/{id}/embed` | bearer JWT | Return `<script src=".../widget.v1.js?id={public_id}"></script>` | `401`, `404` |
| `GET /public/v1/widgets/{public_id}/config` | public | Small safe rendering configuration | `404`; CORS-aware; `304` for matching ETag |
| `GET /widget.v1.js` | public | Versioned JS bundle | `200`, immutable long-lived cache |
| `OPTIONS /public/v1/submissions` | public | CORS preflight | `204` with allowed headers/methods for an allowed origin |
| `POST /public/v1/submissions` | public | Validate, protect, enrich, persist, queue event; returns `201` | `400/422`, `413`, `429`; never `500` for bad input/upstream geo/notification failure |
| `GET /api/v1/submissions` | bearer JWT | Paginated tenant-only submission table; filters by widget/date | `401` |
| `GET /api/v1/dashboard/summary` | bearer JWT | Counts-over-time, per-widget totals, geo breakdown | `401` |

Public submission request shape:

```json
{
  "widget_id": "public-widget-uuid",
  "fields": {"email": "visitor@example.com", "name": "Ada"},
  "website": ""
}
```

Headers: `Content-Type: application/json`, `Idempotency-Key: UUID`. The server derives client IP using a carefully configured trusted-proxy setting; in local development it can use a test-only header or loopback fallback. Limit the raw request body before JSON parsing (for example 16 KB). Validate widget existence/active status and validate `fields` against that widget’s stored field schema. Reject unknown fields, bad types, missing required fields, malformed e-mail, excessive string lengths, and excessive field counts.

## 6. Request flows

### Owner management flow

1. Seeded owner logs in and receives a JWT containing user and tenant IDs.
2. Owner creates/updates a widget through authenticated routes.
3. The service sets ownership from the JWT and returns a generated snippet using the public UUID.
4. Every read/update/delete query constrains `tenant_id`; cross-tenant access returns `404` to avoid object enumeration.

### Embed and render flow

1. Customer adds `<script src="http://localhost:8000/widget.v1.js?id=PUBLIC_ID"></script>` to `customer-site/index.html`.
2. The bundle reads `document.currentScript`, extracts `id`, creates an isolated root/container, and fetches `/public/v1/widgets/{id}/config`.
3. It renders only the configured safe fields using DOM APIs (`textContent`, property assignment), never untrusted HTML.
4. The config response includes `Cache-Control: public, max-age=300, must-revalidate` and an ETag based on `config_version`; respond `304` when applicable.
5. Serve `widget.v1.js` with `Cache-Control: public, max-age=31536000, immutable`. A bundle release changes the filename/reference to `widget.v2.js`.

### Hardened public submission flow

1. CORS middleware accepts only explicitly configured customer-site origins in development; handle `OPTIONS` before submission logic. Do not use credentialed wildcard CORS.
2. Enforce body-size limit, JSON media type, and Pydantic structure at the boundary.
3. Load active widget by public ID. Apply rate limit on `hash(client_ip):widget_id`; return `429` plus `Retry-After` when the configured burst is exceeded.
4. If `website` honeypot is filled, return a neutral accepted/rejected response without storing a normal lead and without exposing the signal.
5. Check idempotency record before all irreversible work. Return the saved submission representation for a duplicate key.
6. Ask geo provider A; on timeout/non-success/malformed response ask provider B. Catch provider errors and continue with `geo=null` when both fail. Use short timeouts and never log an IP or secret in detail.
7. In one DB transaction, create the submission and matching pending outbox event.
8. Schedule the outbox worker after commit. Return `201` immediately. Notification failures update event state and are logged/alerted, but cannot change the stored submission or its response.

## 7. Implementation phases and gates

### Phase 0 — repository and local baseline (1–2 hours) — **Complete**

1. Create the separate public repository, MIT license, `.gitignore`, `.env.example`, README skeleton, BUILDLOG, EVIDENCE, and `capstone.yaml` before code.
2. Add Docker Compose for PostgreSQL and the API; create a one-command local boot path and an independent seed command.
3. Set up settings validation, structured safe logging, health endpoint, SQLAlchemy session, Alembic, and pytest.

Gate: a clean checkout can boot the API/database and run a trivial test without secrets committed.

### Phase 1 — design, identity, and tenant-safe CRUD (4–6 hours) — **Complete**

1. Put the concise design rationale from sections 1–6 into README and draw the three actor/request paths.
2. Add migrations for tenants, users, widgets, submissions, and outbox events.
3. Implement login and auth dependencies; never take tenant ID from the request body or query string.
4. Implement widget schema validation and CRUD with tenant-filtered repository methods.
5. Implement snippet generation and seed Alice/Bob plus a demo widget.
6. Add tests proving Alice cannot read, update, delete, list, or see submissions for Bob’s widget.

Gate: an authenticated owner creates a widget and receives its one-line snippet; cross-tenant access is demonstrably blocked.

### Phase 2 — hardened submission path (14–20 hours) — **Complete**

1. Create public config lookup plus a field-schema validator that is driven by the stored widget definition.
2. Add exact CORS configuration, preflight handling, body-size middleware, error mapping, and origin tests.
3. Add the public submission endpoint and rate limiter; ensure individual limiter keys avoid one widget starving all others.
4. Add the honeypot, active-widget check, payload normalization, and idempotency key repository transaction.
5. Implement `GeoProvider`, provider A/B adapters, timeout/error handling, and deterministic fake providers for tests.
6. Create submission and outbox event atomically; add worker retry/status paths and a configurable forced notifier failure.

Gate: a cross-origin curl/browser submission stores an enriched row; provider failure, notification failure, and retried requests cannot lose or duplicate the lead.

### Phase 3 — delivery, dashboard, and customer site (12–16 hours) — **Complete**

1. Build `widget.v1.js` with no framework dependency. It loads config, renders safely, posts JSON with an idempotency key, and presents success/error states without exposing internals.
2. Serve correct cache headers and ETag/304 behaviour. Document the version-bump release procedure.
3. Add `customer-site/index.html`; serve it on port 8080 while API runs on 8000 to prove cross-origin loading/submission.
4. Implement paginated submission list and SQL aggregation endpoints: daily count, counts by widget, and country/city breakdown.
5. Add an intentionally plain dashboard HTML page only if helpful for the demo; API responses plus a simple table are sufficient.
6. Complete test suite and paste each verifiable proof into EVIDENCE as it passes.

Gate: the widget renders from the second origin, all automated tests pass, and dashboard statistics show the new submission.

### Phase 4 — acceptance rehearsal and polish (2–3 hours) — **Complete**

1. Seed deterministic demo data and write exact run/seed/test commands in README and `capstone.yaml`.
2. Rehearse the six-minute sequence in section 10 below twice on a clean terminal/browser session.
3. Capture real outputs for every definition-of-done line and every acceptance probe in EVIDENCE.
4. Verify no `.env`, token, password, raw IP, large artifact, virtual environment, or dependency directory is tracked.

Gate: all six evaluator probes pass in sequence and an unfamiliar reviewer can run the project from README.

## 8. Test plan mapped to acceptance probes

| Test | Setup/action | Expected result |
|---|---|---|
| Cross-origin render | Serve customer site on `:8080`, API on `:8000`, load snippet | Bundle and config load; form renders. |
| CORS preflight | Send `OPTIONS` with allowed origin/request headers | `204` and exact allow headers/methods/origin. |
| CORS rejection | Use disallowed origin | No permissive CORS header; browser blocks request. |
| Valid public submit | Valid fields and idempotency key | `201`, tenant/widget-linked submission visible in dashboard. |
| Malformed input | Invalid JSON/type/missing required/unknown field | Clean JSON `400` or `422`; no row; no `500`. |
| Oversized body | Payload over configured size | `413`; no row. |
| Tenant isolation | Tenant A requests Tenant B IDs/list/statistics | `404` or empty tenant-safe result; never B data. |
| Rate limit | Burst same IP + widget | Threshold produces `429`/`Retry-After`; a distinct legitimate key/request succeeds. |
| Honeypot | Fill `website` | Neutral reject/drop; no standard lead stored. |
| Geo fallback | Fake A fails and fake B responds | Stored submission includes B geo/provider. |
| Geo total failure | Both fakes fail | `201`; stored submission has null geo. |
| Notification failure | Notifier raises | `201` and stored submission; failed outbox event recorded/retried. |
| Idempotency | Replay same key/body | No second row/event; response represents original submission. |
| Cache delivery | Fetch bundle/config and repeat with `If-None-Match` | Immutable bundle header; config short TTL and `304`. |
| Dashboard aggregation | Seed multiple rows/widgets/countries | Correct tenant-only totals, timeline, widget, and geo groups. |

Use fakes/fixtures for clock, client IP, geo providers, rate limiter, and notifier. Unit tests cover services and adapters; integration tests use a real disposable PostgreSQL service; browser/e2e test verifies rendering and form submission from the second origin. No test should rely on a live geo API.

## 9. Configuration, operations, and security checklist

`.env.example` should document safe placeholders for:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://widget:widget@db:5432/widget_platform
JWT_SECRET=replace-with-a-long-development-secret
ALLOWED_WIDGET_ORIGINS=http://localhost:8080
MAX_SUBMISSION_BYTES=16384
RATE_LIMIT_MAX_REQUESTS=5
RATE_LIMIT_WINDOW_SECONDS=60
GEO_PROVIDER_A_ENABLED=true
GEO_PROVIDER_B_ENABLED=true
NOTIFIER_MODE=console
```

- Add `.env`, credentials, local volumes, test artifacts, `__pycache__`, and virtual environments to `.gitignore` before the first commit.
- Hash passwords; never log credentials, JWTs, API keys, form bodies containing PII, or raw IP addresses. Store a salted/rotating HMAC of IP if rate limiting/audit requires persistence.
- Configure trusted proxy behaviour explicitly. Do not blindly trust `X-Forwarded-For` from public clients.
- Set outbound geo-provider timeouts, tolerate malformed responses, and cap retries. The enrichment call must not become an availability dependency.
- Limit the widget config to safe presentation data. Escape/render via DOM APIs to prevent an owner-supplied title/label becoming injected HTML.
- Return generic public errors; keep detailed exception messages in sanitized server logs only.
- Document the local in-memory limiter’s multi-instance limitation and the Redis replacement path in README.

## 10. Demo script (six minutes)

1. Log in as Alice; create a signup widget and show the returned embed snippet.
2. Open the customer site on `http://localhost:8080`; show the widget loaded from the API origin and submit a valid lead.
3. Open Alice’s dashboard endpoint/table; show the lead, widget attribution, and geo enrichment.
4. Send an invalid and oversized submission; show clean JSON 4xx responses. Demonstrate a disallowed origin’s CORS behaviour.
5. Fire a small burst to get `429`, then show a normal permitted request still works.
6. Toggle geo provider A down; submit and show provider B enrichment. Toggle both down; show storage still succeeds without geo.
7. Force notifier failure; show successful public response and stored submission/outbox failure state. State: “Non-critical failures never break the main path.”

## 11. Submission pack and evidence

Before final submission, ensure these required files exist at repository root:

| File | Completion standard |
|---|---|
| `README.md` | Problem, architecture diagram, local run/seed/test commands, API usage/examples, demo instructions, and honest limitations. |
| `capstone.yaml` | Exact one-command `run`, `seed`, and `test` values; base URL and endpoints to probe. |
| `EVIDENCE.md` | One real pasted test output, curl transcript, or log line for every core Definition-of-Done item. |
| `BUILDLOG.md` | Dated AI assistance record: prompt/use, what was accepted, what was corrected, and why. |
| `.env.example` | Every required configuration key, safe placeholder values only. |

Suggested `capstone.yaml` shape (final commands must match the actual project):

```yaml
run: docker compose up --build
seed: docker compose exec api python scripts/seed_demo.py
test: docker compose exec api pytest
base_url: http://localhost:8000
endpoints:
  - POST /public/v1/submissions
  - GET /public/v1/widgets/{public_id}/config
  - GET /api/v1/dashboard/summary
```

## 12. Definition-of-done cross-check

- [ ] Authenticated widget CRUD is validated and tenant-isolated.
- [ ] Snippet is generated per widget.
- [ ] Public config is small, CORS-aware, cached, and version-aware.
- [ ] Versioned bundle loads and renders from a second origin.
- [ ] Public submission supports valid cross-origin requests and preflight.
- [ ] Invalid/malformed/oversized input yields intentional 4xx JSON errors.
- [ ] Valid submission is safely stored against correct widget and tenant.
- [ ] Rate limit produces `429` under burst without taking the service down.
- [ ] Honeypot demonstrably blocks/drops spam.
- [ ] Provider A → B fallback enriches; both unavailable still stores submission.
- [ ] Notification failure does not block storage/success.
- [ ] Durable outbox/background worker has retry and failure visibility.
- [ ] Idempotent retry creates only one submission/event.
- [ ] Dashboard shows tenant-only list, time count, widget stats, and geo breakdown.
- [ ] Automated tests cover CORS, payload failures, rate limit, spam, fallback, side-effect failure, idempotency, tenant isolation, and rendering.
- [ ] README, `capstone.yaml`, EVIDENCE, BUILDLOG, and `.env.example` are complete; no secrets are tracked.

## 13. Build order summary

Do not start with the widget UI. The risk order is: establish repository/migrations/auth → prove tenant-safe widget CRUD → harden and test public submission path → add enrichment/outbox/idempotency → deliver the bundle/config → add dashboard → collect evidence and rehearse failures. This order keeps the difficult public-internet behaviour testable before presentation work begins.
