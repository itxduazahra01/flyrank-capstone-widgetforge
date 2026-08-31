# Test Strategy

## Testing principle

Prioritize scary cases over superficial coverage. Tests must be deterministic: no live geo API, mail server, clock, or rate-limit dependence.

## Test layers

| Layer | Examples | Tooling |
|---|---|---|
| Unit | Widget field validation, geo fallback, idempotency service, notification retry calculation | pytest with fakes |
| Integration | Repositories, migrations, transaction creates submission+outbox | pytest + disposable PostgreSQL |
| API | Auth, CORS preflight, 4xx errors, tenant isolation, rate limit | FastAPI TestClient/httpx |
| E2E | Second-origin page loads bundle/config and submits a lead | Playwright or browser-based manual script |

## Mandatory deterministic scenarios

1. Valid second-origin submission is stored and returned by owner dashboard.
2. Invalid JSON, invalid field, unknown field, missing field, and oversized body return intentional 4xx JSON—never 500.
3. Rate-limit burst returns `429` plus `Retry-After`; a non-abusive request still succeeds.
4. Filled honeypot is dropped/rejected without a visible spam oracle.
5. Geo A fails/B succeeds; both fail; neither case loses a valid submission.
6. Notifier throws; submission remains committed and failed outbox state is observable.
7. Duplicate idempotency key results in exactly one submission/outbox event.
8. Tenant A cannot inspect Tenant B through any widget, list, submission, or dashboard route.
9. ETag/config cache and immutable bundle headers are present.
10. Unsafe configuration text cannot become script/HTML in the rendered widget.

## Quality gates

- All tests green via the single documented command.
- New bug fixes include a regression test.
- Critical path tests use test doubles for integrations and are safe to run offline.
- `EVIDENCE.md` holds actual outputs for every capstone Definition-of-Done item.
