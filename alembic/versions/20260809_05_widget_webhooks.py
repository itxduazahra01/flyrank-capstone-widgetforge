"""Add per-widget webhook destinations.

Revision ID: 20260809_05
Revises: 20260809_04
"""
from alembic import op
import sqlalchemy as sa


revision = "20260809_05"
down_revision = "20260809_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "widget_webhooks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("widget_id", sa.String(length=36), sa.ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_widget_webhooks_tenant_id", "widget_webhooks", ["tenant_id"])
    op.create_index("ix_widget_webhooks_widget_id", "widget_webhooks", ["widget_id"])


def downgrade() -> None:
    op.drop_table("widget_webhooks")
