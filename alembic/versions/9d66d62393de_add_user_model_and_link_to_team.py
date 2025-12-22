"""add_user_model_and_link_to_team

Revision ID: 9d66d62393de
Revises: 
Create Date: 2025-12-22 06:11:22.577157

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '9d66d62393de'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create team_status enum type (only if it doesn't exist)
    # Use DO block to safely create enum type
    conn = op.get_bind()
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE team_status AS ENUM ('REGISTERED', 'PAID_CONFIRMED', 'PAID_REJECTED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    conn.commit()
    
    # Use the enum type (it should exist now, don't try to create it)
    # Use postgresql.ENUM with create_type=False to prevent auto-creation
    team_status_enum = postgresql.ENUM('REGISTERED', 'PAID_CONFIRMED', 'PAID_REJECTED', name='team_status', create_type=False)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False, comment='Họ và tên'),
        sa.Column('username', sa.String(length=100), nullable=False, comment='Tên đăng nhập'),
        sa.Column('email', sa.String(length=255), nullable=False, comment='Email'),
        sa.Column('hashed_password', sa.String(length=255), nullable=False, comment='Mật khẩu đã hash'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Tài khoản có hoạt động không'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create teams table (without enum column first to avoid auto-creation)
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True, comment='Email liên hệ'),
        sa.Column('team_name', sa.String(length=255), nullable=False, comment='Tên đội bóng'),
        sa.Column('leader_name', sa.String(length=255), nullable=False, comment='Tên đội trưởng'),
        sa.Column('leader_student_id', sa.String(length=50), nullable=True, comment='Mã sinh viên đội trưởng'),
        sa.Column('phone', sa.String(length=20), nullable=False, comment='Số điện thoại đội trưởng'),
        sa.Column('vice_leader_name', sa.String(length=255), nullable=True, comment='Họ và tên đội phó'),
        sa.Column('vice_leader_student_id', sa.String(length=50), nullable=True, comment='Mã sinh viên đội phó'),
        sa.Column('vice_leader_phone', sa.String(length=20), nullable=True, comment='Số điện thoại đội phó'),
        sa.Column('members_list_file', sa.String(length=500), nullable=True, comment='File danh sách thành viên (path)'),
        sa.Column('members_list_text', sa.Text(), nullable=True, comment='Danh sách thành viên (text backup)'),
        sa.Column('order_id', sa.String(length=100), nullable=False, comment='Mã đơn hàng MoMo duy nhất'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0', comment='Số tiền đăng ký'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True, comment='Thời điểm thanh toán thành công'),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='ID đại diện đội (User)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    # Add enum column using raw SQL to avoid auto-creation
    op.execute(sa.text("""
        ALTER TABLE teams 
        ADD COLUMN status team_status NOT NULL DEFAULT 'REGISTERED';
    """))
    op.create_index(op.f('ix_teams_id'), 'teams', ['id'], unique=False)
    op.create_index(op.f('ix_teams_order_id'), 'teams', ['order_id'], unique=True)
    op.create_index(op.f('ix_teams_status'), 'teams', ['status'], unique=False)
    op.create_index(op.f('ix_teams_user_id'), 'teams', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop teams table
    op.drop_index(op.f('ix_teams_user_id'), table_name='teams')
    op.drop_index(op.f('ix_teams_status'), table_name='teams')
    op.drop_index(op.f('ix_teams_order_id'), table_name='teams')
    op.drop_index(op.f('ix_teams_id'), table_name='teams')
    op.drop_table('teams')
    
    # Drop users table
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    
    # Drop enum type
    team_status_enum = postgresql.ENUM('REGISTERED', 'PAID_CONFIRMED', 'PAID_REJECTED', name='team_status')
    team_status_enum.drop(op.get_bind(), checkfirst=True)

