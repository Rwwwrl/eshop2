"""initial expand branch

Revision ID: 48385ed04096
Revises:
Create Date: 2026-02-28 13:21:03.633125
"""

from typing import Sequence, Union

revision: str = "48385ed04096"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("expand",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
