"""add preferred_stack to users

Revision ID: c2d3e4f5a6b7
Revises: d1fcecdd8add
Create Date: 2026-05-13 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'd1fcecdd8add'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('preferred_stack', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'preferred_stack')
