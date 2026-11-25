from pathlib import Path

from fastapi import FastAPI
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
