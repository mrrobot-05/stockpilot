# Architecture

StockPilot is a single Python process: one FastAPI app serves both the JSON API under `/api`
and server-rendered HTML pages. There is no separate frontend build, no Node runtime at serve
time and no Docker image.

## Request flow

```text
Browser / CLI
    │
    ▼
FastAPI app (backend/app/main.py)
    ├─ same_origin_guard middleware (POST/PATCH/PUT/DELETE)
    ├─ /static            → css/app.css, js/app.js, favicon.svg
    ├─ /api/*             → JSON routers → Pydantic schemas → services → SQLAlchemy
    └─ /dashboard, /products, ... → pages router → Jinja2 templates
                                      ├─ full page for a normal GET
                                      └─ table/modal partial for HX-Request
    │
    ▼
SQLite (backend/stockpilot.db, or DATABASE_URL)
```

- `main.py` mounts static files and includes the API and pages routers. Page routes carry
  `include_in_schema=False`, so `/docs` documents only the API.
- `app/routers/pages.py` owns all HTML routes, the `money` and `dt` Jinja filters, and the
  HTMX/form handling. Table partials use `hx-target`/`hx-swap="outerHTML"`; modals swap into
  `#modal-root` and are shown by `static/js/app.js`.
- Forms post to HTML routes that parse `Form` fields, build the same Pydantic schemas used by
  the API, and call the same services. Success returns a refreshed table plus
  `HX-Retarget`, `HX-Reswap` and `HX-Trigger` headers (`closeModal`, `showToast`); errors
  re-render the modal at HTTP 200 so HTMX will swap it.
- Services in `app/services/` are the single source of domain truth. Routers (API and HTML)
  are thin adapters over them.

## Data model

| Model | Key fields | Notes |
| --- | --- | --- |
| `Product` | `sku`, `name`, `category_id`, `supplier_id`, cost/sell price, `quantity`, `reorder_level`, `is_active` | Opening stock is set at creation and creates no ledger row. |
| `Category` | `name`, `description` | Unique name; product count is computed by a grouped query. |
| `Supplier` | `name`, contact/email/phone/address/notes | Unique name; product count is computed by a grouped query. |
| `StockMovement` | `product_id`, `movement_type`, `quantity`, `quantity_change`, `stock_after`, `note`, `created_at` | Immutable ledger; no PATCH/DELETE routes. |

Expression indexes (`lower(sku)`, `lower(name)`) enforce case-insensitive uniqueness at the
database layer, backing the API's `409` checks. Deleting a category or supplier nulls the
matching products' references rather than deleting the products.

## Ledger invariant

A product's `quantity` is changed **only** through `create_movement` in
`app/services/movements.py`:

- `IN`: `UPDATE products SET quantity = quantity + q WHERE id = id`; `quantity_change = q`.
- `OUT`: `UPDATE ... SET quantity = quantity - q WHERE id = id AND quantity >= q`. A zero
  `rowcount` rolls back and returns `409 Insufficient stock`, so concurrent issues cannot
  oversell.
- `ADJUST`: `UPDATE ... SET quantity = q WHERE id = id`; `quantity_change = new - old`.

The product is refreshed from the database before the ledger row is inserted, so
`stock_after` always equals the committed stock level after the movement. `synchronize_session=False`
prevents a stale identity-map value from leaking into the update. Movements are never edited;
products with movement history cannot be deleted.

## Security posture

- **Local-only:** bind `127.0.0.1`; no auth, users, roles or CSRF tokens in v1.
- **Same-origin guard:** for unsafe methods, any supplied `Origin`/`Referer` host must match
  `request.url.hostname`; mismatches get `403`. Missing headers are allowed so CLI clients,
  TestClient and scripts still work.
- **Safe defaults:** `DEBUG=false`; `.env.example` contains no secrets and `.env` is ignored.
- **CSV hygiene:** string cells starting with `=`, `+`, `-` or `@` are prefixed with `'` to
  prevent spreadsheet formula injection.
- **Future work:** authentication and CSRF tokens, self-hosted/pinned front-end assets with
  full SRI coverage, HTTPS and production deployment. See [../PLAN.md](../PLAN.md) and
  [../SECURITY.md](../SECURITY.md).
