"""add_is_admin_column_if_exists

Revision ID: 39805178a2a6
Revises: 185e877726ed
Create Date: 2025-12-22 13:34:12.796129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '39805178a2a6'
down_revision = '185e877726ed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_admin column to users table if it doesn't exist
    # This migration is safe to run even if column already exists
    from sqlalchemy import text
    conn = op.get_bind()
    
    # Check if column exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'users' 
            AND column_name = 'is_admin'
        );
    """))
    column_exists = result.scalar()
    
    if not column_exists:
        # Add column using raw SQL with IF NOT EXISTS equivalent
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT false;
        """))
        conn.commit()
    else:
        # Column already exists, do nothing
        pass


def downgrade() -> None:
    # Remove is_admin column from users table
    from sqlalchemy import text
    conn = op.get_bind()
    
    # Check if column exists before dropping
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'users' 
            AND column_name = 'is_admin'
        );
    """))
    column_exists = result.scalar()
    
    if column_exists:
        conn.execute(text("ALTER TABLE users DROP COLUMN is_admin;"))
        conn.commit()

