"""reply content text

Revision ID: a7c9d1f4b8e2
Revises: d95b0a590f6a
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = 'a7c9d1f4b8e2'
down_revision: Union[str, Sequence[str], None] = 'd95b0a590f6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'reply',
        'content',
        existing_type=sa.VARCHAR(length=100),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'reply',
        'content',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(length=100),
        existing_nullable=False,
    )