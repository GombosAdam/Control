"""add assigned_to to purchase_order_approvals

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-04-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('purchase_order_approvals',
        sa.Column('assigned_to', sa.String(36), sa.ForeignKey('users.id'), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('purchase_order_approvals', 'assigned_to')
