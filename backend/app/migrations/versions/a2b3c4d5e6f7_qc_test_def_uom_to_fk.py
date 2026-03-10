"""Change qc_test_definitions.uom string to uom_id FK

Revision ID: a2b3c4d5e6f7
Revises: f13dbf42ab10
Create Date: 2026-03-10 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f13dbf42ab10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add uom_id column as FK to units_of_measure
    op.add_column('qc_test_definitions', sa.Column('uom_id', sa.Integer(), sa.ForeignKey('units_of_measure.id'), nullable=True))
    # Drop old string uom column (if it exists)
    try:
        op.drop_column('qc_test_definitions', 'uom')
    except Exception:
        pass  # Column may not exist if table was created after this change


def downgrade() -> None:
    op.add_column('qc_test_definitions', sa.Column('uom', sa.String(50), nullable=True))
    try:
        op.drop_column('qc_test_definitions', 'uom_id')
    except Exception:
        pass
