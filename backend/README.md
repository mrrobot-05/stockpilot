# StockPilot backend

FastAPI + SQLAlchemy 2 + Alembic JSON API for StockPilot. Python 3.11+ required.

## Setup

From `backend/`:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env
```

On macOS/Linux use `source .venv/bin/activate` and `cp .env.example .env` instead.

## Exact reproduction

`pyproject.toml` intentionally uses open-ended version ranges. For a byte-for-byte
reproducible environment, install the pinned lock file instead (after creating the venv):

```powershell
.\.venv\Scripts\python -m pip install -r requirements.lock
```

`requirements.lock` pins the runtime and dev dependencies that were tested together.
Regenerate it from an updated environment as plain UTF-8 (PowerShell's `>` writes UTF-16):

```powershell
.\.venv\Scripts\python -m pip freeze --exclude-editable | .\.venv\Scripts\python -c "import sys; open('requirements.lock','w',encoding='utf-8',newline='\n').write(sys.stdin.read())"
```

## Database

The default database is SQLite at `backend/stockpilot.db`. Create/update the schema with Alembic:

```powershell
.\.venv\Scripts\python -m alembic upgrade head
```

To create a new migration after changing a model:

```powershell
.\.venv\Scripts\python -m alembic revision --autogenerate -m "describe change"
```

## Run

```powershell
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

> **Local only.** v1 has no authentication and no CSRF tokens. Keep the server bound to
> `127.0.0.1` and do not expose it to an untrusted network. State-changing requests
> (`POST`, `PATCH`, `PUT`, `DELETE`) that carry an `Origin` or `Referer` header from a
> different host are rejected with `403`; requests without those headers (CLI tools,
> scripts and tests) are allowed. `DEBUG` defaults to `false`.

## UI

The server-rendered UI (Jinja2 + Bootstrap 5.3 + HTMX + Chart.js via CDN) runs on the same app.
Start the server from `backend/` and open http://127.0.0.1:8000/ — it redirects to
`/dashboard`. The theme toggle in the top bar switches between light and dark mode and
remembers your choice in `localStorage`; the export dropdown downloads the same CSV files as
the API.

Current UI pages:

| Page | Purpose |
| --- | --- |
| `/dashboard` | Totals, stock value, chart, attention list, recent movements |
| `/products` | Search/filter/sort/paginate; modal create, edit and delete |
| `/movements` | Filtered ledger and the record-movement modal (IN / OUT / ADJUST) |
| `/categories` | Searchable list with product counts and full CRUD modals |
| `/suppliers` | Searchable list with product counts and full CRUD modals |
| `/settings` | Theme control, read-only USD, version, API/CSV links and seed command |

All page routes are excluded from the OpenAPI schema; only `/api` endpoints are documented
at `/docs`.

A fresh database has an empty-state dashboard. Load demo data with:

```powershell
.\.venv\Scripts\python -m scripts.seed
```

Run that from `backend/` after `alembic upgrade head`. The seed is idempotent and skips when
products already exist.

## Test and lint

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

## API

- `GET /api/health`
- `GET /api/products` — `q`, `low_stock`, `out_of_stock`, `sort`, `page`, `page_size`,
  `category_id`, `supplier_id`, `is_active`
- `POST /api/products`
- `GET /api/products/{id}`
- `PATCH /api/products/{id}`
- `DELETE /api/products/{id}`
- `POST /api/products/{id}/movements` — record IN / OUT / ADJUST
- `GET /api/products/{id}/movements` — history for one product
- `GET /api/movements` — `product_id`, `movement_type`, `page`, `page_size`, `sort`
- `GET /api/categories` — optional `q`
- `POST /api/categories`
- `GET /api/categories/{id}`
- `PATCH /api/categories/{id}`
- `DELETE /api/categories/{id}`
- `GET /api/suppliers` — optional `q`
- `POST /api/suppliers`
- `GET /api/suppliers/{id}`
- `PATCH /api/suppliers/{id}`
- `DELETE /api/suppliers/{id}`
- `GET /api/stats` — dashboard totals, counts and the latest 10 movements
- `GET /api/export/products.csv`
- `GET /api/export/movements.csv`

Sort accepts `id`, `sku`, `name`, `quantity`, `sell_price`, `created_at`; prefix with `-` for
descending. Duplicate SKUs are rejected with `409` (case-insensitive), as are duplicate
category and supplier names. Product reads include nested `category` and `supplier` briefs.
Deleting a category or supplier sets the matching products' references to `null`.

`low_stock` means `0 < quantity <= reorder_level`; `out_of_stock` means `quantity == 0`.
They are independent filters on `/api/products` and can be combined with `q`, `category_id`
and `supplier_id`.

## Stock movements

Stock is changed only through the movement ledger; `PATCH /api/products/{id}` rejects
`quantity` with `422` ("Use the stock movements API to change quantity"). `ProductCreate.quantity`
is opening stock and creates no movement row.

- `IN`: `quantity >= 1`, adds to stock.
- `OUT`: `quantity >= 1`, subtracts from stock; insufficient stock returns `409`.
- `ADJUST`: `quantity >= 0` is the **new absolute stock level**; `quantity_change` is
  `new - old` and may be negative.

Each movement records `quantity`, signed `quantity_change`, `stock_after`, and an optional
`note`, and is applied to the product in the same transaction. Movements are immutable —
there are no PATCH or DELETE endpoints. Products with movement history cannot be deleted
(`409`). Movement list sorting accepts `id`, `created_at`, `quantity`, `movement_type`,
`stock_after`; prefix with `-` for descending (default `-created_at`).

## Dashboard and data export

`/api/stats` returns product/stock totals, stock cost and retail values, low-stock
(`0 < quantity <= reorder_level`) and out-of-stock counts, category/supplier counts, and
the 10 most recent movements with nested product briefs. All figures are plain JSON
numbers.

The CSV endpoints stream downloadable files (`Content-Disposition: attachment`) with a
stable header row. Products are ordered by id; movements by `created_at`, `id`.

`low_stock` means `0 < quantity <= reorder_level`; `out_of_stock` means `quantity == 0`.
Both filters are available on `/api/products`, and the dashboard's "Needs attention" list
merges the two, sorted by quantity.

## Seed data

After `alembic upgrade head`, load demo data from `backend/`:

```powershell
.\.venv\Scripts\python -m scripts.seed
```

The seed is idempotent: it prints a skip message and changes nothing when any products
already exist. It creates three categories, three suppliers, eight products and ten
movements. Opening stock is set at product creation (`quantity`) and produces no movement
rows; subsequent sales, a restock and a stocktake correction are recorded in the ledger.
