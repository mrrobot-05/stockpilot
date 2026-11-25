from fastapi import FastAPI

from app.core.config import settings
from app.routers import categories, health, products, suppliers

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(health.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
