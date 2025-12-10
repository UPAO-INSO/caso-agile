"""Add egresos table

Revision ID: a1f2c3d4e5b
Revises: 59d23688588f
Create Date: 2025-12-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1f2c3d4e5b'
down_revision = '59d23688588f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'egresos',
        sa.Column('egreso_id', sa.Integer(), nullable=False),
        sa.Column('pago_id', sa.Integer(), nullable=True),
        sa.Column('monto', sa.Numeric(12, 2), nullable=False),
        sa.Column('concepto', sa.String(length=255), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pago_id'], ['pagos.pago_id'], ),
        sa.PrimaryKeyConstraint('egreso_id')
    )


def downgrade():
    op.drop_table('egresos')
