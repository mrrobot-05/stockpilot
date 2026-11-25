from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import (
    categories,
    exports,
    health,
    movements,
    pages,
    products,
    stats,
    suppliers,
)

app = FastAPI(title=settings.app_name, version="0.1.0")

STATE_CHANGING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


@app.middleware("http")
async def same_origin_guard(request: Request, call_next):
    """Reject writes whose Origin/Referer points at another host.

    Requests without either header (CLI clients, TestClient, curl scripts) are allowed;
    v1 has no auth or CSRF tokens, so browsers are protected at the network boundary.
    """
    if request.method in STATE_CHANGING_METHODS:
        expected = (request.url.hostname or "").lower()
        for header in ("origin", "referer"):
            value = request.headers.get(header)
            if value is None:
                continue
            host = urlparse(value).hostname
            if host is None or host.lower() != expected:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-origin request blocked"},
                )
    return await call_next(request)


app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)

app.include_router(health.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
app.include_router(movements.router)
app.include_router(stats.router)
app.include_router(exports.router)
app.include_router(pages.router)
