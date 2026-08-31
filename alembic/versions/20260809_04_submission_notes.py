"""Add private owner notes to submissions.

Revision ID: 20260809_04
Revises: 20260809_03
"""
from alembic import op
import sqlalchemy as sa


revision = "20260809_04"
down_revision = "20260809_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("submissions", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_column("submissions", "updated_at")
    op.drop_column("submissions", "notes")
