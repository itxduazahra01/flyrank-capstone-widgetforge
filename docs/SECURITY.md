# Security & Resilience Plan

## Threat model

| Threat | Control | Verification |
|---|---|---|
| Cross-tenant data access | Tenant from JWT; tenant predicate in every owner query | Alice cannot access Bob's widget/submissions. |
| Arbitrary cross-origin browser use | Explicit allow-list CORS and preflight handling | Allowed and disallowed origin tests. |
| Malformed/unbounded input | JSON/content-type checks, Pydantic schema, 16 KB body limit, field/string limits | Invalid and oversized payload tests. |
| Automated spam/flooding | IP+widget limiter and honeypot | Burst gets `429`; honeypot does not create lead. |
| Replay/network retry duplicate | Unique idempotency constraint and replay response | Same key creates one row/event. |
| Geo provider outage | Timeouts + A→B→no-geo fallback | Faked A/B outage tests. |
| Notification outage | Transactional outbox and retry worker | Forced notification error leaves lead stored. |
| Secret leakage | Environment-only settings, redacted logs, `.env` ignored | Secret scan/manual tracked-file check. |
| XSS through widget configuration | DOM `textContent`, no untrusted `innerHTML` | Malicious label renders as text. |
| Spoofed client IP | Trust forwarding headers only from configured reverse proxy | Unit test header trust policy. |

## Security baseline

- Passwords are hashed; tokens have expiry and a strong environment-provided signing secret.
- Public endpoints expose generic errors only; structured logs are sanitized of email, payload, token, raw IP, and secrets.
- Public config includes presentation/schema data only—never owner identity, secrets, or submissions.
- Rate-limit identifiers use a keyed IP hash if they leave process memory.
- The app has no credentials in version control. `.env.example` contains placeholders only.

## Explicit limitations

The local capstone limiter is process-local and has no distributed coordination. Production would use Redis or an API gateway/WAF. Authentication, consent/retention, audit logs, secret rotation, CSP/SRI, and full privacy compliance require a production design review before real customer data is processed.
