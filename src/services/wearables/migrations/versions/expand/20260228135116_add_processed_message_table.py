"""add processed_message table

Revision ID: 6f3b055b226d
Revises: 177032a51f43
Create Date: 2026-02-28 13:51:16.948873
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6f3b055b226d"
down_revision: Union[str, None] = "177032a51f43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processed_message",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("logical_id", sa.Uuid(), nullable=False),
        sa.Column("message_code", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("logical_id", "message_code"),
    )


def downgrade() -> None:
    pass
