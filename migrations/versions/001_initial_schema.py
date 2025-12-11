"""Initial database schema - All tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-12-10 13:41:00.000000

Esta migración crea el esquema completo de la base de datos incluyendo:
- Tabla clientes
- Tabla declaraciones_juradas
- Tabla prestamos
- Tabla cuotas
- Tabla pagos
- Tabla usuarios
- Tabla egresos
- Tabla aperturas_caja
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Crear todas las tablas del sistema"""
    
    # ==================== ENUM TYPES ====================
    # Los tipos ENUM se crearán automáticamente cuando se creen las tablas
    # para evitar errores de duplicación
    
    # ==================== TABLA CLIENTES ====================
    op.create_table(
        'clientes',
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('dni', sa.String(length=8), nullable=False),
        sa.Column('nombre_completo', sa.String(length=200), nullable=False),
        sa.Column('apellido_paterno', sa.String(length=100), nullable=False),
        sa.Column('apellido_materno', sa.String(length=100), nullable=True),
        sa.Column('correo_electronico', sa.String(length=100), nullable=False),
        sa.Column('pep', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('fecha_registro', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('cliente_id'),
        sa.UniqueConstraint('dni', name='uq_cliente_dni')
    )
    op.create_index('ix_clientes_dni', 'clientes', ['dni'])
    
    # ==================== TABLA DECLARACIONES JURADAS ====================
    op.create_table(
        'declaraciones_juradas',
        sa.Column('declaracion_id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('tipo_declaracion', postgresql.ENUM('USO_PROPIO', 'PEP', 'AMBOS', name='tipodeclaracionenum'), nullable=False),
        sa.Column('fecha_firma', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
        sa.Column('contenido', sa.Text(), nullable=True),
        sa.Column('firmado', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.cliente_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('declaracion_id')
    )
    op.create_index('ix_declaraciones_cliente_id', 'declaraciones_juradas', ['cliente_id'])
    
    # ==================== TABLA PRESTAMOS ====================
    op.create_table(
        'prestamos',
        sa.Column('prestamo_id', sa.Integer(), nullable=False),
        sa.Column('monto_total', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('interes_tea', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('plazo', sa.Integer(), nullable=False),
        sa.Column('f_otorgamiento', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
        sa.Column('f_registro', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('estado', postgresql.ENUM('VIGENTE', 'CANCELADO', name='estadoprestamoenum'), nullable=False, server_default='VIGENTE'),
        sa.Column('requiere_dec_jurada', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('declaracion_id', sa.Integer(), nullable=True),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.CheckConstraint('(requiere_dec_jurada = FALSE) OR (declaracion_id IS NOT NULL)', name='chk_declaracion_si_requerida'),
        sa.CheckConstraint('interes_tea >= 0 AND interes_tea <= 100', name='chk_interes_tea_rango'),
        sa.CheckConstraint('monto_total > 0', name='chk_monto_total_positivo'),
        sa.CheckConstraint('plazo > 0', name='chk_plazo_positivo'),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.cliente_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['declaracion_id'], ['declaraciones_juradas.declaracion_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('prestamo_id')
    )
    op.create_index('ix_prestamos_cliente_id', 'prestamos', ['cliente_id'])
    op.create_index('ix_prestamos_estado', 'prestamos', ['estado'])
    
    # ==================== TABLA CUOTAS ====================
    op.create_table(
        'cuotas',
        sa.Column('cuota_id', sa.Integer(), nullable=False),
        sa.Column('numero_cuota', sa.Integer(), nullable=False),
        sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
        sa.Column('monto_cuota', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('monto_capital', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('monto_interes', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('saldo_capital', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('fecha_pago', sa.Date(), nullable=True),
        sa.Column('monto_pagado', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('es_cuota_ajuste', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('prestamo_id', sa.Integer(), nullable=False),
        # Campos de mora
        sa.Column('mora_acumulada', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('mora_generada', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('saldo_pendiente', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.CheckConstraint('monto_cuota > 0', name='chk_monto_cuota_positivo'),
        sa.CheckConstraint('numero_cuota > 0', name='chk_numero_cuota_positivo'),
        sa.CheckConstraint('mora_acumulada >= 0', name='chk_mora_acumulada_no_negativa'),
        sa.CheckConstraint('saldo_pendiente >= 0', name='chk_saldo_pendiente_no_negativo'),
        sa.ForeignKeyConstraint(['prestamo_id'], ['prestamos.prestamo_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cuota_id'),
        sa.UniqueConstraint('prestamo_id', 'numero_cuota', name='uq_prestamo_numero_cuota')
    )
    op.create_index('ix_cuotas_prestamo_id', 'cuotas', ['prestamo_id'])
    op.create_index('ix_cuotas_fecha_vencimiento', 'cuotas', ['fecha_vencimiento'])
    
    # ==================== TABLA PAGOS ====================
    op.create_table(
        'pagos',
        sa.Column('pago_id', sa.Integer(), nullable=False),
        sa.Column('cuota_id', sa.Integer(), nullable=False),
        sa.Column('medio_pago', postgresql.ENUM(
            'EFECTIVO', 'TARJETA_DEBITO', 'TARJETA_CREDITO', 
            'TRANSFERENCIA', 'YAPE', 'PLIN',
            name='mediopagoenum'
        ), nullable=False),
        # Montos
        sa.Column('monto_contable', sa.Numeric(precision=12, scale=2), nullable=True, comment='Deuda contable de la cuota'),
        sa.Column('monto_pagado', sa.Numeric(precision=12, scale=2), nullable=False, comment='Monto recibido en caja'),
        sa.Column('monto_mora', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0', comment='Mora pagada'),
        sa.Column('ajuste_redondeo', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0', comment='Pérdida/Ganancia por redondeo'),
        # Datos de pago en efectivo
        sa.Column('hora_pago', sa.Time(), nullable=True, comment='Hora en que se realizó el pago'),
        sa.Column('monto_dado', sa.Numeric(precision=12, scale=2), nullable=True, comment='Monto entregado por el cliente (efectivo)'),
        sa.Column('vuelto', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00', comment='Vuelto entregado al cliente'),
        # Fechas
        sa.Column('fecha_pago', sa.Date(), nullable=False),
        # Comprobantes y observaciones
        sa.Column('comprobante_referencia', sa.String(length=100), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=True),
        # Constraints
        sa.CheckConstraint('monto_pagado > 0', name='chk_monto_pagado_positivo'),
        sa.CheckConstraint('monto_mora >= 0', name='chk_monto_mora_no_negativo'),
        sa.CheckConstraint('ajuste_redondeo >= 0', name='chk_ajuste_redondeo_no_negativo'),
        sa.CheckConstraint('vuelto >= 0', name='chk_vuelto_no_negativo'),
        sa.ForeignKeyConstraint(['cuota_id'], ['cuotas.cuota_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('pago_id')
    )
    op.create_index('ix_pagos_cuota_id', 'pagos', ['cuota_id'])
    op.create_index('ix_pagos_fecha_pago', 'pagos', ['fecha_pago'])
    op.create_index('ix_pagos_medio_pago', 'pagos', ['medio_pago'])
    
    # ==================== TABLA USUARIOS ====================
    op.create_table(
        'usuarios',
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('usuario', sa.String(length=50), nullable=False),
        sa.Column('correo', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('nombre_completo', sa.String(length=200), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('rol', sa.String(length=50), nullable=False, server_default='usuario'),
        sa.Column('fecha_creacion', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('fecha_ultima_conexion', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('usuario_id'),
        sa.UniqueConstraint('correo', name='uq_usuario_correo'),
        sa.UniqueConstraint('usuario', name='uq_usuario_usuario')
    )
    op.create_index('ix_usuarios_usuario', 'usuarios', ['usuario'])
    op.create_index('ix_usuarios_correo', 'usuarios', ['correo'])
    
    # ==================== TABLA EGRESOS ====================
    op.create_table(
        'egresos',
        sa.Column('egreso_id', sa.Integer(), nullable=False),
        sa.Column('pago_id', sa.Integer(), nullable=True),
        sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('concepto', sa.String(length=255), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('monto > 0', name='chk_monto_egreso_positivo'),
        sa.ForeignKeyConstraint(['pago_id'], ['pagos.pago_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('egreso_id')
    )
    op.create_index('ix_egresos_fecha_registro', 'egresos', ['fecha_registro'])
    op.create_index('ix_egresos_pago_id', 'egresos', ['pago_id'])
    
    # ==================== TABLA APERTURAS CAJA ====================
    op.create_table(
        'aperturas_caja',
        sa.Column('apertura_id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('monto >= 0', name='chk_monto_apertura_no_negativo'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('apertura_id')
    )
    op.create_index('ix_aperturas_caja_fecha', 'aperturas_caja', ['fecha'], unique=False)
    
    # ==================== DATOS INICIALES ====================
    # Crear usuario administrador por defecto
    # Password hash para 'admin123' generado con werkzeug.security
    from werkzeug.security import generate_password_hash
    admin_password_hash = generate_password_hash('admin123')
    
    op.execute(f"""
        INSERT INTO usuarios (usuario, correo, password_hash, nombre_completo, activo, rol)
        VALUES ('admin', 'admin@prestamos.com', '{admin_password_hash}', 'Administrador del Sistema', true, 'admin')
    """)


def downgrade():
    """Eliminar todas las tablas en orden inverso"""
    
    # Eliminar tablas en orden inverso (respetando foreign keys)
    op.drop_table('aperturas_caja')
    op.drop_table('egresos')
    op.drop_table('usuarios')
    op.drop_table('pagos')
    op.drop_table('cuotas')
    op.drop_table('prestamos')
    op.drop_table('declaraciones_juradas')
    op.drop_table('clientes')
    
    # Eliminar tipos ENUM
    postgresql.ENUM(name='mediopagoenum').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='estadoprestamoenum').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='tipodeclaracionenum').drop(op.get_bind(), checkfirst=True)
