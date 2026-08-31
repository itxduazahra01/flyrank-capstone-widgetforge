# WidgetForge Demo & Acceptance Guide

## Fast verification

```powershell
Copy-Item .env.example .env
python scripts/seed_demo.py
python -m unittest discover -s tests -v
```

For the PostgreSQL/Docker path:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec api python scripts/seed_demo.py
docker compose exec api python -m unittest discover -s tests -v
```

Serve the customer page on a second origin:

```powershell
python -m http.server 8080 --directory customer-site
```

After seeding, replace `REPLACE_WITH_PUBLIC_ID` in `customer-site/index.html` with the seeded widget’s `public_id`, then open `http://localhost:8080`.

## Six-minute walkthrough

1. `POST /api/v1/auth/login` using `alice@acme.test` / `DemoPass123!`.
2. Create a widget; call its `/embed` endpoint and show the generated script tag.
3. Load the second-origin customer page and submit the widget form.
4. Call `/api/v1/submissions` and `/api/v1/dashboard/summary` with Alice's bearer token.
5. Show malformed input (`422`), oversized input (`413`), honeypot behaviour, and the sixth request burst (`429`) with the automated tests.
6. Show the geo fallback and notification failure tests; state: “Non-critical failures never break the main path.”
7. Run `python scripts/process_outbox.py` to show durable events being processed.

## Demo credentials

| Tenant | Email | Password |
|---|---|---|
| Acme Labs | `alice@acme.test` | `DemoPass123!` |
| Beta Studio | `bob@beta.test` | `DemoPass123!` |

These credentials are deterministic local demo data only. They are not production credentials.
