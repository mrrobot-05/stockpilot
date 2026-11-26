# StockPilot — Build Plan

Status: **v1 complete** (shipped 2026-11-26)
Updated: 2026-11-26

## Product

StockPilot is our own inventory management app: track products, stock levels, categories,
suppliers and stock movements from a clean web UI and a JSON API. v1 is local-only and runs as
a single FastAPI process with no Node build step. See `README.md` for setup and usage.

## Decisions

- Scope: full v1 (rebrand + backend + UI + inventory features) — **done**
- Auth: none in v1; users/roles and CSRF tokens deferred to v1.1
- ORM: SQLAlchemy 2.x; schemas with Pydantic v2
- Migrations: Alembic (`backend/alembic/versions/`)
- Database: SQLite at `backend/stockpilot.db`; Postgres optional later via `DATABASE_URL`
- UI: Jinja2 templates + Bootstrap 5.3.3 + Bootstrap Icons + HTMX 2.x + Chart.js 4 (CDN)
- No Docker, no React, no Node/npm build
- Theme: light + dark toggle (`data-bs-theme`), persisted in `localStorage`
- Currency: USD in v1; a real settings model with configurable currency is deferred
- Serving: bind `127.0.0.1`; `DEBUG=false` by default; same-origin guard on state-changing requests
- Legacy tutorial folders were removed before publication; no legacy code remains

## Architecture

```
stockpilot/
├── .github/
│   └── workflows/ci.yml    # Python 3.12/3.13 CI matrix
├── docs/
│   └── README.md           # documentation index
├── README.md               # complete v1 documentation
├── PLAN.md                 # this plan
├── .gitignore
└── backend/
    ├── pyproject.toml, requirements.lock, .env.example
    ├── alembic.ini, alembic/
    ├── app/
    │   ├── main.py         # app, same-origin middleware, static mount
    │   ├── core/config.py
    │   ├── db/session.py, base.py
    │   ├── models/         # product, category, supplier, stock_movement
    │   ├── schemas/        # API request/response models
    │   ├── routers/        # /api + server-rendered pages
    │   ├── services/       # domain logic, stats, CSV export
    │   ├── templates/      # base, pages, partials (tables, modals)
    │   └── static/         # css/app.css, js/app.js, favicon.svg
    ├── scripts/seed.py
    └── tests/              # API, domain, migrations and UI tests
```

## v1 features

- Dashboard: totals, stock value, stock-health chart, attention list, recent movements
- Products: CRUD; SKU, name, description, category, supplier, cost/sell price, quantity,
  reorder level; search, filters, sorting and pagination
- Stock movements: IN / OUT / ADJUST with notes; atomic stock updates; immutable history
- Categories and suppliers: CRUD with product counts; references cleared on delete
- Alerts: `low_stock` (`0 < quantity <= reorder_level`) and `out_of_stock` (`quantity == 0`)
  filters on `/api/products`, merged into the dashboard attention list
- Settings: informational page with theme control, read-only USD, version and shortcuts
- CSV export: products and movements, sanitised against spreadsheet formula injection
- Seed script, Alembic migrations, case-insensitive unique expression indexes
- Responsive Bootstrap layout, dark mode, HTMX swaps, toasts, modals, empty states
- JSON API under `/api` for scripts and future AI clients
- Server-side same-origin guard on all state-changing requests

## API

- `GET /api/health`
- `GET /api/products` — `q`, `low_stock`, `out_of_stock`, `sort`, `page`, `page_size`,
  `category_id`, `supplier_id`, `is_active`
- `POST /api/products`, `GET/PATCH/DELETE /api/products/{id}`
- `GET/POST /api/products/{id}/movements`, `GET /api/movements`
- `GET/POST /api/categories`, `GET/PATCH/DELETE /api/categories/{id}`
- `GET/POST /api/suppliers`, `GET/PATCH/DELETE /api/suppliers/{id}`
- `GET /api/stats`
- `GET /api/export/products.csv`, `GET /api/export/movements.csv`

Full semantics are documented in `backend/README.md`.

## Phases

| # | Phase | Status | Outcome |
| --- | --- | --- | --- |
| 0 | Baseline & skeleton | ✅ Done | git repo, PLAN.md, pyproject, .env.example, config |
| 1 | Backend core | ✅ Done | SQLAlchemy models, schemas, Alembic, product CRUD, pytest |
| 2 | Inventory domain | ✅ Done | categories, suppliers, movements, stats, CSV, seed, tests |
| 3 | UI foundation | ✅ Done | base template, Bootstrap theme, HTMX, layout, dashboard |
| 4 | Screens | ✅ Done | products, movements, categories, suppliers, settings, alerts |
| 5 | Polish & docs | ✅ Done | responsive Bootstrap layout, a11y basics, full tests, README, no legacy branding |
| 6 | AI v1.1 | ⬜ Planned | chat assistant, forecasting, OCR, anomaly detection |

## Definition of done (v1)

- [x] `pytest -q` and `ruff check .` pass in `backend/` (177 tests, no warnings)
- [x] app runs with `uvicorn app.main:app --host 127.0.0.1 --port 8000` from `backend/`
- [x] Alembic `upgrade head` and `check` pass against a clean database
- [x] responsive Bootstrap layout with visible focus and skip link
- [x] no legacy branding string in tracked files
- [x] no secrets in tracked files; `DEBUG=false` by default
- [x] README has setup, UI/API notes and a local-only security warning

## Deferred beyond v1

- Authentication, users/roles and CSRF tokens before any network exposure
- A real settings model: configurable currency, default reorder level and theme server-side
- Self-hosted front-end assets and SRI hashes for every CDN link
- Production deployment, HTTPS, remote database configuration and a device-level a11y audit
- Manual screenshots for the README

## AI roadmap (v1.1)

- Natural-language chat assistant that calls the API
- Demand forecasting and reorder suggestions
- Receipt/invoice OCR to create stock movements
- Stock anomaly detection
- Auto-categorisation and semantic search
