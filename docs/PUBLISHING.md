# Publishing StockPilot

Target repository: <https://github.com/mrrobot-05/stockpilot>
Default branch: `main`

## Repository settings

**Description**

```text
Local-first inventory manager with a FastAPI JSON API, a Jinja2/Bootstrap/HTMX UI, an atomic stock ledger, CSV exports and SQLite.
```

**Suggested topics**

```text
fastapi sqlalchemy sqlite jinja2 bootstrap htmx inventory-management python alembic
```

Set the repository to **public**, keep Issues enabled, and use the issue and pull request
templates under `.github/`. Website can be left blank: StockPilot is local-only and has no
public deployment.

## Before pushing

From the repository root:

```powershell
git status --short                       # must be empty
git branch --show-current                # main
git log --format="%h %an <%ae>" -5       # Aditya Kale <adityakale5002@gmail.com>
git grep -n -i ("tel" + "usko")          # no output
$bad = @(('1234' + '5678'), ('password' + '='), ('BEGIN PRIVATE ' + 'KEY'))
git grep -n -i -E ($bad -join '|')
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

Also confirm no `.venv/`, `*.db`, `__pycache__/`, `*.egg-info/` or `.env` files are tracked:

```powershell
cd ..
git ls-files | Select-String '\.venv/|\.db$|__pycache__|egg-info|\.env$'
```

Only `.env.example` should appear if you broaden the pattern to `.env*`.

## Push with GitHub CLI

```powershell
gh auth status
gh repo create mrrobot-05/stockpilot --public --source=. --remote=origin --push
```

If the repository already exists, add the remote and push instead:

```powershell
git remote add origin https://github.com/mrrobot-05/stockpilot.git
git push -u origin main
```

Do not paste an access token into chat or commit it; authenticate through `gh auth login` or
a credential helper.

## Push manually

1. Create an empty public repository named `stockpilot` under the `mrrobot-05` account.
2. Do **not** initialise it with a README, license or `.gitignore` — the local repo already has them.
3. From the local repo:

   ```powershell
   git remote add origin https://github.com/mrrobot-05/stockpilot.git
   git push -u origin main
   ```

## Post-push checks

- `gh repo view --json name,visibility,url` reports `stockpilot`, `PUBLIC` and the expected URL.
- The CI workflow runs on Python 3.12 and 3.13 and passes (tests, ruff, Alembic, JS syntax).
- The README CI badge is green and all relative documentation links resolve.
- `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md` and `.github/` templates are visible.
- Running the quickstart locally still reaches `/dashboard` and `/docs`.
- No secrets, databases or browser profiles were uploaded.

## Screenshots

See [screenshots/README.md](screenshots/README.md) for how to capture dashboard, products,
movements and settings at desktop and mobile sizes. Screenshots are not committed in v1; if
you add them later, capture from seeded demo data and redact any personal information.
