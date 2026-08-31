# WidgetForge Frontend Extension Plan

**Status:** In progress — Phase 1 visual foundation completed locally; do not commit or push without approval.

## Goal

Evolve WidgetForge from a backend-capstone dashboard into a believable lead-capture product while preserving the existing security and tenant-isolation guarantees.

The extension has two surfaces:

1. **Owner dashboard:** create, publish, analyse, and manage leads.
2. **Embedded widget:** a configurable form that remains lightweight, accessible, and safe on a customer website.

## Product outcome

An owner should be able to:

1. Select a widget template.
2. Configure fields and appearance with a live preview.
3. Publish the widget and copy an installation guide/snippet.
4. See views, starts, submissions, and conversion rate.
5. Search, filter, annotate, and update the status of captured leads.

## Design direction: calm brutalism

The intended style is **brutalist in structure, not aggressive in colour**:

- Strong black/ink borders, square or near-square corners, visible hierarchy.
- Large type, clear labels, deliberate spacing, short interface copy.
- Off-white background, charcoal text, muted cobalt primary, soft acid-lime success accent, restrained coral warning accent.
- No glass effects, gradients, neon glow, excessive shadows, or “AI” visual motifs.
- Use colour as a signal, not decoration; every state must also have text/icon support.

### Suggested tokens

| Token | Value | Use |
|---|---:|---|
| Canvas | `#F5F2EA` | App background |
| Ink | `#18212B` | Text, borders |
| Cobalt | `#2457E6` | Primary action, links |
| Lime | `#DFFF39` | Success and selected states |
| Coral | `#FF694C` | Warning/destructive states |
| Surface | `#FFFFFF` | Cards, fields, tables |

Accessibility rules: WCAG AA text contrast, visible focus rings, 44px minimum pointer targets, semantic labels, no colour-only status communication, reduced-motion support.

## Phase 1 — Dashboard foundations and design system

**Progress (2026-08-09):** The frontend now uses the calm-brutalist visual foundation: ink borders, off-white surfaces, cobalt primary actions, lime/coral status accents, square controls, deliberate focus rings, responsive layout, and clearer dashboard/table hierarchy. `npm.cmd run build` passes. Reusable component extraction and the expanded app shell remain next in this phase.

### Frontend

- Introduce global design tokens and reusable components: `Button`, `Input`, `Select`, `Badge`, `EmptyState`, `MetricCard`, `DataTable`, `Drawer`, and `Toast`.
- Create a stable app shell: sidebar, workspace header, responsive mobile navigation, account menu.
- Add loading, empty, error, and permission-denied states for every dashboard view.
- Use route-level pages: Overview, Widgets, Submissions, Settings.

### Verification

- TypeScript build passes.
- Keyboard navigation and visible focus review.
- Screenshot evidence for desktop and narrow/mobile layouts.

## Phase 2 — Visual widget builder and preview

**Progress (2026-08-09):** Started locally. The widget-creation page now includes a responsive desktop/mobile live visitor preview that reflects title, description, fields, required markers, button text, primary colour, and corner radius as the owner edits. Owners can begin from Newsletter, Contact, Book a demo, or Waitlist templates, then configure the validated `primary_color`, `border_radius`, and success message before creation. The widget list gives owners a tenant-scoped publish/pause/resume control. Its installation panel links to an owner-only edit page for visitor-facing copy, active state, fields, field order, appearance, success message, and allowed origins, without changing the public widget ID; it uses the existing server-side tenant checks. The backend persists the restricted appearance contract inside the existing widget display-options document; the public configuration endpoint exposes it and the framework-free embed applies it. Legacy widgets receive safe defaults. Docker Compose was rebuilt and all 11 backend tests passed (browser test is intentionally skipped inside the API image; CI runs it with Chromium).

### Frontend

- Template chooser: Newsletter, Contact, Book a demo, Waitlist, Feedback.
- Field editor: add/remove fields, label, placeholder, type, required flag, max length, and drag-to-reorder.
- Appearance controls: button text, success message, primary colour, border radius, and light/dark surface choice.
- Live preview using the same public widget rendering primitives where practical.
- Device switcher for desktop and mobile preview.
- Publish state: Draft, Published, Paused.

### Backend/data changes

- Extend `Widget` configuration with `appearance`, `success_message`, `status`, and `published_at`.
- Add an Alembic migration; maintain defaults so existing widgets continue to render.
- Validate appearance values server-side with a strict allowlist/schema.
- Return safe appearance data from the public config endpoint only.

### Verification

- Tenant-isolated create/update tests.
- Public config never includes owner/private data.
- Browser test verifies changed configuration appears in the embedded form.

## Phase 3 — Installation and domain controls

**Progress (2026-08-09):** Started locally. The validated widget appearance contract now accepts an optional normalized `allowed_origins` list. The saved per-widget list is the single customer-facing domain control: public embed requests receive dynamic CORS headers, while public events and lead submissions are rejected with `403` when a widget has an allowlist and the browser origin is not listed. No operator `.env` change or API restart is required when an owner adds a site. Regression tests cover an allowed origin, a blocked origin, arbitrary-origin preflight, and a real browser embed on a second origin. The builder now gives owners an optional comma-separated allowlist with origin-format guidance; the backend remains the enforcement point. The dashboard also includes a per-widget installation panel with a fetched versioned snippet, copy feedback, and clear HTML/React/WordPress guidance. A test-installation preview link remains pending.

### Frontend

- Dedicated installation panel: Copy snippet, HTML, React/Next.js, WordPress tabs.
- “Test installation” instructions and a shareable preview link.
- Per-widget domain allowlist editor with clear draft/published indicators.
- Copy feedback and snippet version display.

### Backend/data changes

- Add `allowed_domains` to Widget, validated and normalized.
- Enforce allowed domains on public submissions; return a safe, explicit error for blocked origins.
- Keep localhost development origins documented and opt-in.

### Verification

- Allowed domain succeeds; unlisted domain is rejected.
- Existing CORS/preflight tests remain green.

## Phase 4 — Lead management

**Progress (2026-08-09):** Started locally. Added Alembic migrations for a tenant-scoped lead lifecycle (`new`, `contacted`, `qualified`, `closed`) and private owner notes. Owners can update a lead status or note through the API; another tenant receives `404`. The API accepts bulk lifecycle updates for up to 50 selected tenant-owned leads and rejects mixed-tenant selections. A dedicated Lead actions dashboard view supports lifecycle changes with clear feedback. The new Lead explorer view exposes tenant-scoped widget, country, status, and date filters plus cursor-based Load more pagination; the same filters are available to CSV export. The dashboard has a lifecycle filter, client-side lead search, per-lead status controls, a detail drawer for all captured fields/geo/timestamp, and an in-drawer private-note editor. A CSV download covers the active status filter. Owners can export up to 10,000 tenant-scoped leads using formula-injection-safe CSV values; notes are deliberately excluded.

### Frontend

- Submissions table with search, date range, widget, country, and status filters.
- Lead detail drawer with complete submitted fields, source origin, geo result, timestamp, status, and internal notes.
- Lead lifecycle: `new`, `contacted`, `qualified`, `closed`.
- Bulk status updates and CSV export of the currently filtered result.

### Backend/data changes

- Add `lead_status`, `notes`, and `updated_at` to submissions (or a separate `submission_notes` table if multiple notes are required).
- Add tenant-scoped filter, detail, status-update, and export endpoints.
- Use pagination/cursor parameters rather than returning unbounded lead lists.
- Record an audit/outbox event for lead-status changes if notifications are introduced.

### Verification

- Tenant B cannot read/update/export Tenant A submissions.
- Search/filter and status transitions have API tests.
- CSV escaping prevents spreadsheet formula injection.

## Phase 5 — Analytics and funnel

**Progress (2026-08-09):** Started locally. The embed now emits lightweight `widget_viewed` and first `form_started` events with a per-browser-session identifier that is HMAC-hashed server-side; no raw IP address is stored in the event table. Events are server-deduplicated per widget/event/session and rate-limited on the public path. An accepted submission also records an event transactionally. The owner dashboard exposes tenant-scoped views, starts, accepted leads, and view-to-lead conversion in a simple funnel. Owners can select a 7/30/90-day range and see daily event bars, top origins, and accepted-lead countries. The analytics API supports the validated 1–90-day range. API regression tests verify public ingestion, deduplication, time-range aggregates, country data, and tenant isolation.

### Events to capture

- `widget_viewed`
- `form_started`
- `submission_accepted`

### Frontend

- Date selector: 7 days, 30 days, custom range.
- Metrics: views, starts, accepted submissions, conversion rate.
- Charts: trend over time, performance by widget, source domain, country.
- Explain unavailable/partial analytics clearly.

### Backend/data changes

- Create an append-only `widget_events` table with tenant ID, widget ID, event type, origin, session hash, and timestamp.
- Rate-limit/dedupe anonymous view events; never store raw IP addresses.
- Add tenant-scoped aggregate endpoints with indexed date-range queries.

### Verification

- Event ingestion cannot create cross-tenant data.
- Aggregates match seeded event fixtures.
- Dashboard handles zero-data state gracefully.

## Phase 6 — Notifications and integrations

**Progress (2026-08-09):** Started locally. The existing durable outbox worker supports an opt-in signed generic webhook delivery mode. It serializes a stable event envelope, sends only from the worker, adds event/delivery/signature headers, retries with the existing backoff policy, and is disabled by default (`NOTIFIER_MODE=console`). It supports safe secret rotation: a temporary previous secret emits a second signature header during the transition. Owners can configure one HTTPS webhook destination per widget through tenant-scoped API endpoints and a widget-specific dashboard page; the worker uses that destination before falling back to the global environment destination. Owners also have a tenant-scoped delivery-history API and dashboard page that report state, attempts, scheduled retry, and safe error text without returning lead payloads. Regression tests cover signing, rotation headers, and tenant isolation. Slack/Discord adapters remain pending.

- Owner-configurable email notification toggle per widget.
- Signed webhook delivery with secret rotation, retry state, and delivery history.
- Optional Slack/Discord adapter after the generic webhook is stable.
- Reuse the existing transactional outbox; never deliver a notification in the public request path.

## Recommended delivery order

| Increment | Value | Risk |
|---|---|---|
| 1. Design system + app shell | Makes the product feel intentional | Low |
| 2. Widget builder + preview | Highest visible product value | Medium |
| 3. Lead management | Turns submissions into workflow | Medium |
| 4. Installation + domain controls | Improves real customer onboarding/security | Medium |
| 5. Analytics funnel | Strong portfolio differentiator | High |
| 6. Notifications/webhooks | Production-style extension | High |

## Non-negotiable engineering constraints

- All owner reads/writes remain tenant-scoped on the server.
- The embedded bundle stays framework-free and versioned.
- Public endpoints remain body-capped, CORS-controlled, rate-limited, idempotent, and safe under dependency failure.
- Every schema change is an Alembic migration and has upgrade-safe defaults.
- New user-facing flows require API tests and browser evidence.
- Credentials, access tokens, raw IP addresses, and production lead PII must not enter screenshots, source control, or public demos.

## Definition of done for the extension

- A client can build, preview, publish, install, and pause a themed widget.
- A lead can be found, opened, annotated, status-managed, and exported by its owner only.
- Dashboard funnel metrics match captured events.
- Domain restrictions and all existing security regressions are tested.
- CI runs backend tests, browser embed proof, and frontend build.

**Browser proof progress (2026-08-09):** Added a Playwright owner-dashboard proof that seeds an authenticated owner session and opens the analytics dashboard, Lead explorer, bulk Lead actions, and Integrations pages. It passes locally. CI installs frontend dependencies and runs every `test_browser*.py` proof alongside the original cross-origin embed test.
