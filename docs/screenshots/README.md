# Screenshots

This folder contains 1440×1000 PNGs of all six v1 pages, captured from seeded demo data with
headless Microsoft Edge. To regenerate them (or capture a different theme/data set), use the
real app locally:

1. From `backend/`, create and seed a fresh database:

   ```powershell
   .\.venv\Scripts\python -m alembic upgrade head
   .\.venv\Scripts\python -m scripts.seed
   ```

2. Start the server bound to localhost:

   ```powershell
   .\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. Open <http://127.0.0.1:8000/>. Useful screens:

   | Page | What to show |
   | --- | --- |
   | `/dashboard` | Stat cards, stock-health chart, attention list, recent movements |
   | `/products` | Filters, table badges, pagination, one open modal |
   | `/movements` | Type filter and the record-movement modal |
   | `/settings` | Theme control and information cards |

4. Capture at **1440×1000** for parity with the committed images (or **360×740** for a mobile
   check). Headless Edge/Chrome works well with a CDN-friendly time budget:

   ```powershell
   msedge --headless=new --disable-gpu --hide-scrollbars --window-size=1440,1000 `
     --virtual-time-budget=8000 --screenshot=docs\screenshots\dashboard.png `
     http://127.0.0.1:8000/dashboard
   ```

5. Optionally toggle the theme in the top bar and capture again; screenshots inherit the
   browser's colour-scheme preference when no `sp-theme` value is stored.

Save files here using descriptive names such as `dashboard-desktop.png` and
`products-mobile.png`, then reference them from a release note. Do not commit `.env`,
`*.db` files, browser profiles or any personal data visible in the screenshots.
