from fastapi import FastAPI

from app.core.config import settings
from app.routers import categories, exports, health, movements, products, stats, suppliers

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(health.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
app.include_router(movements.router)
app.include_router(stats.router)
app.include_router(exports.router)
