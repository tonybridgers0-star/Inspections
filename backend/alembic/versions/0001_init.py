"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-01-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("orders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("order_number", sa.String(), nullable=False),
        sa.Column("client", sa.String()),
        sa.Column("insured_name", sa.String()),
        sa.Column("phone", sa.String()),
        sa.Column("address1", sa.String()),
        sa.Column("city", sa.String()),
        sa.Column("state", sa.String()),
        sa.Column("zip", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("due_date", sa.String()),
        sa.Column("notes", sa.Text()),
        sa.Column("lat", sa.Float()),
        sa.Column("lon", sa.Float()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)

    op.create_table("custom_fields_definitions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("field_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_custom_fields_definitions_key", "custom_fields_definitions", ["key"], unique=True)

    op.create_table("order_custom_fields",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("custom_field_id", sa.String(), sa.ForeignKey("custom_fields_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
    )
    op.create_index("ix_order_custom_fields_order_id", "order_custom_fields", ["order_id"])

    op.create_table("saved_views",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("sorts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    op.create_table("activity_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("before", sa.JSON()),
        sa.Column("after", sa.JSON()),
        sa.Column("created_at", sa.DateTime()),
    )

    op.create_table("geocode_cache",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("normalized_address", sa.String(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_geocode_cache_normalized_address", "geocode_cache", ["normalized_address"], unique=True)

    op.create_table("app_settings",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_geocode_cache_normalized_address", table_name="geocode_cache")
    op.drop_table("geocode_cache")
    op.drop_table("activity_log")
    op.drop_table("saved_views")
    op.drop_table("order_custom_fields")
    op.drop_index("ix_custom_fields_definitions_key", table_name="custom_fields_definitions")
    op.drop_table("custom_fields_definitions")
    op.drop_index("ix_orders_order_number", table_name="orders")
    op.drop_table("orders")
