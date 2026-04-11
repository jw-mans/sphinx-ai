"""add user_notes to interviews

Revision ID: a1b2c3d4e5f6
Revises: 585a3fd6e5fb
Create Date: 2026-04-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3e585e0d7a5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interviews', sa.Column('user_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('interviews', 'user_notes')
