"""initial contract branch

Revision ID: 6a478a0eca57
Revises:
Create Date: 2026-02-12 22:50:49.010868
"""

from typing import Sequence, Union

# NOTE @sosov: Empty migration that establishes the contract branch.
# All destructive schema changes (DROP, REMOVE) go here.
revision: str = "6a478a0eca57"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("contract",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
