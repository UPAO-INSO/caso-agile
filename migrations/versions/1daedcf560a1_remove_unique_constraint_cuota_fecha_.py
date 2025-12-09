"""remove_unique_constraint_cuota_fecha_pago

Revision ID: 1daedcf560a1
Revises: dd1a32861bbe
Create Date: 2025-12-09 11:50:08.637042

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1daedcf560a1'
down_revision = 'dd1a32861bbe'
branch_labels = None
depends_on = None


def upgrade():
    # Eliminar constraint único que impide múltiples pagos el mismo día
    op.drop_constraint('uq_cuota_fecha_pago', 'pagos', type_='unique')


def downgrade():
    # Recrear constraint si se hace rollback
    op.create_unique_constraint('uq_cuota_fecha_pago', 'pagos', ['cuota_id', 'fecha_pago'])
