from pydantic import BaseModel

from app.schemas.movement import MovementRead


class StatsRead(BaseModel):
    total_products: int
    active_products: int
    total_stock_units: int
    stock_cost_value: float
    stock_retail_value: float
    low_stock_count: int
    out_of_stock_count: int
    category_count: int
    supplier_count: int
    recent_movements: list[MovementRead]
