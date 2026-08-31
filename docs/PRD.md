# Product Requirements Document — WidgetForge

| Field | Value |
|---|---|
| Product | WidgetForge — Embeddable Lead-Capture Platform |
| Status | Pre-implementation |
| Version | 1.0 |
| Target release | Capstone MVP |
| Primary users | Small business/site owners and their website visitors |
| Technical owner | Solo developer |

## 1. Executive summary

WidgetForge enables a site owner to create a lead-capture widget, install it on any website with a single `<script>` tag, and view the safely stored submissions in a tenant-isolated dashboard.

The product’s differentiator is not visual form complexity; it is a backend designed for the open internet. The browser hosting the widget is untrusted, traffic can be abusive, external providers can fail, and multiple customers must never access one another’s leads. The MVP therefore prioritizes correctness, safe degradation, and verifiable engineering over UI polish.

## 2. Problem statement

Embedding a simple form on a third-party website looks easy until the backend must handle public traffic. A naïve implementation commonly has one or more of these failures:

- The widget works only on the developer’s own origin because CORS/preflight was not designed.
- Requests contain arbitrary or oversized fields and cause server errors.
- Spam or rapid submissions overwhelm the endpoint.
- A failed geo lookup or email/webhook prevents a valid lead from being stored.
- A retry creates duplicated leads.
- One customer can view another customer’s records through an incomplete authorization check.
- Cached JavaScript/configuration becomes stale or slows every page load.

WidgetForge addresses these risks with a small, demonstrable platform pattern: authenticated configuration, cached public delivery, hardened public writes, isolated persistence, and owner analytics.

## 3. Product goals

### Primary goals

1. Let an authenticated owner create and manage a reusable form widget.
2. Make installation one copyable script tag, with no manual configuration required on the customer page.
3. Allow a visitor to submit from a different web origin successfully and safely.
4. Ensure valid submissions are stored even when geo or notification dependencies fail.
5. Prevent common public-endpoint abuse and show that prevention with repeatable tests.
6. Provide sufficient dashboard data for an owner to confirm lead volume, source widget, and basic geography.
7. Make the system easy for a reviewer to run, test, and evaluate locally.

### Product quality goals

- Every request boundary returns intentional JSON responses and honest HTTP statuses.
- Tenant isolation is enforced by the backend and proven by tests.
- Non-critical failures never change a previously successful lead-capture outcome.
- All external dependency failure behaviour can be tested without network access.
- Documentation explains architecture choices, trade-offs, setup, limitations, and evidence.

## 4. Non-goals

The MVP will not include:

- A no-code drag-and-drop builder, arbitrary custom CSS, complex conditional forms, or more than one/two widget types.
- Billing, workspace invitations, SSO, production deployment, a paid CDN, or a custom domain.
- Guaranteed delivery/uptime, high-volume distributed rate limiting, or a production privacy/compliance programme.
- CAPTCHA, behavioral bot analysis, customer segmentation, A/B tests, or real-time notifications.
- AI-generated forms or AI lead scoring. These add cost/evaluation burden and do not strengthen the core engineering story.

## 5. Users, personas, and jobs-to-be-done

### Persona A: Owner Olivia

Olivia manages a small product or marketing site. She wants to collect newsletter signups or contact requests without writing a backend. She is comfortable copying a script tag but not debugging browser security errors.

**Job:** When I need to collect leads on my site, I want to configure and install a reliable form in one step so I can see incoming leads without maintaining public API infrastructure.

### Persona B: Visitor Victor

Victor visits Olivia’s website and enters details into a form. He expects the form to be quick, understandable, and safe. He should not see internal provider errors, credentials, or technical details.

**Job:** When I choose to contact or subscribe, I want a quick form that confirms whether my submission was accepted.

### Persona C: Evaluator Elena

Elena is reviewing the capstone/repository. She needs to validate setup, public API resilience, data isolation, and documented failure behaviour in minutes.

**Job:** When I assess the project, I want reproducible commands, tests, and evidence so I can verify claims without inferring implementation details.

## 6. Scope and release definition

### MVP scope

| Area | Included behaviour |
|---|---|
| Identity | Seeded users authenticate and receive a JWT; token determines tenant. |
| Widget management | Create, list, read, update, disable/delete widgets owned by caller. |
| Widget model | `signup` and/or `contact`; bounded schema-defined text/email fields, title, description, button text. |
| Installation | Owner receives one versioned script snippet per widget. |
| Public delivery | Widget bundle and public config served with intentional cache policy. |
| Public writes | CORS/preflight, payload limits, field validation, spam defence, rate limit, idempotency. |
| Enrichment | IP geo provider A with provider B fallback; no geo remains successful. |
| Side effect | Console notification or local Mailpit/webhook through transactional outbox and retry worker. |
| Dashboard | Tenant-only submission list, date counts, per-widget totals, geo breakdown. |
| Proof | Automated tests, plain second-origin page, README, evidence, build log, environment example. |

### Post-MVP candidates

Only consider these when all MVP acceptance criteria are green:

1. Observability pack: correlation IDs, structured logs, health/readiness, operational counters.
2. Redis-backed distributed limiter behind an adapter and Docker profile.
3. Signed webhooks, delivery history, and event replay protection.
4. Widget targeting rules or consent/retention controls.
5. SSE dashboard updates.

## 7. User stories and acceptance criteria

### Epic A — Account and tenant safety

**US-A1: Authenticate owner**

As an owner, I can log in with demo credentials and receive a bearer token so I can access my workspace.

Acceptance criteria:

- Valid credentials return `200` with an expiring token.
- Invalid credentials return a generic `401` JSON error.
- Credentials, tokens, and password hashes are never logged or returned beyond the token response.

**US-A2: Enforce tenant isolation**

As an owner, I can access only my own widgets, leads, and dashboard metrics.

Acceptance criteria:

- The backend derives tenant identity from JWT claims.
- Tenant A cannot read, update, delete, or list Tenant B’s objects, including dashboard aggregates.
- Cross-tenant object access returns `404`, not data or an authorization hint.
- Automated tests exercise every tenant-owned route against two seeded tenants.

### Epic B — Widget configuration and installation

**US-B1: Create widget**

As an owner, I can create a signup/contact widget with a safe field definition so I can collect the data I need.

Acceptance criteria:

- `POST /api/v1/widgets` validates widget type, title, button text, and bounded field schema.
- Each field has a unique safe name, type, label, required flag, and maximum length.
- Invalid definitions return `422` with per-field details; no widget is stored.
- A successful creation returns owner-safe widget data and opaque `public_id`.

**US-B2: Manage widgets**

As an owner, I can list, view, update, and disable/delete my widgets.

Acceptance criteria:

- List returns caller-tenant widgets only.
- Updating public rendering data increments `config_version`.
- Inactive/deleted widgets no longer accept public submissions and are unavailable from public config.
- Updates preserve tenant ownership and validate new configuration before save.

**US-B3: Receive an embed snippet**

As an owner, I can copy a one-line script tag for my widget.

Acceptance criteria:

- Endpoint returns `<script src="http://localhost:8000/widget.v1.js?id=PUBLIC_ID"></script>` (or configured base URL).
- It is generated for a widget owned by the authenticated caller only.
- Snippet exposes no tenant ID, secret, internal primary key, or dashboard data.

### Epic C — Public widget delivery and rendering

**US-C1: Load from another origin**

As a visitor, I can load the widget from a page served on a different origin.

Acceptance criteria:

- `customer-site/index.html` served on port 8080 loads the bundle from API port 8000.
- The bundle reads its script ID, retrieves public config, and renders the configured fields/button.
- Rendering uses DOM API text/property assignment; it never inserts owner-supplied strings through `innerHTML`.
- A missing/inactive public widget fails gracefully without breaking the host page.

**US-C2: Cache delivery efficiently**

As a site owner, I want the widget to have predictable, low-overhead asset delivery.

Acceptance criteria:

- `widget.v1.js` sends `Cache-Control: public, max-age=31536000, immutable`.
- A bundle change uses a new filename/version rather than replacing a supposedly immutable asset.
- Public config sends short-lived cache headers and an ETag; matching requests can receive `304`.
- Authenticated lead/dashboard responses use `Cache-Control: no-store`.

### Epic D — Safe public submission

**US-D1: Submit valid lead**

As a visitor, I can submit the configured form and receive a clear success state.

Acceptance criteria:

- Submission is accepted from allowed second-origin page via configured CORS.
- Server validates JSON content type, body size, widget status, required fields, types, string limits, email format, and unknown fields.
- Only configured non-honeypot fields are persisted.
- Success returns `201` with a submission identifier/status and no internal metadata.
- Stored lead is connected to the correct widget and tenant.

**US-D2: Get useful safe validation feedback**

As a visitor, I receive an understandable validation error rather than an application failure.

Acceptance criteria:

- Malformed/invalid requests return structured `400`/`422` JSON errors; oversized requests return `413`.
- Bad client input cannot produce an unhandled `500`.
- The widget maps safe validation feedback to the relevant field or generic form error.
- Server exceptions/internal provider details never enter the public response.

**US-D3: Prevent duplicate leads on retry**

As a visitor with an unreliable connection, retrying the same submission does not create duplicate leads.

Acceptance criteria:

- Widget submits an `Idempotency-Key` UUID.
- Database guarantees uniqueness per `(widget_id, idempotency_key)`.
- A repeated key/body returns the original accepted result and creates no extra submission/outbox event.
- Duplicate-key behaviour is tested under an integration transaction.

### Epic E — Abuse resistance

**US-E1: Rate limit bursts**

As an owner, I want a bot flood to be contained without blocking ordinary traffic.

Acceptance criteria:

- Limiter key includes a privacy-safe client IP representation and widget identity.
- Configurable burst threshold returns `429` and `Retry-After`.
- Tests demonstrate throttling under a burst and success for a legitimate/non-throttled request.
- The initial single-process limitation is documented.

**US-E2: Detect basic form spam**

As an owner, I want obvious automated form fills rejected cheaply.

Acceptance criteria:

- Widget includes an inaccessible/hidden honeypot named `website`.
- A non-empty honeypot submission is not recorded as a normal lead.
- Public response does not reveal the exact spam rule.
- A deterministic test demonstrates the behaviour.

### Epic F — Enrichment and safe side effects

**US-F1: Enrich leads when possible**

As an owner, I can see a lead’s coarse geography when providers are available.

Acceptance criteria:

- Submission service calls provider A with bounded timeout.
- A failure/non-valid response from A invokes provider B.
- A provider B response persists city/country and provider attribution.
- When both fail, submission still returns `201`, with null geo fields.
- Tests use fake providers; no test depends on live external APIs.

**US-F2: Notify without risking a lead**

As an owner, I can receive a notification without notification availability determining whether a lead is captured.

Acceptance criteria:

- Lead and `outbox_event` are stored atomically in one database transaction.
- Worker processes pending events asynchronously with bounded retry and sanitized error state.
- Forced notification failure leaves submission stored and public result successful.
- Outbox event IDs enable receivers to deduplicate at-least-once delivery.

### Epic G — Dashboard and evaluation experience

**US-G1: View leads and basic analytics**

As an owner, I can review my leads and understand their basic distribution.

Acceptance criteria:

- Paginated list filters by caller tenant, optionally widget/date range.
- Summary gives time-bucketed count, per-widget totals, and geo country/city breakdown.
- Empty states return stable valid JSON.
- Aggregation queries use appropriate indexes and never include another tenant’s data.

**US-G2: Run and verify project**

As an evaluator, I can run the project and prove important behaviours locally.

Acceptance criteria:

- README provides exact boot, seed, and test commands.
- `capstone.yaml`, `.env.example`, `BUILDLOG.md`, and `EVIDENCE.md` are present and current.
- The final demo includes valid submission, invalid input, CORS behaviour, rate-limit burst, geo fallback, and notification failure.

## 8. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | JWT authentication and token-derived tenant scope | Must |
| FR-02 | Validated tenant-isolated widget CRUD | Must |
| FR-03 | Per-widget opaque ID and generated script snippet | Must |
| FR-04 | Public cached config and versioned JS delivery | Must |
| FR-05 | Second-origin rendering/submission | Must |
| FR-06 | Public validation, payload cap, CORS/preflight, intentional errors | Must |
| FR-07 | Per-IP/widget rate limit and honeypot | Must |
| FR-08 | Idempotent writes | Must |
| FR-09 | Geo A→B fallback and no-geo degradation | Must |
| FR-10 | Transactional outbox/background notification handling | Must |
| FR-11 | Tenant-only submission dashboard and aggregates | Must |
| FR-12 | Observability counters/correlation IDs | Should |
| FR-13 | Redis limiter adapter | Could |
| FR-14 | Signed outbound webhooks/delivery status | Could |
| FR-15 | Targeting/SSE dashboard | Won’t for MVP |

## 9. Non-functional requirements

| Area | Requirement |
|---|---|
| Security | No secrets committed; passwords hashed; no raw payload/token/PII in logs; owner queries tenant-scoped. |
| Reliability | Provider and notifier failures do not invalidate accepted leads. |
| Performance | Bundle is long-cacheable; config is small and short-cacheable; outbound providers have short timeouts. |
| Availability | Rate limits and payload caps prevent trivial resource abuse; normal requests remain served after a burst. |
| Privacy | Collect minimum configured data; exclude honeypot; prefer HMAC IP hash over raw IP. |
| Testability | Clock, notifier, geo providers, and limiter are replaceable/fakeable in tests. |
| Maintainability | Routes are thin; service/repository/integration boundaries and ADRs explain decisions. |
| Documentation | Clean-machine setup, limitations, API contract, architecture, and evidence are current. |

## 10. Metrics and measurement

The MVP should record/derive the following locally. These are portfolio-quality operational signals, not production SLO claims.

| Metric | Definition | Why it matters |
|---|---|---|
| Accepted submissions | Count of persisted non-spam submissions | Product value baseline. |
| Validation rejection rate | Invalid/oversized requests ÷ public submission attempts | Shows public input quality/attack surface. |
| Rate-limit count | Number of `429` responses | Shows abuse pressure and limiter effectiveness. |
| Spam-honeypot count | Filled honeypot attempts | Shows basic bot filtering. |
| Geo fallback rate | Provider B successes ÷ geo attempts | Reveals primary provider reliability. |
| Geo unavailable rate | Both-provider failures ÷ geo attempts | Ensures degradation is observable. |
| Outbox failure/retry count | Failed/retried events | Makes non-critical failures visible. |
| Idempotent replay count | Duplicate-key requests | Validates retry behaviour. |

MVP success is all acceptance tests green and every capstone probe passing. If the observability enhancement is implemented, expose counters in logs or a protected/local metrics endpoint and show them in the demo.

## 11. End-to-end flows

### Configuration flow

```text
Owner login → JWT → create widget → validate/store tenant-owned config
→ return public ID + versioned script snippet → paste into customer page
```

### Visitor load flow

```text
Customer page → GET widget.v1.js?id=PUBLIC_ID → GET public config
→ render safe DOM form → visitor completes fields
```

### Visitor submit flow

```text
OPTIONS preflight → CORS allow check → body cap → schema validation
→ rate limit → honeypot → idempotency lookup → geo A → geo B → no geo
→ transaction: submission + outbox event → 201 accepted
→ worker: notification / retry / failure record
```

## 12. Dependencies and configuration

| Dependency | Purpose | Failure policy |
|---|---|---|
| PostgreSQL | Durable tenants/widgets/leads/outbox | Application cannot accept durable leads without it. |
| Geo provider A (`ip-api.com`) | First coarse geo lookup | Fall back to B. |
| Geo provider B (`ipapi.co`) | Second geo lookup | Continue without geo. |
| Console/Mailpit/webhook notifier | Non-critical notification | Record/retry failure; never reject lead. |
| Docker Compose | Local repeatable service boot | README provides alternative only if fully verified. |

All credentials/configuration are environment variables represented safely in `.env.example`. No third-party paid tier or credit card is required.

## 13. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| CORS/preflight confusion | Widget fails in browser despite API working in curl | Implement/test `OPTIONS` early using second origin. |
| Scope creep into frontend/form builder | Core resilience misses deadline | Freeze to one/two widget types and a minimal UI. |
| Live geo test flakiness | Tests unreliable | Use fakes; live APIs only for manual development. |
| In-memory limiter misunderstood as production-ready | Misleading project claims | Document limitation and optional Redis adapter. |
| Worker crash after event claim | Delayed notification | Lease/available-at/retry state and tests; lead remains safe. |
| Incorrect tenant predicate | Data leak | Central scoped repository methods plus cross-tenant tests. |
| Sensitive logs | Privacy/security issue | Structured redaction policy and review before demo/commit. |
| AI feature scope | Cost/ungrounded claims | Exclude from MVP; add only with budget, eval, and fallback. |

## 14. Delivery plan and gates

| Phase | Deliverables | Exit gate |
|---|---|---|
| 0: Foundation | Repo pack, docs, Docker baseline, settings, migrations/test harness | Clean environment boots; no secrets tracked. |
| 1: Owner path | Auth, tenant model, widget CRUD, embed snippet | Tenant A cannot access B; widget can be created. |
| 2: Public path | Config, CORS, validation, limiter, honeypot, idempotency, geo/outbox | Cross-origin valid lead stores; failure tests pass. |
| 3: Delivery/dashboard | Bundle, cache headers, customer site, aggregates, E2E tests | Widget renders at second origin; dashboard shows lead. |
| 4: Evidence/demo | Seed, docs, EVIDENCE, rehearsal | All acceptance probes pass twice. |
| 5: Optional differentiator | Observability or one selected enhancement | Core remains green and enhancement has tests/docs. |

## 15. Launch/readiness checklist

- [ ] Core functional requirements FR-01 through FR-11 are complete.
- [ ] Automated tests cover all mandatory hostile-path scenarios and are green.
- [ ] Manual second-origin browser flow is verified.
- [ ] All API contracts match implementation/OpenAPI.
- [ ] Migrations and seed script work from a clean database.
- [ ] Cache, CORS, error, and secret-handling headers/behaviour are verified.
- [ ] `EVIDENCE.md` has actual proof for each Definition-of-Done item.
- [ ] README contains correct run/seed/test steps, architecture, limitations, and demo route.
- [ ] BUILDLOG accurately records AI assistance and corrections.
- [ ] Optional enhancement work has not weakened or delayed the core.

## 16. Open decisions before implementation

These choices have safe defaults but should be confirmed before code begins:

1. **Project name:** keep `WidgetForge`, or choose a personal portfolio name.
2. **Notification demonstration:** console output first (simplest) or local Mailpit (more visual).
3. **Optional differentiator:** observability is recommended; Redis limiter or signed webhook is a stronger but larger second option.
4. **Public CORS policy for demo:** explicit `http://localhost:8080` allow-list is recommended; document how owners would register origins in a later release.

Until a decision changes it, implementation uses the recommended defaults above.
