# UI Implementation Plan — WidgetForge

## Goal

Add a polished frontend that makes WidgetForge feel like a real SaaS product without weakening its backend focus. It has two surfaces:

1. **Visitor widget:** the embedded form displayed on a customer website.
2. **Owner dashboard:** an authenticated interface for configuring widgets, copying snippets, and reviewing leads.

The UI consumes the existing FastAPI API. Tenant isolation, authorization, validation, analytics, rate limiting, and abuse controls remain server-side.

## Scope

| In scope | Out of scope |
|---|---|
| Responsive login/dashboard/widget editor/submissions pages | Drag-and-drop form builder, billing, teams, roles, real-time updates |
| Polished embedded widget states | New frontend authentication provider |
| Accessible inputs, errors, empty/loading/success states | Replacing Swagger/OpenAPI |
| React/TypeScript frontend in `frontend/` | Mobile app or a large design-system dependency |

## Recommended stack

| Concern | Choice | Why |
|---|---|---|
| Application | React + TypeScript + Vite | Fast build, clear separation from FastAPI. |
| Styling | Plain CSS + design tokens | Professional visual result without framework overhead. |
| Routing | React Router | Clean login/dashboard/widget paths. |
| HTTP | Typed `fetch` wrapper | Existing API surface is small. |
| Session | `sessionStorage` JWT | Reasonable for local capstone; clear on logout/401. |
| Icons | Inline SVG or Lucide React | Consistent, accessible UI. |

Run Vite on port `5173`. The existing public widget test page remains on port `8080`.

## Information architecture

```text
/login                 Sign in
/dashboard             Metrics, recent leads, widget performance
/widgets               Widget list
/widgets/new           Create widget
/widgets/:id           Edit widget, install snippet, filtered leads
```

Use a left sidebar on desktop and compact top navigation on mobile. Keep content centered and constrained to a readable width.

## Visual direction

- Light slate/off-white page background, white cards, subtle borders, 12–16px radius.
- One restrained indigo/blue primary colour, with green/amber/red status colours paired with text.
- Inter or system sans-serif, generous spacing, and strong headings.
- Avoid gradient-heavy landing-page styling, crowded charts, excessive shadows, and animations.

Accessibility requirements:

- Keyboard-visible focus styles and semantic labels for every input.
- Errors use text plus colour and are connected with `aria-describedby`.
- Icon-only controls have accessible names.
- Use `textContent` in the embed widget; never render owner-supplied content as HTML.

## Visitor widget

### Required states

| State | Expected UX |
|---|---|
| Loading | Compact “Loading form…” state with no layout shift. |
| Ready | Title, optional description, fields, button, and hidden honeypot. |
| Client validation | Clear field-level error and focus first invalid field. |
| Submitting | Disable button and retain data. |
| Success | Replace form with concise confirmation. |
| Failure | Generic retry guidance; never expose backend/provider details. |

### Implementation tasks

1. Add scoped `wf-` CSS classes or a namespaced injected stylesheet to `widget.v1.js`.
2. Use a `data-widgetforge-root` container so host-site CSS does not break layout.
3. Add client required/e-mail validation only for UX; server validation stays authoritative.
4. Reuse one idempotency key while retrying one in-progress submission; create a new key after a final response.
5. Show friendly messages for `422`, `429`, and network errors.
6. Test on the existing second-origin page and a page with intentionally conflicting global CSS.

## Owner dashboard

### Login

- Centered sign-in card with email/password, primary CTA, and clear invalid-login state.
- Keep demo credentials in a development-only helper; do not display them in a deployed public build.
- Store the JWT in `sessionStorage`; logout or a `401` clears it and returns to `/login`.

### Dashboard overview

- Summary cards: total submissions, active widgets, top country.
- Widget-performance list: title, type, active state, total leads.
- Recent-submissions table: name/e-mail, widget, country, timestamp.
- Empty state with “Create your first widget” action.

### Widget list and editor

- List title, type, active state, updated date, and actions.
- Editor sections: content, configured fields, display/publishing state.
- Start with the existing supported `text` and `email` fields only.
- Enforce 1–8 fields visually, map API `422` errors inline, and indicate unsaved changes.
- After save, show an installation panel with a copyable snippet and “paste before `</body>`” guidance.

### Submissions

- Reuse `GET /api/v1/submissions` and summary endpoint.
- Columns: date/time, e-mail, name, widget, country/city.
- Never display raw IPs, bearer tokens, full raw payloads, or notifier errors in owner UI.

## API mapping

| UI behaviour | Endpoint |
|---|---|
| Login | `POST /api/v1/auth/login` |
| Overview | `GET /api/v1/dashboard/summary` |
| Leads | `GET /api/v1/submissions` |
| Widget list/create | `GET/POST /api/v1/widgets` |
| Widget edit/deactivate | `GET/PATCH/DELETE /api/v1/widgets/{id}` |
| Install snippet | `GET /api/v1/widgets/{id}/embed` |

Only add backend support when UI cannot reasonably use the current contract. Likely future additions: pagination metadata for submissions and `active_widget_count` in summary.

## Frontend structure

```text
frontend/
├── src/
│   ├── api/          # typed fetch client and contracts
│   ├── auth/         # session provider and route guard
│   ├── components/   # Button, Input, Card, Table, Toast, EmptyState
│   ├── features/     # dashboard, widgets, submissions
│   ├── pages/        # route-level screens
│   ├── styles/       # tokens and global/component CSS
│   └── main.tsx
├── package.json
└── vite.config.ts
```

## Delivery phases

### Phase 1 — shell and authentication (2–3 hours) — **Complete**

1. Scaffold Vite React TypeScript app, tokens, router, navigation, and protected route.
2. Build login/logout and API client.
3. Verify invalid/expired token handling.

**Gate:** owner can log in with real API and reach a protected dashboard shell. The Vite production build passes and the development server responds on `http://localhost:5173`.

### Phase 2 — dashboard and widget management (5–7 hours) — **Complete**

1. Build summary cards, widget list, and submissions table.
2. Build create/edit widget form with API validation mapping.
3. Build copy-snippet install panel.

**Gate:** owner creates a widget through UI, copies a real API-generated snippet, submits a browser lead, and sees it in the dashboard. The frontend production build passes.

### Phase 3 — embed polish (3–4 hours) — **In progress**

1. Apply isolated widget styling.
2. Add validation, submitting, success, and error states.
3. Verify host-CSS collision resistance and keyboard use.

**Gate:** polished second-origin widget works while the existing backend suite remains green. Scoped styling, client-side feedback, loading/submitting/success/error states, and retry-safe idempotency-key handling are implemented; Docker image rebuild verification is pending.

### Phase 4 — proof and quality (2–3 hours)

1. Add frontend tests for login, editor, and empty/error states.
2. Run frontend checks and all 7 existing backend tests.
3. Capture token-safe screenshots/GIF for dashboard, snippet, embed, and lead capture.
4. Update README and demo guide.

**Gate:** a recruiter can understand the product and see an end-to-end workflow in under two minutes.

## Acceptance checklist

- [ ] Login, logout, unauthorized redirect, loading, empty, and API-error states work.
- [ ] Dashboard and leads display only authenticated tenant data.
- [ ] Widget CRUD uses real API and communicates validation errors clearly.
- [ ] Install snippet can be copied with confirmation.
- [ ] Embedded form is accessible, responsive, and CSS-isolated.
- [ ] Existing backend tests remain green.
- [ ] Screenshots contain no JWT, password, raw IP, or private lead data.

## Portfolio narrative

The best demo sequence is: **log in → create widget → copy snippet → open customer site on another origin → submit lead → see dashboard result → point to rate-limit/fallback/outbox tests.** The UI makes the backend engineering visible; it does not replace it.
