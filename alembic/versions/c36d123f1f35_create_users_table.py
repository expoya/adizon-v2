"""create_users_table

Revision ID: c36d123f1f35
Revises: 
Create Date: 2025-12-29 10:54:58.269767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c36d123f1f35'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table for Adizon User-Management."""
    # Create ENUM type for UserRole (drop if exists first)
    op.execute("DROP TYPE IF EXISTS userrole CASCADE")
    user_role_enum = postgresql.ENUM('user', 'admin', name='userrole', create_type=False)
    user_role_enum.create(op.get_bind(), checkfirst=False)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('telegram_id', sa.String(100), nullable=True, unique=True),
        sa.Column('slack_id', sa.String(100), nullable=True, unique=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('role', user_role_enum, nullable=False, server_default='user'),
        sa.Column('crm_display_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])
    op.create_index('ix_users_slack_id', 'users', ['slack_id'])


def downgrade() -> None:
    """Drop users table."""
    op.drop_index('ix_users_slack_id', table_name='users')
    op.drop_index('ix_users_telegram_id', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    
    # Drop ENUM type
    user_role_enum = postgresql.ENUM('user', 'admin', name='userrole')
    user_role_enum.drop(op.get_bind(), checkfirst=True)
