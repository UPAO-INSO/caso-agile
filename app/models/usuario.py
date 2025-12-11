from werkzeug.security import generate_password_hash, check_password_hash
from app.common.extensions import db
from datetime import datetime


class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    usuario_id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre_completo = db.Column(db.String(200), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    rol = db.Column(db.String(50), default='usuario', nullable=False)  # 'admin', 'usuario', 'operador'
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now())
    fecha_ultima_conexion = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Genera y almacena el hash de la contraseña"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica si la contraseña coincide con el hash almacenado"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'usuario_id': self.usuario_id,
            'usuario': self.usuario,
            'correo': self.correo,
            'nombre_completo': self.nombre_completo,
            'activo': self.activo,
            'rol': self.rol,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_ultima_conexion': self.fecha_ultima_conexion.isoformat() if self.fecha_ultima_conexion else None
        }
    
    def __repr__(self):
        return f"<Usuario: {self.usuario} - {self.nombre_completo}>"
