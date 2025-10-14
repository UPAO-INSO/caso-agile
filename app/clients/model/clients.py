from sqlalchemy.orm import relationship
from ... import db


class Cliente(db.Model):
    __tablename__ = 'clientes'

    cliente_id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(8), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(200), nullable=False)
    apellido_paterno = db.Column(db.String(100), nullable=False)
    apellido_materno = db.Column(db.String(100))
    pep = db.Column(db.Boolean, default=False, nullable=False)
    fecha_registro = db.Column(db.DateTime, server_default=db.func.now())

    # Relaciones Lógicas (para Python)
    prestamos = relationship("Prestamo", back_populates="cliente")
    declaraciones_juradas = relationship("DeclaracionJurada", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente: DNI:{self.dni} - NOMBRES:{self.nombre_completo} - PEP:{self.pep}>"
