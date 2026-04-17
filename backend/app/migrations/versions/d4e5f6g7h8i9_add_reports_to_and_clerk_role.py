"""add positions table, position_id to users, clerk role

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-04-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False),
        sa.Column('reports_to_id', sa.String(36), sa.ForeignKey('positions.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Add position_id to users
    op.add_column('users',
        sa.Column('position_id', sa.String(36), sa.ForeignKey('positions.id'), nullable=True)
    )

    # Add clerk to userrole enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'clerk'")

    # Drop reports_to if it exists (was added in same session but now replaced by positions)
    try:
        op.drop_constraint('users_reports_to_fkey', 'users', type_='foreignkey')
        op.drop_column('users', 'reports_to')
    except Exception:
        pass


def downgrade() -> None:
    op.drop_column('users', 'position_id')
    op.drop_table('positions')
