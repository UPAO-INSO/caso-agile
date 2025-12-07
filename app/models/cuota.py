from sqlalchemy.orm import relationship
from app.common.extensions import db


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
