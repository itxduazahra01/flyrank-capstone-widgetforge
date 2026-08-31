# Architecture

## Chosen shape: modular monolith

One FastAPI service, one PostgreSQL database, and a separately served local customer page form the first release. Modules have strict dependency direction but are deployed together.

This is intentional: a solo capstone does not need independent scaling or the operations burden of microservices. Interfaces around geo and notification integrations preserve an extraction path if future traffic proves it necessary.

```text
Owner (authenticated)                         Visitor (untrusted browser)
        │                                                │
        ▼                                                ▼
 /api/v1/widgets, dashboard               widget.v1.js → public config
        │                                                │
        ▼                                                ▼
   API routes ────────────────► Submission service ◄── POST public submission
        │                                │
        ▼                                ├─ validation / CORS / rate limit / spam
 Services (business rules)                 ├─ GeoProvider A → GeoProvider B → no geo
        │                                └─ atomic submission + outbox event
        ▼                                                │
 Repositories / ORM                                         ▼
        │                                           background notifier worker
        ▼
    PostgreSQL
```

## Layers and responsibilities

| Layer | Owns | Must not own |
|---|---|---|
| API routes | HTTP parsing, auth dependency, response codes | SQL, geo fallback, notification policy |
| Services | authorization policy, transactions, idempotency, enrichment orchestration | framework request/response objects |
| Repositories | tenant-scoped persistence and aggregate queries | HTTP or provider calls |
| Integrations | geo/notifier adapter calls, timeouts, response translation | business authorization or DB transactions |
| Worker | claim/retry outbox events and record outcomes | public request success semantics |

## Request paths

### Owner path

JWT → route → tenant-scoped widget/dashboard service → repository → PostgreSQL.

### Embed path

`widget.v1.js?id=PUBLIC_ID` → public config endpoint → JSON config → safe DOM rendering. Bundle uses long immutable caching; config uses short TTL plus ETag.

### Submission path

Preflight/CORS → payload cap → validation → rate limit → honeypot → idempotency → geo fallback → transaction (submission + outbox) → background notification. The response does not wait for notification completion.

## Operational boundaries

- PostgreSQL is the source of truth for leads and outbox events.
- Provider timeouts are short and all provider errors are converted to a safe no-geo result after fallback.
- The initial in-memory rate limiter is suitable for one local process only. Redis is the documented production replacement.
- Notifications are at-least-once; notifier payloads require an event ID so receivers can deduplicate.

## Cache policy

| Resource | Header / behaviour | Reason |
|---|---|---|
| `widget.v1.js` | `Cache-Control: public, max-age=31536000, immutable` | New filename on release prevents stale bundle use. |
| Widget config | `Cache-Control: public, max-age=300, must-revalidate`, ETag | Fast loading without long-lived stale display configuration. |
| Authenticated dashboard | `Cache-Control: no-store` | Avoid browser/proxy caching of lead data. |

## Architecture validation

Architecture is considered successful when routes can be tested with fake providers, database queries never leak cross-tenant records, and the worker can fail without changing a previously returned successful submission response.
# Architecture

## Runtime services

Docker Compose runs four cooperating services: PostgreSQL, a one-shot Alembic `migrate` job, the FastAPI `api`, and a restartable `worker`. API and worker startup are gated on successful schema migration. The worker polls the transactional outbox and retries failed notifications without blocking public lead capture.

## Enrichment and analytics

Geo enrichment is opt-in (`GEO_ENRICHMENT_ENABLED=true`) and uses ip-api followed by ipwho.is. Either provider can fail without rejecting a submission. Dashboard summaries include totals, per-widget/country aggregates, and a date-grouped submissions-over-time series.
