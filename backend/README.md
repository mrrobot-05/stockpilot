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
Regenerate it from an updated environment with
`pip freeze --exclude-editable > requirements.lock`.

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

## API (Phase 1)

- `GET /api/health`
- `GET /api/products` — `q`, `low_stock`, `sort`, `page`, `page_size`
- `POST /api/products`
- `GET /api/products/{id}`
- `PATCH /api/products/{id}`
- `DELETE /api/products/{id}`

Sort accepts `id`, `sku`, `name`, `quantity`, `sell_price`, `created_at`; prefix with `-` for
descending. Duplicate SKUs are rejected with `409` (case-insensitive).
