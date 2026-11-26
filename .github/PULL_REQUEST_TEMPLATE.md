## Summary

<!-- What changed and why? Link any related issue (e.g. Closes #12). -->

## Type of change

- [ ] Feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Chore / tooling

## Testing

- [ ] `python -m pytest -q` passes in `backend/`
- [ ] `python -m ruff check .` passes in `backend/`
- [ ] `alembic check` passes against a clean database (model changes only)
- [ ] `node --check backend/app/static/js/app.js` passes (JS changes only)

Describe any manual verification (pages visited, browser/viewport checks):

## Checklist

- [ ] No secrets, `.env` files, databases or screenshots committed
- [ ] API contracts unchanged, or the change is called out above
- [ ] New Alembic migration added if models changed
- [ ] Docs/README updated if behaviour changed
- [ ] Commits follow the style in [CONTRIBUTING.md](../CONTRIBUTING.md)
