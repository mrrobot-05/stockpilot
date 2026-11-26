# Screenshots

This repository intentionally does not ship screenshots. If you would like to add them for a
fork or a release note, capture them locally with the real app:

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

4. Capture at **1280×800** (desktop) and **360×740** (mobile). Use your browser's dev tools
   device toolbar or a screenshot extension; no Node/npm build is needed.
5. Optionally toggle dark mode and capture the dashboard again.

Save files here using descriptive names such as `dashboard-desktop.png` and
`products-mobile.png`, then reference them from a release note. Do not commit `.env`,
`*.db` files, browser profiles or any personal data visible in the screenshots.
