from sqlalchemy.orm import relationship
from app.common.extensions import db
from datetime import datetime
import enum


class EstadoPagoEnum(enum.Enum):
    PENDIENTE = 'PENDIENTE'
    REALIZADO = 'REALIZADO'
    DEVUELTO = 'DEVUELTO'


class Pago(db.Model):
    __tablename__ = 'pagos'

    pago_id = db.Column(db.Integer, primary_key=True)
    cuota_id = db.Column(db.Integer, db.ForeignKey('cuotas.cuota_id'), nullable=False)
    monto_pagado = db.Column(db.Numeric(12, 2), nullable=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    fecha_registro = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    estado = db.Column(db.Enum(EstadoPagoEnum), default=EstadoPagoEnum.REALIZADO, nullable=False)
    comprobante_referencia = db.Column(db.String(100), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    # Relaciones Lógicas
    cuota = relationship("Cuota", back_populates="pagos")

    __table_args__ = (
        db.CheckConstraint('monto_pagado > 0', name='chk_monto_pagado_positivo'),
        db.UniqueConstraint('cuota_id', 'fecha_pago', name='uq_cuota_fecha_pago'),
    )

    def __repr__(self):
        return f"<Pago ID {self.pago_id} - S/ {self.monto_pagado} el {self.fecha_pago}>"

    def to_dict(self):
        return {
            'pago_id': self.pago_id,
            'cuota_id': self.cuota_id,
            'monto_pagado': float(self.monto_pagado) if self.monto_pagado else 0,
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
            'estado': self.estado.value if self.estado else None,
            'comprobante_referencia': self.comprobante_referencia,
            'observaciones': self.observaciones
        }
