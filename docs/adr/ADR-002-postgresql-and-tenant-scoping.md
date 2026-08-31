# ADR-002: Use PostgreSQL with tenant-scoped queries

## Status

Accepted

## Context

The project requires migrations, indexes, tenant isolation, JSON form payloads, and dashboard aggregation. SQLite is fine for early exploration but weaker for demonstrating production-style indexing/concurrency.

## Decision

Use PostgreSQL in Docker Compose. Every tenant-owned read, mutation, pagination query, and aggregate has a tenant predicate derived from JWT authentication.

## Rationale

PostgreSQL provides durable relational constraints, JSONB for bounded flexible form data, and credible aggregation/index work. Query-level tenant scope prevents an authorization check from being forgotten in a route.

## Trade-offs

- Docker and migrations add setup complexity over SQLite.
- Row-level security is deferred; application query discipline is mandatory.

## Consequences

- Positive: realistic persistence and explainable isolation tests.
- Negative: a repository mistake can still leak data.
- Mitigation: centralized scoped repository methods and cross-tenant integration tests.
