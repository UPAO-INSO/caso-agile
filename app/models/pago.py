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

class MetodoPagoEnum(enum.Enum):
    """
    MÓDULO 2: Enum para métodos de pago
    - EFECTIVO: REDONDEO aplicado
    - TARJETA: Monto exacto sin redondeo
    - TRANSFERENCIA: Monto exacto sin redondeo
    """
    EFECTIVO = 'EFECTIVO'
    TARJETA = 'TARJETA'
    TRANSFERENCIA = 'TRANSFERENCIA'


class Pago(db.Model):
    __tablename__ = 'pagos'

    pago_id = db.Column(db.Integer, primary_key=True)
    cuota_id = db.Column(db.Integer, db.ForeignKey('cuotas.cuota_id'), nullable=False)
    
    # monto_contable: El monto que debía pagarse (según la cuota)
    monto_contable = db.Column(db.Numeric(12, 2), nullable=True, comment='Deuda contable de la cuota')
    
    # monto_pagado: El monto realmente recibido (redondeado si es efectivo)
    monto_pagado = db.Column(db.Numeric(12, 2), nullable=False, comment='Monto recibido en caja')
    
    # ajuste_redondeo: La diferencia entre contable y pagado (D_perd)
    # Será 0 para pagos digitales, puede ser positivo para efectivo (pérdida por redondeo a favor del cliente)
    ajuste_redondeo = db.Column(
        db.Numeric(12, 2), 
        default=0.00, 
        nullable=False,
        comment='Pérdida/Ganancia por redondeo'
    )
    
    monto_mora = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    hora_pago = db.Column(db.Time, nullable=True, comment='Hora en que se realizó el pago')
    monto_dado = db.Column(db.Numeric(12, 2), nullable=True, comment='Monto entregado por el cliente (billetes)')
    vuelto = db.Column(db.Numeric(12, 2), default=0.00, nullable=False, comment='Vuelto entregado al cliente')
    metodo_pago = db.Column(SQLAlchemyEnum(MetodoPagoEnum), nullable=False, comment='Método de pago: EFECTIVO, TARJETA, TRANSFERENCIA')
    medio_pago = db.Column(SQLAlchemyEnum(MedioPagoEnum), nullable=False)
    comprobante_referencia = db.Column(db.String(100), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    # Relaciones Lógicas
    cuota = relationship("Cuota", back_populates="pagos")

    __table_args__ = (
        db.CheckConstraint('monto_pagado > 0', name='chk_monto_pagado_positivo'),
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
