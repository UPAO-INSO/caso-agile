from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from app.common.extensions import db
import enum


class MedioPagoEnum(enum.Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA_DEBITO = "TARJETA_DEBITO"
    TARJETA_CREDITO = "TARJETA_CREDITO"
    TRANSFERENCIA = "TRANSFERENCIA"
    BILLETERA_ELECTRONICA = "BILLETERA_ELECTRONICA"
    PAGO_AUTOMATICO = "PAGO_AUTOMATICO"



class Pago(db.Model):
    __tablename__ = 'pagos'

    pago_id = db.Column(db.Integer, primary_key=True)
    cuota_id = db.Column(db.Integer, db.ForeignKey('cuotas.cuota_id'), nullable=False)
    monto_pagado = db.Column(db.Numeric(12, 2), nullable=False)
    monto_mora = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)  # NUEVO
    fecha_pago = db.Column(db.Date, nullable=False)
    medio_pago = db.Column(SQLAlchemyEnum(MedioPagoEnum), nullable=False)
    comprobante_referencia = db.Column(db.String(100), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    # Relaciones Lógicas
    cuota = relationship("Cuota", back_populates="pagos")

    __table_args__ = (
        db.CheckConstraint('monto_pagado > 0', name='chk_monto_pagado_positivo'),
        db.CheckConstraint('monto_mora >= 0', name='chk_monto_mora_no_negativo'),
    )

    def __repr__(self):
        return f"<Pago {self.pago_id} - Cuota {self.cuota_id} - ${self.monto_pagado}>"

    def to_dict(self):
        return {
            'pago_id': self.pago_id,
            'cuota_id': self.cuota_id,
            'monto_pagado': float(self.monto_pagado),
            'monto_mora': float(self.monto_mora),
            'fecha_pago': self.fecha_pago.isoformat(),
            'medio_pago': self.medio_pago.value if self.medio_pago else None,
            'comprobante_referencia': self.comprobante_referencia,
            'observaciones': self.observaciones
        }
