from sqlalchemy.orm import relationship
from app.common.extensions import db
from datetime import date
from decimal import Decimal


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
    monto_pagado = db.Column(db.Numeric(12, 2), nullable=True, default=0)
    
    # Campos de mora
    mora_generada = db.Column(db.Numeric(12, 2), nullable=False, default=0)  # Mora histórica total generada
    mora_acumulada = db.Column(db.Numeric(12, 2), nullable=False, default=0)  # Mora pendiente de pago
    saldo_pendiente = db.Column(db.Numeric(12, 2), nullable=False)  # Saldo de la cuota pendiente
    
    prestamo_id = db.Column(db.Integer, db.ForeignKey('prestamos.prestamo_id'), nullable=False)

    # Relaciones Lógicas
    prestamo = relationship("Prestamo", back_populates="cuotas")
    pagos = relationship("Pago", back_populates="cuota", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint('prestamo_id', 'numero_cuota', name='uq_prestamo_numero_cuota'),
        db.CheckConstraint('numero_cuota > 0', name='chk_numero_cuota_positivo'),
        db.CheckConstraint('monto_cuota > 0', name='chk_monto_cuota_positivo'),
    )

    def __repr__(self):
        return f"<Cuota {self.numero_cuota} de Prestamo ID {self.prestamo_id}>"

    def to_dict(self):
        return {
            'cuota_id': self.cuota_id,
            'numero_cuota': self.numero_cuota,
            'fecha_vencimiento': self.fecha_vencimiento.isoformat(),
            'monto_cuota': float(self.monto_cuota),
            'monto_capital': float(self.monto_capital),
            'monto_interes': float(self.monto_interes),
            'saldo_capital': float(self.saldo_capital),
            'saldo_pendiente': float(self.saldo_pendiente),
            'mora_generada': float(self.mora_generada),
            'mora_acumulada': float(self.mora_acumulada),
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'monto_pagado': float(self.monto_pagado) if self.monto_pagado else 0
        }