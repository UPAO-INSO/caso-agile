"""add_monto_contable_ajuste_redondeo_to_pagos_fixed

Revision ID: dd1a32861bbe
Revises: 019a1c7790fc
Create Date: 2025-12-09 11:46:00.196054

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd1a32861bbe'
down_revision = '019a1c7790fc'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar columna monto_contable (nullable para datos existentes)
    op.add_column('pagos', sa.Column('monto_contable', sa.Numeric(precision=12, scale=2), nullable=True, comment='Deuda contable de la cuota'))
    
    # Agregar columna ajuste_redondeo con valor por defecto
    op.add_column('pagos', sa.Column('ajuste_redondeo', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00', comment='Pérdida/Ganancia por redondeo (Ley N° 29571)'))
    
    # Agregar constraint único para evitar pagos duplicados en la misma fecha
    op.create_unique_constraint('uq_cuota_fecha_pago', 'pagos', ['cuota_id', 'fecha_pago'])


def downgrade():
    # Eliminar constraint
    op.drop_constraint('uq_cuota_fecha_pago', 'pagos', type_='unique')
    
    # Eliminar las columnas agregadas
    op.drop_column('pagos', 'ajuste_redondeo')
    op.drop_column('pagos', 'monto_contable')
