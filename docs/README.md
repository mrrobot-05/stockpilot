# StockPilot documentation

- [Root README](../README.md) — features, quickstart, UI pages, API summary and security notes.
- [Backend README](../backend/README.md) — setup, database, API semantics, migrations and seed data.
- [Architecture](ARCHITECTURE.md) — request flow, data model, ledger invariant and security posture.
- [Build plan](../PLAN.md) — v1 status, decisions, phases and the v1.1 AI roadmap.
- [Changelog](../CHANGELOG.md) — release notes for 0.1.0.
- [Contributing](../CONTRIBUTING.md) — setup, tests, lint and commit style.
- [Security policy](../SECURITY.md) — local-only scope and private vulnerability reporting.
- [Publishing](PUBLISHING.md) — GitHub description, topics, push steps and post-push checks.
- [Screenshots](screenshots/README.md) — how to capture local screenshots (no images committed).
- [CI workflow](../.github/workflows/ci.yml) — Python 3.12/3.13 test matrix, Alembic checks,
  ruff and JavaScript syntax validation.
- [Issue templates](../.github/ISSUE_TEMPLATE/) and
  [pull request template](../.github/PULL_REQUEST_TEMPLATE.md) — community contribution forms.

StockPilot is a single FastAPI application with a Jinja2/Bootstrap/HTMX UI. Run it locally
with the commands in the root README; no Docker, Node build or separate frontend server is
needed.
