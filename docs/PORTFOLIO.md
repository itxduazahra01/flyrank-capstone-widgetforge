# Portfolio & CV Positioning

## What makes this project stand out

Build the core exactly as planned, then choose **one** differentiated enhancement. A finished, measured enhancement is more valuable than several incomplete features.

Recommended enhancement order:

1. **Observability pack (best CV return):** correlation IDs across public submission/outbox logs, structured JSON logs, `/health` and `/ready` endpoints, and counters for submissions, rejected requests, provider fallback, and notification failures.
2. **Production-grade distributed rate-limit adapter:** retain local memory implementation but add a Redis-backed adapter behind the same interface, Docker profile, and contract tests. Clearly compare the two in README.
3. **Webhook delivery UX:** signed webhook payloads (`timestamp + HMAC`), retry/replay-safe event IDs, delivery status visible in dashboard, and an example receiver.
4. **Targeting rules:** show widget only on matching path, after delay, or once per browser.
5. **Real-time dashboard:** SSE for live submissions, only after persistence and tests are stable.

Avoid building AI features just to say “AI.” If one is added, it needs a per-call budget, grounded inputs, opt-in disclosure, stored evaluation cases, and a graceful no-AI fallback.

## Suggested CV bullets

Use only claims demonstrated by the final repository:

- Built a multi-tenant embeddable lead-capture platform with FastAPI, PostgreSQL, Docker, and a versioned JavaScript widget delivered across origins.
- Hardened a public form-submission API with strict schema validation, CORS/preflight support, payload limits, honeypot spam defense, rate limiting, and idempotent writes.
- Designed resilient integrations using geo-provider fallback and a transactional outbox, ensuring external-service failures never lost accepted leads.
- Implemented tenant-scoped analytics and deterministic integration tests covering authorization isolation, abuse scenarios, dependency failures, and browser rendering.

## README/recruiter narrative

“WidgetForge lets any site embed a lead form in one script tag. Its backend is designed for the open internet: untrusted requests are validated and rate-limited, leads stay tenant-isolated, and provider/notification failures degrade safely rather than losing customer data.”

## Portfolio evidence to include

- A 60–90 second screen recording: create → embed on second origin → submit → dashboard → kill geo provider → show success/fallback.
- Architecture diagram and ADR index.
- CI badge with tests passing.
- Screenshot or GIF of the second-origin widget and dashboard.
- A “failure modes tested” section that links to specific test names.

## Interview talking points

- Why a modular monolith is the right first choice and what would trigger an extraction.
- Why the outbox event is written in the same transaction as the lead.
- How CORS differs from authorization and why public APIs still need abuse controls.
- Why idempotency belongs at the write boundary.
- How short config caching and immutable versioned bundle caching solve different problems.
