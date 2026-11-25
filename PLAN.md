# StockPilot — Build Plan

Status: approved — v1 implementation
Updated: 2026-11-26

## Product
StockPilot is our own inventory management app: track products, stock levels, categories, suppliers, and stock movements from a clean web UI and a JSON API.

## Decisions
- Scope: full v1 (rebrand + backend + UI + inventory features)
- Auth: none in v1; JWT users/roles in v1.1
- ORM: SQLAlchemy 2.x
- Migrations: Alembic
- Database: SQLite at `backend/stockpilot.db`; Postgres optional later via `DATABASE_URL`
- UI: Jinja2 templates + Bootstrap 5.3 + Bootstrap Icons + HTMX + Chart.js (CDN)
- No Docker, no React, no Node/npm build
- Theme: light + dark toggle (`data-bs-theme`)
- Currency: USD (configurable in Settings)
- Legacy tutorial folders: `archive/` (git-ignored; delete after v1 ships)

## Architecture
```
stockpilot/
├── PLAN.md
├── README.md
├── .gitignore
├── archive/                  # legacy tutorial code (ignored)
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/config.py
│   │   ├── db/session.py, base.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── templates/
│   │   └── static/
│   └── tests/
```

## v1 features
- Dashboard: total products, stock value, low-stock/out-of-stock counts, recent movements, chart
- Products: CRUD; SKU, name, description, category, supplier, cost price, sell price, quantity, reorder level
- Stock movements: IN / OUT / ADJUST with note; auto-update quantity; history
- Categories and suppliers: CRUD with product counts
- Alerts: low stock and out of stock views
- Settings: currency, default reorder level, theme
- CSV export: products and movements
- Seed script and Alembic migrations
- Responsive Bootstrap layout, dark mode, toasts, modals, empty states, skeleton loaders
- JSON API under `/api` for AI/future clients

## API sketch
- `GET /api/health`
- `GET /api/products` (`q`, `category_id`, `low_stock`, `sort`, `page`, `page_size`)
- `POST /api/products`, `GET/PATCH/DELETE /api/products/{id}`
- `GET/POST /api/products/{id}/movements`
- `GET/POST/PATCH/DELETE /api/categories`
- `GET/POST/PATCH/DELETE /api/suppliers`
- `GET /api/stats`
- `GET /api/export/products.csv`, `GET /api/export/movements.csv`

## Phases
| # | Phase | Done when |
| 0 | Baseline & skeleton | git repo, archive, PLAN.md, pyproject, .env.example, config |
| 1 | Backend core | SQLAlchemy models, schemas, Alembic, product CRUD, pytest |
| 2 | Inventory domain | categories, suppliers, movements, stats, CSV, seed + tests |
| 3 | UI foundation | base template, Bootstrap theme, HTMX, layout, dashboard |
| 4 | Screens | products, movements, categories, suppliers, settings, alerts |
| 5 | Polish & docs | responsive/a11y, full tests, README, zero legacy branding |
| 6 | AI v1.1 | chat assistant, forecasting, OCR, anomaly detection |

## Definition of done (v1)
- `pytest` and `ruff check` pass in `backend/`
- app runs with `uvicorn app.main:app --reload` from `backend/`
- all pages responsive at 360/768/1280 and keyboard navigable
- no legacy branding string in tracked files
- no secrets in tracked files
- README has setup, screenshots, and API notes

## AI roadmap (v1.1)
- Natural-language chat assistant that calls the API
- Demand forecasting and reorder suggestions
- Receipt/invoice OCR to create stock movements
- Stock anomaly detection
- Auto-categorization and semantic search
