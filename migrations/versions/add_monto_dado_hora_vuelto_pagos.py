"""add monto_dado hora_pago vuelto to pagos

Revision ID: add_monto_dado_hora_vuelto
Revises: 3053b6dad6e3
Create Date: 2025-12-10 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_monto_dado_hora_vuelto'
down_revision = '3053b6dad6e3'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar columnas nuevas al modelo Pago
    op.add_column('pagos', sa.Column('hora_pago', sa.Time(), nullable=True, comment='Hora en que se realizó el pago'))
    op.add_column('pagos', sa.Column('monto_dado', sa.Numeric(precision=12, scale=2), nullable=True, comment='Monto entregado por el cliente (billetes)'))
    op.add_column('pagos', sa.Column('vuelto', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00', comment='Vuelto entregado al cliente'))


def downgrade():
    # Revertir cambios
    op.drop_column('pagos', 'vuelto')
    op.drop_column('pagos', 'monto_dado')
    op.drop_column('pagos', 'hora_pago')
