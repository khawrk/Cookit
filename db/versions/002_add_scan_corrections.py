"""add_scan_corrections

Revision ID: 002
Revises: 001
Create Date: 2026-04-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scan_corrections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("original_quantity", sa.Float(), nullable=True),
        sa.Column("original_unit", sa.String(50), nullable=True),
        sa.Column("corrected_name", sa.String(255), nullable=False),
        sa.Column("corrected_quantity", sa.Float(), nullable=True),
        sa.Column("corrected_unit", sa.String(50), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_scan_corrections_user_created", "scan_corrections", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_scan_corrections_user_created", table_name="scan_corrections")
    op.drop_table("scan_corrections")
