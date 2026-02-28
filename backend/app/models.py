import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    order_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    client: Mapped[str | None] = mapped_column(String, nullable=True)
    insured_name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    address1: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    zip: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Active")
    due_date: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    custom_values: Mapped[list["OrderCustomField"]] = relationship("OrderCustomField", back_populates="order", cascade="all, delete-orphan")


class CustomFieldDefinition(Base):
    __tablename__ = "custom_fields_definitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    label: Mapped[str] = mapped_column(String)
    field_type: Mapped[str] = mapped_column(String, default="string")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrderCustomField(Base):
    __tablename__ = "order_custom_fields"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    custom_field_id: Mapped[str] = mapped_column(ForeignKey("custom_fields_definitions.id", ondelete="CASCADE"), index=True)
    value: Mapped[str] = mapped_column(Text)

    order: Mapped[Order] = relationship("Order", back_populates="custom_values")
    custom_field: Mapped[CustomFieldDefinition] = relationship("CustomFieldDefinition")


class SavedView(Base):
    __tablename__ = "saved_views"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    columns: Mapped[list] = mapped_column(JSON, default=list)
    sorts: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    entity_type: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class GeocodeCache(Base):
    __tablename__ = "geocode_cache"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    normalized_address: Mapped[str] = mapped_column(String, unique=True, index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text)
