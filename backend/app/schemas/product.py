from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.category import CategoryBrief
from app.schemas.supplier import SupplierBrief


class _ProductValidators(BaseModel):
    """Shared normalization and validation rules for product input schemas."""

    @field_validator("sku", mode="before", check_fields=False)
    @classmethod
    def normalize_sku(cls, value: object) -> object:
        if value is None:
            raise ValueError("sku must be a string")
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("name", "description", mode="before", check_fields=False)
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name", check_fields=False)
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None or len(value) < 1:
            raise ValueError("name must contain at least one character")
        return value

    @field_validator("cost_price", "sell_price", check_fields=False)
    @classmethod
    def validate_price(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            raise ValueError("price must be a number")
        if value < 0:
            raise ValueError("price must be greater than or equal to zero")
        return value

    @field_validator("quantity", "reorder_level", check_fields=False)
    @classmethod
    def validate_count(cls, value: int | None) -> int | None:
        if value is None:
            raise ValueError("value must be an integer")
        if value < 0:
            raise ValueError("value must be greater than or equal to zero")
        return value

    @field_validator("is_active", check_fields=False)
    @classmethod
    def validate_is_active(cls, value: bool | None) -> bool | None:
        if value is None:
            raise ValueError("is_active must be a boolean")
        return value


class ProductBase(_ProductValidators):
    sku: str = Field(max_length=64)
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category_id: int | None = None
    supplier_id: int | None = None
    cost_price: Decimal = Decimal("0")
    sell_price: Decimal = Decimal("0")
    quantity: int = 0
    reorder_level: int = 0
    is_active: bool = True


class ProductCreate(ProductBase):
    """Payload for creating a product."""


class ProductUpdate(_ProductValidators):
    """Payload for partially updating a product; omitted fields stay unchanged."""

    sku: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category_id: int | None = None
    supplier_id: int | None = None
    cost_price: Decimal | None = None
    sell_price: Decimal | None = None
    quantity: int | None = None
    reorder_level: int | None = None
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    category_id: int | None
    supplier_id: int | None
    category: CategoryBrief | None = None
    supplier: SupplierBrief | None = None
    cost_price: Decimal
    sell_price: Decimal
    quantity: int
    reorder_level: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Pydantic v2 uses `when_used="json"` for JSON-only serializers;
    # `mode` instead selects a plain vs. wrap serializer function.
    @field_serializer("cost_price", "sell_price", when_used="json")
    def _money_to_float(self, value: Decimal) -> float:
        return float(value)


class ProductPage(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
    pages: int
