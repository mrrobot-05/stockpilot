from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_OPTIONAL_TEXT_FIELDS = ("contact_name", "email", "phone", "address", "notes")


class _SupplierValidators(BaseModel):
    """Shared normalization rules for supplier input schemas."""

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

    @field_validator(*_OPTIONAL_TEXT_FIELDS, mode="before", check_fields=False)
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class SupplierBase(_SupplierValidators):
    name: str = Field(min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)


class SupplierCreate(SupplierBase):
    """Payload for creating a supplier."""


class SupplierUpdate(_SupplierValidators):
    """Payload for partially updating a supplier; omitted fields stay unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    notes: str | None
    product_count: int = 0
    created_at: datetime
    updated_at: datetime


class SupplierBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
