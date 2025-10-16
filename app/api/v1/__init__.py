"""
API v1
Primera versión de la API REST
"""
from flask import Blueprint

api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Importar rutas después de crear el blueprint para evitar circular imports
from . import clientes, prestamos

__all__ = ['api_v1_bp']
