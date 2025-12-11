from sqlalchemy.orm import relationship
from app.common.extensions import db
import enum


class TipoDeclaracionEnum(enum.Enum):
    USO_PROPIO = 'USO_PROPIO'
    PEP = 'PEP'
    AMBOS = 'AMBOS'


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
    prestamo = relationship("Prestamo", back_populates="declaracion_jurada", uselist=False)

    def __repr__(self):
        return f"<DeclaracionJurada ID {self.declaracion_id} para Cliente ID {self.cliente_id}>"
