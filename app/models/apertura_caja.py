from datetime import datetime
from app.common.extensions import db


class AperturaCaja(db.Model):
    __tablename__ = 'aperturas_caja'

    apertura_id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    usuario_id = db.Column(db.Integer, nullable=True)
    fecha_registro = db.Column(db.DateTime, server_default=db.text('now()'), nullable=False)

    def to_dict(self):
        return {
            'apertura_id': self.apertura_id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'monto': float(self.monto),
            'usuario_id': self.usuario_id,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
        }

    def __repr__(self):
        return f"<AperturaCaja {self.apertura_id} Fecha {self.fecha} Monto {self.monto}>"
