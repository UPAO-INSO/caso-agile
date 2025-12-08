"""add_pago_table

Revision ID: add_pago_table
Revises: 1cf38e205110
Create Date: 2024-12-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_pago_table'
down_revision = '1cf38e205110'
branch_labels = None
depends_on = None


def upgrade():
     # Verificar si la tabla 'pagos' existe, y si es así, eliminarla
    if op.get_bind().engine.dialect.has_table(op.get_bind(), 'pagos'):
        op.drop_table('pagos')
    
    # Eliminar enums si existen
    op.execute('DROP TYPE IF EXISTS estadopagoenum')
    op.execute('DROP TYPE IF EXISTS mediopagoenum')
    
    # Crear tabla pagos nueva
    op.create_table(
        'pagos',
        sa.Column('pago_id', sa.Integer(), nullable=False),
        sa.Column('cuota_id', sa.Integer(), nullable=False),
        sa.Column('monto_pagado', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('monto_mora', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('fecha_pago', sa.Date(), nullable=False),
        sa.Column('medio_pago', sa.Enum('EFECTIVO', 'TARJETA_DEBITO', 'TARJETA_CREDITO', 'TRANSFERENCIA', 'BILLETERA_ELECTRONICA', 'PAGO_AUTOMATICO', name='mediopagoenum'), nullable=False),
        sa.Column('comprobante_referencia', sa.String(length=100), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.CheckConstraint('monto_pagado > 0', name='chk_monto_pagado_positivo'),
        sa.CheckConstraint('monto_mora >= 0', name='chk_monto_mora_no_negativo'),
        sa.ForeignKeyConstraint(['cuota_id'], ['cuotas.cuota_id'], ),
        sa.PrimaryKeyConstraint('pago_id')
    )

    # Crear índice para mejorar búsquedas
    op.create_index('ix_pagos_cuota_id', 'pagos', ['cuota_id'])

def downgrade():
    op.drop_table('pagos')
    op.execute('DROP TYPE IF EXISTS mediopagoenum')