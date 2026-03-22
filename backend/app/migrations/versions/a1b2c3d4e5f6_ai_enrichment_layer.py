"""ai enrichment layer - new table and columns

Revision ID: a1b2c3d4e5f6
Revises: 4f30aab9c35c
Create Date: 2026-03-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4f30aab9c35c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ai_enrichments table
    op.create_table(
        'ai_enrichments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('invoice_id', sa.String(36), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('enrichment_type', sa.String(50), nullable=False),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('accepted', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Invoice: add AI enrichment fields
    op.add_column('invoices', sa.Column('suggested_accounting_code', sa.String(20), nullable=True))
    op.add_column('invoices', sa.Column('anomaly_flags', sa.JSON(), nullable=True))
    op.add_column('invoices', sa.Column('ai_confidence', sa.Float(), nullable=True))

    # Partner: add vector and accounting fields
    op.add_column('partners', sa.Column('vector_id', sa.String(100), nullable=True))
    op.add_column('partners', sa.Column('default_accounting_code', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('partners', 'default_accounting_code')
    op.drop_column('partners', 'vector_id')
    op.drop_column('invoices', 'ai_confidence')
    op.drop_column('invoices', 'anomaly_flags')
    op.drop_column('invoices', 'suggested_accounting_code')
    op.drop_table('ai_enrichments')
