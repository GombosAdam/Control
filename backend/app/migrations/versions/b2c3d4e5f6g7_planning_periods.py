"""planning periods - new table and budget_lines FK

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-22 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'planning_periods',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('start_month', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('end_month', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('plan_type', sa.String(8), nullable=False, server_default='budget'),
        sa.Column('scenario_id', sa.String(36), sa.ForeignKey('scenarios.id'), nullable=True),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.add_column(
        'budget_lines',
        sa.Column('planning_period_id', sa.String(36), sa.ForeignKey('planning_periods.id'), nullable=True),
    )
    op.create_index('ix_budget_lines_planning_period_id', 'budget_lines', ['planning_period_id'])


def downgrade() -> None:
    op.drop_index('ix_budget_lines_planning_period_id', table_name='budget_lines')
    op.drop_column('budget_lines', 'planning_period_id')
    op.drop_table('planning_periods')
