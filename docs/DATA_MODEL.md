# Data Model

## Entity relationships

```text
Tenant 1 ─── * User
Tenant 1 ─── * Widget 1 ─── * Submission 1 ─── * OutboxEvent
```

## Tables

### tenants

`id UUID PK`, `name TEXT`, `created_at TIMESTAMPTZ`.

### users

`id UUID PK`, `tenant_id UUID FK tenants`, `email TEXT UNIQUE`, `password_hash TEXT`, `created_at TIMESTAMPTZ`.

### widgets

`id UUID PK`, `public_id UUID UNIQUE`, `tenant_id UUID FK tenants`, `widget_type TEXT`, `title TEXT`, `description TEXT NULL`, `form_fields JSONB`, `button_text TEXT`, `display_options JSONB`, `is_active BOOLEAN`, `config_version INTEGER`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`.

`form_fields` example:

```json
[
  {"name":"email","label":"Work email","type":"email","required":true,"max_length":254},
  {"name":"name","label":"Name","type":"text","required":false,"max_length":120}
]
```

Constraints: allowed `widget_type`; unique/non-reserved field names; bounded field count; `config_version >= 1`.

### submissions

`id UUID PK`, `tenant_id UUID FK tenants`, `widget_id UUID FK widgets`, `idempotency_key UUID NULL`, `payload JSONB`, `source_origin TEXT NULL`, `ip_hash TEXT NULL`, `geo_country TEXT NULL`, `geo_city TEXT NULL`, `geo_provider TEXT NULL`, `spam_status TEXT`, `created_at TIMESTAMPTZ`.

Constraints and indexes:

- Unique `(widget_id, idempotency_key)` where `idempotency_key IS NOT NULL`.
- Index `(tenant_id, created_at DESC)` for dashboard list/timeline.
- Index `(widget_id, created_at DESC)` for widget stats.
- Index `(tenant_id, geo_country)` for geo aggregation.

### outbox_events

`id UUID PK`, `event_type TEXT`, `submission_id UUID FK submissions`, `status TEXT`, `attempt_count INTEGER`, `last_error TEXT NULL`, `available_at TIMESTAMPTZ`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`.

Constraints: status is `pending`, `processing`, `sent`, or `failed`; attempt count is non-negative. Index `(status, available_at)`.

## Data handling choices

- Store the form payload only after filtering against the widget schema.
- Do not store the honeypot field.
- Prefer a keyed hash of client IP instead of raw IP for rate-limiting/audit metadata; document its retention policy if deployment is added.
- Dashboard queries are always filtered by tenant before grouping or pagination.
