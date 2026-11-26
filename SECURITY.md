# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | ✅ |

## Local-only by design

StockPilot v1 has **no authentication, no users/roles and no CSRF tokens**. It is intended to
run on a single machine, bound to `127.0.0.1`. Do not expose it to an untrusted network or
deploy it publicly. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the current security
posture.

Protections that do exist:

- `DEBUG` defaults to `false`.
- `POST`, `PATCH`, `PUT` and `DELETE` requests carrying an `Origin` or `Referer` from another
  host are rejected with `403`; requests without those headers are allowed for CLI/TestClient use.
- CSV string cells beginning with `=`, `+`, `-` or `@` are prefixed with `'` so spreadsheets
  treat them as text, not formulas.
- No secrets are committed; copy `.env.example` to `.env` locally.

Reporting a vulnerability privately
-----------------------------------

Please **do not open a public issue** for a security problem. Use GitHub's private
"Report a vulnerability" feature on this repository, or email
`adityakale5002@gmail.com` with:

- a short description and the affected version/commit,
- steps to reproduce (include a minimal request or payload),
- the impact you observed and any suggested fix.

You should receive an acknowledgement within a few days. Please give maintainers a reasonable
window to fix the issue before public disclosure.

## Out of scope

- Attacks that require the attacker to already have local access to the machine.
- Issues caused by exposing StockPilot to a network despite the local-only guidance.
- Third-party CDN behaviour (Bootstrap, Bootstrap Icons, HTMX, Chart.js, Google Fonts).
