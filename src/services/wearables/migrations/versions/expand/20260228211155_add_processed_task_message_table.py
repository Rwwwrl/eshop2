"""add processed_task_message table

Revision ID: fd214703c05c
Revises: 6f3b055b226d
Create Date: 2026-02-28 21:11:55.648913
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fd214703c05c"
down_revision: Union[str, None] = "6f3b055b226d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processed_task_message",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("logical_id", sa.Uuid(), nullable=False),
        sa.Column("task_message_code", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("logical_id", "task_message_code"),
    )


def downgrade() -> None:
    pass
