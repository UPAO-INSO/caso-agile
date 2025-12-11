from datetime import datetime
from app.common.extensions import db


class Egreso(db.Model):
    __tablename__ = 'egresos'

    egreso_id = db.Column(db.Integer, primary_key=True)
    pago_id = db.Column(db.Integer, db.ForeignKey('pagos.pago_id'), nullable=True)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    concepto = db.Column(db.String(255), nullable=False)
    usuario_id = db.Column(db.Integer, nullable=True)
    fecha_registro = db.Column(db.DateTime, server_default=db.text('now()'), nullable=False)

    def to_dict(self):
        return {
            'egreso_id': self.egreso_id,
            'pago_id': self.pago_id,
            'monto': float(self.monto),
            'concepto': self.concepto,
            'usuario_id': self.usuario_id,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
        }

    def __repr__(self):
        return f"<Egreso ID {self.egreso_id} - S/ {self.monto} ({self.concepto})>"
