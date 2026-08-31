# API Contract

Base URLs: authenticated endpoints use `/api/v1`; browser-facing endpoints use `/public/v1`.

## Authenticated owner endpoints

| Route | Purpose |
|---|---|
| `POST /api/v1/auth/login` | Get a seeded demo JWT. |
| `POST /api/v1/widgets` | Create widget for token tenant. |
| `GET /api/v1/widgets` | List token-tenant widgets. |
| `GET/PATCH/DELETE /api/v1/widgets/{id}` | Read/change/remove own widget only. |
| `GET /api/v1/widgets/{id}/embed` | Return script snippet for own widget. |
| `GET /api/v1/submissions` | Paginated own submissions. |
| `GET /api/v1/dashboard/summary` | Tenant-scoped time/widget/geo aggregates. |

Owner routes require `Authorization: Bearer <jwt>`. A cross-tenant object is indistinguishable from a missing object (`404`).

## Public endpoints

| Route | Cache/CORS | Purpose |
|---|---|---|
| `GET /widget.v1.js` | Immutable one-year cache | Render/fetch/submit bundle. |
| `GET /public/v1/widgets/{public_id}/config` | 5-minute TTL, ETag, configured CORS | Safe rendering config. |
| `OPTIONS /public/v1/submissions` | Configured origins/methods/headers | Browser preflight. |
| `POST /public/v1/submissions` | Configured CORS | Hardened lead capture. |

Submission request:

```json
{
  "widget_id": "a-public-widget-uuid",
  "fields": {"email": "ada@example.com", "name": "Ada"},
  "website": ""
}
```

Required headers: `Content-Type: application/json`, `Idempotency-Key: <UUID>`. `website` is a hidden honeypot and is omitted/empty for human submissions.

Success response:

```json
{"id":"submission-uuid","status":"accepted","created_at":"2026-08-08T12:00:00Z"}
```

Error response:

```json
{"error":{"code":"validation_error","message":"Submitted fields are invalid","details":[{"field":"email","message":"Invalid email"}]}}
```

The implementation must publish OpenAPI at `/docs` and keep actual schemas/status codes synchronized with this contract.
