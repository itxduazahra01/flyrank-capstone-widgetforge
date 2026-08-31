"""Add privacy-conscious widget funnel events.

Revision ID: 20260809_03
Revises: 20260809_02
"""
from alembic import op
import sqlalchemy as sa


revision = "20260809_03"
down_revision = "20260809_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "widget_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("widget_id", sa.String(length=36), sa.ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("source_origin", sa.String(length=300)),
        sa.Column("session_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_widget_events_tenant_id", "widget_events", ["tenant_id"])
    op.create_index("ix_widget_events_widget_id", "widget_events", ["widget_id"])
    op.create_index("ix_widget_events_event_type", "widget_events", ["event_type"])
    op.create_index("ix_widget_events_created_at", "widget_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("widget_events")
