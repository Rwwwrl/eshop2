"""initial expand branch

Revision ID: c9373c730ebf
Revises:
Create Date: 2026-02-12 22:53:44.475913
"""

from typing import Sequence, Union

# NOTE @sosov: Empty migration that establishes the expand branch.
# All additive schema changes (CREATE, ADD) go here.
revision: str = "c9373c730ebf"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("expand",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
