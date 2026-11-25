# StockPilot

**Inventory, on autopilot.**

StockPilot is a local-first inventory manager for tracking products, stock levels, categories,
suppliers and stock movements. It ships as one FastAPI app with a server-rendered Bootstrap UI
and a JSON API for scripts and future AI clients. Version 1 is complete.

## Features

- **Dashboard** — product/stock totals, cost and retail value, low-stock and out-of-stock
  counts, a stock-health doughnut chart, a "Needs attention" list and recent movements.
- **Products** — searchable, filterable, sortable list with pagination; create, edit and delete
  through modals; SKU, name, description, category, supplier, cost/sell price, reorder level.
- **Stock movements** — IN, OUT and ADJUST ledger with notes, atomic stock updates and a
  full history with product/type filters. Stock changes never bypass the ledger.
- **Categories and suppliers** — CRUD with product counts; deleting one leaves its products
  in the catalogue with the reference cleared.
- **Stock alerts** — `low_stock` (`0 < quantity <= reorder_level`) and `out_of_stock`
  (`quantity == 0`) filters; the dashboard merges both into one attention list.
- **CSV exports** — products and movements, with spreadsheet formula-injection protection.
- **JSON API** — the same data under `/api`, documented at `/docs`.
- **Demo data** — idempotent seed script and Alembic migrations.
- **UI details** — light/dark theme with persistence, responsive layout, HTMX table swaps,
  Bootstrap modals, toasts and thoughtful empty states.

## Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2, Alembic, Pydantic v2,
  pydantic-settings, Jinja2, python-multipart.
- **Database:** SQLite at `backend/stockpilot.db` (override with `DATABASE_URL`; Postgres is
  a later option).
- **Frontend:** Bootstrap 5.3.3 + Bootstrap Icons 1.11.3, HTMX 2.x, Chart.js 4 and Inter,
  loaded from CDNs; the app's own CSS/JS live in `backend/app/static/`.
- **Tooling:** pytest + httpx for tests, ruff for linting.
- **Not included:** no Docker, no React, no Node/npm build step.

## Quickstart

From the repository root (Windows PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.lock
# or, for development with open-ended ranges:
# .\.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m scripts.seed
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

On macOS/Linux use `python3 -m venv .venv`, `source .venv/bin/activate` and
`cp .env.example .env`; the remaining `python`/`uvicorn` commands are the same with
`.venv/bin/` paths.

Open <http://127.0.0.1:8000/> (it redirects to `/dashboard`). Interactive API docs are at
<http://127.0.0.1:8000/docs>. The seed step is optional; without it you get a helpful empty
state with the same command shown on the dashboard. It is idempotent and skips when products
already exist.

## UI pages

| Page | What it does |
| --- | --- |
| `/dashboard` | Totals, stock value, chart, attention list, recent movements |
| `/products` | Search/filter/sort/paginate, modal create/edit/delete, product links |
| `/movements` | Filter by product and type, record IN/OUT/ADJUST in a modal |
| `/categories` | Searchable list with product counts and full CRUD modals |
| `/suppliers` | Searchable list with product counts and full CRUD modals |
| `/settings` | Theme control, read-only USD currency, version, links, seed command |

The theme toggle in the top bar switches light/dark and saves the choice in `localStorage`
(`sp-theme`). See `backend/README.md` for deeper API, migration and data details.

## API summary

- `GET /api/health`
- `GET/POST /api/products`; `GET/PATCH/DELETE /api/products/{id}`
- `GET/POST /api/products/{id}/movements`; `GET /api/movements`
- `GET/POST /api/categories`; `GET/PATCH/DELETE /api/categories/{id}`
- `GET/POST /api/suppliers`; `GET/PATCH/DELETE /api/suppliers/{id}`
- `GET /api/stats`
- `GET /api/export/products.csv`, `GET /api/export/movements.csv`

Product listing accepts `q`, `low_stock`, `out_of_stock`, `is_active`, `category_id`,
`supplier_id`, `sort`, `page` and `page_size`. Duplicate SKUs/category names/supplier names
are rejected with `409` (case-insensitive, enforced by expression indexes). Stock movements
are immutable, and products with movement history cannot be deleted.

## Tests and lint

From `backend/`:

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

The suite covers the JSON API, services, migrations, UI pages and security guards. To verify
migrations against a scratch database, set `DATABASE_URL` to a temporary SQLite file and run
`python -m alembic upgrade head` followed by `python -m alembic check`.

## Structure

```
stockpilot/
├── README.md               # this file
├── PLAN.md                 # build plan and v1.1 roadmap
├── .gitignore
├── archive/                # legacy tutorial code (git-ignored)
└── backend/
    ├── pyproject.toml, requirements.lock, .env.example
    ├── alembic.ini, alembic/
    ├── app/
    │   ├── main.py         # app, same-origin guard, static mount
    │   ├── core/config.py
    │   ├── db/, models/, schemas/, routers/, services/
    │   ├── templates/      # base, pages and partials (modals, tables)
    │   └── static/         # css/app.css, js/app.js
    ├── scripts/seed.py
    └── tests/              # API, domain, migrations and UI tests
```

## Security and local-only use

v1 has **no authentication and no CSRF tokens**. Run the server bound to `127.0.0.1` and do
not expose it to an untrusted network. State-changing requests (`POST`, `PATCH`, `PUT`,
`DELETE`) carrying an `Origin` or `Referer` from another host are rejected with `403`;
requests without those headers (CLI tools, scripts, tests) are allowed. `DEBUG` defaults to
`false`, and CSV string cells are sanitised against spreadsheet formulas. See `PLAN.md` for
deferred security work.

## Deferred to v1.1

- Authentication, users/roles and CSRF tokens before any network exposure.
- Configurable currency/defaults in a real settings model (v1 settings is informational).
- Self-hosted/pinned front-end assets and Subresource Integrity for all CDN links.
- Production deployment, HTTPS and remote database configuration.

## AI roadmap (v1.1)

- Natural-language chat assistant calling the JSON API.
- Demand forecasting and reorder suggestions.
- Receipt/invoice OCR to create stock movements.
- Stock anomaly detection.
- Auto-categorisation and semantic search.
