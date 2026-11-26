# StockPilot documentation

- [Root README](../README.md) — features, quickstart, UI pages, API summary and security notes.
- [Backend README](../backend/README.md) — setup, database, API semantics, migrations and seed data.
- [Build plan](../PLAN.md) — v1 status, decisions, phases and the v1.1 AI roadmap.
- [CI workflow](../.github/workflows/ci.yml) — Python 3.12/3.13 test matrix, Alembic checks,
  ruff and JavaScript syntax validation.

StockPilot is a single FastAPI application with a Jinja2/Bootstrap/HTMX UI. Run it locally
with the commands in the root README; no Docker, Node build or separate frontend server is
needed.
