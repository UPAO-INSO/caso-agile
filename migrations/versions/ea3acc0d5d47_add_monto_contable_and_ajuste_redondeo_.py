"""add_monto_contable_and_ajuste_redondeo_to_pagos

Revision ID: ea3acc0d5d47
Revises: d946ab8ccbcd
Create Date: 2025-12-09 11:44:43.268825

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea3acc0d5d47'
down_revision = 'd946ab8ccbcd'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar columna monto_contable (nullable para datos existentes)
    op.add_column('pagos', sa.Column('monto_contable', sa.Numeric(precision=12, scale=2), nullable=True, comment='Deuda contable de la cuota'))
    
    # Agregar columna ajuste_redondeo con valor por defecto
    op.add_column('pagos', sa.Column('ajuste_redondeo', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00', comment='Pérdida/Ganancia por redondeo (Ley N° 29571)'))


def downgrade():
    # Eliminar las columnas agregadas
    op.drop_column('pagos', 'ajuste_redondeo')
    op.drop_column('pagos', 'monto_contable')
