# Changelog

All notable changes to StockPilot are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses semantic versioning.

## [0.1.0] — 2026-11-26

### Added

- Dashboard with product/stock totals, stock value, health chart, attention list and recent
  movements.
- Products, categories and suppliers: searchable lists with filters, pagination and modal CRUD.
- Stock movement ledger with IN, OUT and ADJUST, atomic stock updates and full history.
- `low_stock` and `out_of_stock` filters; dashboard attention list merges both.
- CSV exports for products and movements with spreadsheet formula-injection sanitisation.
- Jinja2 + Bootstrap 5.3 + Bootstrap Icons + HTMX + Chart.js UI with light/dark theme,
  toasts, modals and empty states.
- JSON API under `/api` with interactive docs at `/docs`.
- Alembic migrations, case-insensitive unique expression indexes and an idempotent seed script.
- Same-origin guard for state-changing requests and `DEBUG=false` by default.
- GitHub Actions CI on Python 3.12 and 3.13 with tests, ruff, Alembic checks and JS syntax check.
- MIT license, security policy, contributing guide and community issue/PR templates.

### Notes

- v1 is local-only: there is no authentication or CSRF token system. See
  [SECURITY.md](SECURITY.md).
- Front-end libraries are loaded from CDNs; self-hosting and full SRI coverage are deferred.
