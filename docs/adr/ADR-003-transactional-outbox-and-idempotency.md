# ADR-003: Use a transactional outbox and idempotency key

## Status

Accepted

## Context

Public browsers retry requests and notification providers fail. A lead must not be duplicated by retry or lost because a secondary side effect fails.

## Decision

Require/accept an `Idempotency-Key` on public submissions and enforce a unique `(widget_id, idempotency_key)` constraint. Write the submission and a pending outbox event in one database transaction; dispatch notifications asynchronously with bounded retries.

## Rationale

The unique constraint is the final authority against duplicate writes. The outbox removes the unsafe gap between committing a lead and attempting a notification.

## Trade-offs

- More schema/state-machine code than firing a webhook inline.
- Notification delivery is at-least-once, so receivers must deduplicate by event ID.

## Consequences

- Positive: accepted lead response is independent of notifier health and retries are observable.
- Negative: pending/failed events require worker monitoring.
- Mitigation: retry cap, sanitized error field, dashboard/admin visibility, and tests for failure paths.
