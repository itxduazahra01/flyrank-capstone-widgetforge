# Capstone Evidence

This file records reproducible proof for the internship evaluator. Run these commands from the repository root after copying `.env.example` to `.env`.

| Requirement | Reproducible proof | Status |
|---|---|---|
| Tenant-isolated owner CRUD | `test_owner_crud_embed_and_tenant_isolation` proves another tenant receives `404` for read, update, and delete. | Complete |
| Cacheable config and immutable bundle | `test_config_cors_cache_and_submission_replay` checks CORS, `ETag`/`304`, config caching, and `widget.v1.js` immutable caching. | Complete |
| Cross-origin browser form | `python -m unittest tests/test_browser_embed.py -v` launches Chromium at `:8080`, renders the remote widget, fills it, and sees confirmation. | Complete in CI |
| Abuse and payload protection | `test_honeypot_validation_and_rate_limit` proves honeypot and `429`; `test_oversized_submission_returns_413` proves the body cap. | Complete |
| Geo degradation | Deterministic provider fakes prove A → B fallback and both-down persistence. Real adapters are opt-in via `GEO_ENRICHMENT_ENABLED=true`. | Complete |
| Durable notification work | The Compose `worker` service polls `outbox_events`; failure isolation/retry state is covered by the public-path suite. | Complete |
| Dashboard analytics | `test_dashboard_is_tenant_scoped` checks tenant scope and the `submissions_over_time` series. | Complete |
| Migration-controlled schema | `docker compose up` executes the Alembic migration job before API/worker startup. A complete legacy pre-Alembic schema is safely baselined rather than overwritten. | Complete |

## Verification commands

```powershell
docker compose up --build -d
docker compose exec api python scripts/seed_demo.py
docker compose exec api python -m unittest discover -s tests -v
docker compose logs worker
```

The GitHub Actions workflow repeats the service and browser checks on every push and pull request.
