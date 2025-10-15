"""
Módulo de Clientes
Gestiona el registro y administración de clientes del sistema
"""
from flask import Blueprint

def init_app(app):
    """
    Inicializa el módulo de clientes registrando el blueprint de rutas
    """
    from .routes import clientes_bp
    app.register_blueprint(clientes_bp)

