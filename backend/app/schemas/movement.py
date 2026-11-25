from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import MovementType


class MovementCreate(BaseModel):
    movement_type: MovementType
    quantity: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def normalize_note(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def check_quantity_for_type(self) -> Self:
        if (
            self.movement_type in (MovementType.IN, MovementType.OUT)
            and self.quantity < 1
        ):
            raise ValueError("IN and OUT movements require quantity >= 1")
        return self


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str


class MovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product: ProductBrief
    movement_type: MovementType
    quantity: int
    quantity_change: int
    stock_after: int
    note: str | None
    created_at: datetime


class MovementPage(BaseModel):
    items: list[MovementRead]
    total: int
    page: int
    page_size: int
    pages: int
