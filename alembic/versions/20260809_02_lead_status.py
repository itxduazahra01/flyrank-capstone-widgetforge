"""Add lifecycle status to captured leads.

Revision ID: 20260809_02
Revises: 20260808_01
"""
from alembic import op
import sqlalchemy as sa


revision = "20260809_02"
down_revision = "20260808_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("lead_status", sa.String(length=20), nullable=False, server_default="new"))
    op.create_index("ix_submissions_lead_status", "submissions", ["lead_status"])
    op.alter_column("submissions", "lead_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_submissions_lead_status", table_name="submissions")
    op.drop_column("submissions", "lead_status")
