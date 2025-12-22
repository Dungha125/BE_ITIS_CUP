"""add_request_id_to_teams

Revision ID: fbe4bf76bbd3
Revises: 39805178a2a6
Create Date: 2025-12-22 14:28:11.244040

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fbe4bf76bbd3'
down_revision = '39805178a2a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add request_id column to teams table
    op.add_column('teams', sa.Column('request_id', sa.String(100), nullable=True))
    op.create_index(op.f('ix_teams_request_id'), 'teams', ['request_id'], unique=False)


def downgrade() -> None:
    # Remove request_id column from teams table
    op.drop_index(op.f('ix_teams_request_id'), table_name='teams')
    op.drop_column('teams', 'request_id')

