"""merge

Revision ID: 63dd86b6a8f1
Revises: c588bb1ef699
Create Date: 2026-04-23 21:01:31.573998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63dd86b6a8f1'
down_revision: Union[str, Sequence[str], None] = 'c588bb1ef699'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
