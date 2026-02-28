from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OrderBase(BaseModel):
    order_number: str
    client: str | None = None
    insured_name: str | None = None
    phone: str | None = None
    address1: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    status: str = "Active"
    due_date: str | None = None
    notes: str | None = None
    lat: float | None = None
    lon: float | None = None


class OrderCreate(OrderBase):
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class OrderUpdate(BaseModel):
    client: str | None = None
    insured_name: str | None = None
    phone: str | None = None
    address1: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    status: str | None = None
    due_date: str | None = None
    notes: str | None = None
    lat: float | None = None
    lon: float | None = None
    custom_fields: dict[str, Any] | None = None


class OrderOut(OrderBase):
    id: str
    completed_at: datetime | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class SavedViewIn(BaseModel):
    name: str
    filters: dict = Field(default_factory=dict)
    columns: list[str] = Field(default_factory=list)
    sorts: list[dict] = Field(default_factory=list)


class SavedViewOut(SavedViewIn):
    id: str

    class Config:
        from_attributes = True


class CustomFieldIn(BaseModel):
    key: str
    label: str
    field_type: str = "string"


class CustomFieldOut(CustomFieldIn):
    id: str

    class Config:
        from_attributes = True
