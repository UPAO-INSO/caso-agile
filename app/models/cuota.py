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
    es_cuota_ajuste = db.Column(db.Boolean, default=False, nullable=False)
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
        ajuste_text = " (AJUSTE)" if self.es_cuota_ajuste else ""
        return f"<Cuota {self.numero_cuota} de Prestamo ID {self.prestamo_id}{ajuste_text}>"
    
    def to_dict(self):
        """Convierte el modelo a diccionario para serialización"""
        return {
            'cuota_id': self.cuota_id,
            'numero_cuota': self.numero_cuota,
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            'monto_cuota': float(self.monto_cuota) if self.monto_cuota else 0,
            'monto_capital': float(self.monto_capital) if self.monto_capital else 0,
            'monto_interes': float(self.monto_interes) if self.monto_interes else 0,
            'saldo_capital': float(self.saldo_capital) if self.saldo_capital else 0,
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'monto_pagado': float(self.monto_pagado) if self.monto_pagado else 0,
            'es_cuota_ajuste': self.es_cuota_ajuste,
            'prestamo_id': self.prestamo_id
        }
