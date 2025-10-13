from sqlalchemy.orm import relationship
from . import db

import enum

# Definimos los ENUMs en Python para usarlos en nuestros modelos
class EstadoPrestamoEnum(enum.Enum):
    VIGENTE = 'VIGENTE'
    CANCELADO = 'CANCELADO'

class TipoDeclaracionEnum(enum.Enum):
    USO_PROPIO = 'USO_PROPIO'
    PEP = 'PEP'
    AMBOS = 'AMBOS'

# --- MODELOS DE LAS TABLAS ---

class Cliente(db.Model):
    __tablename__ = 'clientes'

    cliente_id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(8), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(200), nullable=False)
    apellido_paterno = db.Column(db.String(100), nullable=False)
    apellido_materno = db.Column(db.String(100))
    pep = db.Column(db.Boolean, default=False, nullable=False)
    fecha_registro = db.Column(db.DateTime, server_default=db.func.now())

    # Relaciones Lógicas (para Python)
    prestamos = relationship("Prestamo", back_populates="cliente")
    declaraciones_juradas = relationship("DeclaracionJurada", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente: DNI:{self.dni} - NOMBRES:{self.nombre_completo} - PEP:{self.pep}>"


class DeclaracionJurada(db.Model):
    __tablename__ = 'declaraciones_juradas'

    declaracion_id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.cliente_id'), nullable=False)
    tipo_declaracion = db.Column(db.Enum(TipoDeclaracionEnum), nullable=False)
    fecha_firma = db.Column(db.Date, nullable=False, server_default=db.func.current_date())
    contenido = db.Column(db.Text)
    firmado = db.Column(db.Boolean, default=False, nullable=False)

    # Relaciones Lógicas
    cliente = relationship("Cliente", back_populates="declaraciones_juradas")
    prestamo = relationship("Prestamo", back_populates="declaracion_jurada", uselist=False) # Una DJ pertenece a un solo préstamo

    def __repr__(self):
        return f"<DeclaracionJurada ID {self.declaracion_id} para Cliente ID {self.cliente_id}>"


class Prestamo(db.Model):
    __tablename__ = 'prestamos'

    prestamo_id = db.Column(db.Integer, primary_key=True)
    monto_total = db.Column(db.Numeric(12, 2), nullable=False)
    interes_tea = db.Column(db.Numeric(5, 2), nullable=False)
    plazo = db.Column(db.Integer, nullable=False)
    f_otorgamiento = db.Column(db.Date, nullable=False, server_default=db.func.current_date())
    f_registro = db.Column(db.DateTime, server_default=db.func.now())
    estado = db.Column(db.Enum(EstadoPrestamoEnum), default=EstadoPrestamoEnum.VIGENTE, nullable=False)
    
    # --- Lógica de la Declaración Jurada ---
    requiere_dec_jurada = db.Column(db.Boolean, nullable=False)
    declaracion_id = db.Column(db.Integer, db.ForeignKey('declaraciones_juradas.declaracion_id'), nullable=True)
    
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.cliente_id'), nullable=False)
    
    # Relaciones Lógicas
    cliente = relationship("Cliente", back_populates="prestamos")
    declaracion_jurada = relationship("DeclaracionJurada", back_populates="prestamo", uselist=False)
    cuotas = relationship("Cuota", back_populates="prestamo", cascade="all, delete-orphan")

    # --- VALIDACIONES A NIVEL DE TABLA ---
    __table_args__ = (
        db.CheckConstraint(
            '(requiere_dec_jurada = FALSE) OR (declaracion_id IS NOT NULL)',
            name='chk_declaracion_si_requerida'
        ),
        # --- VALIDACIONES AÑADIDAS ---
        db.CheckConstraint('monto_total > 0', name='chk_monto_total_positivo'),
        db.CheckConstraint('interes_tea >= 0 AND interes_tea <= 100', name='chk_interes_tea_rango'),
        db.CheckConstraint('plazo > 0', name='chk_plazo_positivo'),
    )

    def __repr__(self):
        return f"<Prestamo ID {self.prestamo_id} por S/ {self.monto_total}>"


class Cuota(db.Model):
    __tablename__ = 'cuotas'

    cuota_id = db.Column(db.Integer, primary_key=True)
    numero_cuota = db.Column(db.Integer, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    monto_cuota = db.Column(db.Numeric(12, 2), nullable=False)
    monto_capital = db.Column(db.Numeric(12, 2), nullable=False)
    monto_interes = db.Column(db.Numeric(12, 2), nullable=False)
    saldo_capital = db.Column(db.Numeric(12, 2), nullable=False)
    fecha_pago = db.Column(db.Date, nullable=True)
    monto_pagado = db.Column(db.Numeric(12, 2), nullable=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey('prestamos.prestamo_id'), nullable=False)

    # Relación Lógica
    prestamo = relationship("Prestamo", back_populates="cuotas")

     # --- VALIDACIONES A NIVEL DE TABLA ---
    __table_args__ = (
        db.UniqueConstraint('prestamo_id', 'numero_cuota', name='uq_prestamo_numero_cuota'),
        # --- VALIDACIONES AÑADIDAS ---
        db.CheckConstraint('numero_cuota > 0', name='chk_numero_cuota_positivo'),
        db.CheckConstraint('monto_cuota > 0', name='chk_monto_cuota_positivo'),
    )

    def __repr__(self):
        return f"<Cuota {self.numero_cuota} de Prestamo ID {self.prestamo_id}>"