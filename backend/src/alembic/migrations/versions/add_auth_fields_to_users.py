"""add auth fields to users

Revision ID: b1c2d3e4f5a6
Revises: ad8bbd515d7b
Create Date: 2026-05-08 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'ad8bbd515d7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make telegram_id nullable (existing rows keep their values)
    op.alter_column('users', 'telegram_id', nullable=True)

    # Add new columns for web auth
    op.add_column('users', sa.Column('email', sa.String(), nullable=True))
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=True))
    op.add_column('users', sa.Column('name', sa.String(), nullable=True))

    # Unique index on email (only for non-null values — PostgreSQL allows multiple NULLs)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_email', table_name='users')
    op.drop_column('users', 'name')
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'email')
    op.alter_column('users', 'telegram_id', nullable=False)
