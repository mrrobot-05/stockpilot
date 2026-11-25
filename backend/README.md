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
.\.venv\Scripts\uvicorn app.main:app --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

## Test and lint

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

## API

- `GET /api/health`
- `GET /api/products` — `q`, `low_stock`, `sort`, `page`, `page_size`, `category_id`,
  `supplier_id`, `is_active`
- `POST /api/products`
- `GET /api/products/{id}`
- `PATCH /api/products/{id}`
- `DELETE /api/products/{id}`
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

Sort accepts `id`, `sku`, `name`, `quantity`, `sell_price`, `created_at`; prefix with `-` for
descending. Duplicate SKUs are rejected with `409` (case-insensitive), as are duplicate
category and supplier names. Product reads include nested `category` and `supplier` briefs.
Deleting a category or supplier sets the matching products' references to `null`.
