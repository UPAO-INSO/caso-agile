"""Re-add metodo_pago column to pagos

Revision ID: b2_add_metodo_pago_back
Revises: a1f2c3d4e5b
Create Date: 2025-12-10 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2_add_metodo_pago_back'
down_revision = 'a1f2c3d4e5b'
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM type if not exists and add column with default to avoid issues
    metod_enum = postgresql.ENUM('EFECTIVO', 'TARJETA', 'TRANSFERENCIA', name='metodopagoenum')
    metod_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('pagos', sa.Column('metodo_pago', postgresql.ENUM('EFECTIVO', 'TARJETA', 'TRANSFERENCIA', name='metodopagoenum'), nullable=False, server_default='EFECTIVO'))
    # remove server_default
    with op.get_context().autocommit_block():
        op.alter_column('pagos', 'metodo_pago', server_default=None)


def downgrade():
    op.drop_column('pagos', 'metodo_pago')
    # Optionally drop enum type if desired
    postgresql.ENUM(name='metodopagoenum').drop(op.get_bind(), checkfirst=True)
