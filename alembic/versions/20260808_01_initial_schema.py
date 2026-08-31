"""Create the WidgetForge core schema.

Revision ID: 20260808_01
Revises:
"""
from alembic import op
import sqlalchemy as sa


revision = "20260808_01"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps(table):
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ] if table else []


def upgrade() -> None:
    op.create_table("tenants", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(120), nullable=False, unique=True), *_timestamps(True))
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("email", sa.String(254), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), *_timestamps(True))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table("widgets", sa.Column("id", sa.String(36), primary_key=True), sa.Column("public_id", sa.String(36), nullable=False, unique=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("widget_type", sa.String(30), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("description", sa.Text()), sa.Column("form_fields", sa.JSON(), nullable=False), sa.Column("button_text", sa.String(80), nullable=False), sa.Column("display_options", sa.JSON(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("config_version", sa.Integer(), nullable=False), *_timestamps(True), sa.UniqueConstraint("tenant_id", "id", name="uq_widget_tenant_id"))
    op.create_index("ix_widgets_tenant_id", "widgets", ["tenant_id"])
    op.create_index("ix_widgets_public_id", "widgets", ["public_id"])
    op.create_table("submissions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("widget_id", sa.String(36), sa.ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False), sa.Column("idempotency_key", sa.String(64), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("source_origin", sa.String(300)), sa.Column("ip_hash", sa.String(128), nullable=False), sa.Column("geo_country", sa.String(100)), sa.Column("geo_city", sa.String(100)), sa.Column("geo_provider", sa.String(50)), sa.Column("spam_status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("widget_id", "idempotency_key", name="uq_submission_idempotency"))
    op.create_index("ix_submissions_tenant_id", "submissions", ["tenant_id"])
    op.create_index("ix_submissions_widget_id", "submissions", ["widget_id"])
    op.create_table("outbox_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_type", sa.String(60), nullable=False), sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("attempt_count", sa.Integer(), nullable=False), sa.Column("last_error", sa.String(500)), sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), *_timestamps(True))
    op.create_index("ix_outbox_events_submission_id", "outbox_events", ["submission_id"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("submissions")
    op.drop_table("widgets")
    op.drop_table("users")
    op.drop_table("tenants")
