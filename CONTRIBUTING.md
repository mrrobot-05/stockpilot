# Contributing

Thanks for helping improve StockPilot. Please keep changes focused and local-first: no new
runtime dependencies without discussion, and no changes to the JSON API contract unless the
issue calls for it.

## Setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m scripts.seed   # optional demo data
```

On macOS/Linux use `source .venv/bin/activate` and `cp .env.example .env`.

## Tests and lint

Run these from `backend/` before opening a pull request:

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

CI repeats those checks on Python 3.12 and 3.13, applies migrations against a temporary
`ci.db`, runs `alembic check`, and validates `app/static/js/app.js` with `node --check`.
If you change a model, add an Alembic migration under `backend/alembic/versions/` and verify
`alembic check` reports no pending operations.

## Working on the UI

- Server-rendered pages live in `backend/app/templates/`; shared pieces are in `partials/`.
- Table fragments are swapped with HTMX using `hx-target`/`hx-swap`; modals render into
  `#modal-root` and are shown by `app/static/js/app.js`.
- Reuse the existing filters (`money`, `dt`), CSS tokens (`--sp-*`) and toast helper.
- There is no Node build step. A CDN link change should preserve integrity hashes where
  available.

## Commit style

Use short, conventional-style subjects:

- `feat(ui): add barcode lookup`
- `fix: guard duplicate sku on concurrent create`
- `docs: clarify local-only setup`
- `chore: bump pinned dev tooling`

Keep one logical change per commit, write tests for bug fixes, and never commit secrets,
`.env`, `*.db` files or generated screenshots.

## Pull requests

Fill in the template with a summary and test evidence. Link the issue you are addressing, and
call out any API contract or migration changes explicitly. See
[.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).

## Security issues

Do not file public issues for vulnerabilities; follow [SECURITY.md](SECURITY.md).
