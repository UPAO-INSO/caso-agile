"""add aperturas_caja table

Revision ID: c3a4b5d6e7f
Revises: b2_add_metodo_pago_back
Create Date: 2025-12-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c3a4b5d6e7f'
down_revision = 'b2_add_metodo_pago_back'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'aperturas_caja',
        sa.Column('apertura_id', sa.Integer(), primary_key=True),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('monto', sa.Numeric(12, 2), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_aperturas_caja_fecha'), 'aperturas_caja', ['fecha'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_aperturas_caja_fecha'), table_name='aperturas_caja')
    op.drop_table('aperturas_caja')
