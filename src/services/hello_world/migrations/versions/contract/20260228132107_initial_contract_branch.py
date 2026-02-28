"""initial contract branch

Revision ID: d0838b381690
Revises:
Create Date: 2026-02-28 13:21:07.106750
"""

from typing import Sequence, Union

revision: str = "d0838b381690"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("contract",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
