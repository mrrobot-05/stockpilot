from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _CategoryValidators(BaseModel):
    """Shared normalization rules for category input schemas."""

    @field_validator("name", mode="before", check_fields=False)
    @classmethod
    def strip_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name", check_fields=False)
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None or len(value) < 1:
            raise ValueError("name must contain at least one character")
        return value

    @field_validator("description", mode="before", check_fields=False)
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class CategoryBase(_CategoryValidators):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class CategoryCreate(CategoryBase):
    """Payload for creating a category."""


class CategoryUpdate(_CategoryValidators):
    """Payload for partially updating a category; omitted fields stay unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    product_count: int = 0
    created_at: datetime
    updated_at: datetime


class CategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
