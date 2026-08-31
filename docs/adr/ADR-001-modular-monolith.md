# ADR-001: Start with a modular monolith

## Status

Accepted

## Context

This is a solo, local-first capstone with a 35–50 hour target. It has three request paths and two external integrations but no requirement for independent deployment or scale.

## Decision

Use one FastAPI service with clear API, service, repository, integration, and worker modules. PostgreSQL is the single source of truth.

## Rationale

It keeps debugging, tests, local setup, and demonstration tractable while still making public-boundary and resilience concerns explicit. Provider/notifier interfaces permit later extraction if evidence warrants it.

## Trade-offs

- Give up independent component scaling and deployability.
- Avoid distributed tracing, broker operations, cross-service authentication, and eventual-consistency complexity prematurely.

## Consequences

- Positive: one run command, atomic DB transaction for submission/outbox, fast development.
- Negative: process-local rate limit and worker share API runtime initially.
- Mitigation: adapters and documented Redis/worker extraction triggers.
