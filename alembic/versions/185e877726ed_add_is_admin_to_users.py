"""add_is_admin_to_users

Revision ID: 185e877726ed
Revises: 9d66d62393de
Create Date: 2025-12-22 13:11:23.029355

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '185e877726ed'
down_revision = '9d66d62393de'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_admin column to users table
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false', comment='Tài khoản admin'))


def downgrade() -> None:
    # Remove is_admin column from users table
    op.drop_column('users', 'is_admin')

