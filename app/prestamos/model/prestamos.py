from sqlalchemy.orm import relationship
from ... import db
import enum


class EstadoPrestamoEnum(enum.Enum):
    VIGENTE = 'VIGENTE'
    CANCELADO = 'CANCELADO'


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

    __table_args__ = (
        db.CheckConstraint(
            '(requiere_dec_jurada = FALSE) OR (declaracion_id IS NOT NULL)',
            name='chk_declaracion_si_requerida'
        ),
        db.CheckConstraint('monto_total > 0', name='chk_monto_total_positivo'),
        db.CheckConstraint('interes_tea >= 0 AND interes_tea <= 100', name='chk_interes_tea_rango'),
        db.CheckConstraint('plazo > 0', name='chk_plazo_positivo'),
    )

    def __repr__(self):
        return f"<Prestamo ID {self.prestamo_id} por S/ {self.monto_total}>"
