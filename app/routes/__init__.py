"""
Routes Package
Centraliza todas las rutas de la aplicación (API, vistas y endpoints)
"""
from flask import Blueprint

# Blueprint principal
main_bp = Blueprint('main', __name__)

# Blueprint de autenticación
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Blueprints de API REST
api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Blueprints de vistas HTML
clientes_view_bp = Blueprint('clientes_view', __name__)
prestamos_view_bp = Blueprint('prestamos_view', __name__)

# Blueprints de módulos
clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')
prestamos_bp = Blueprint('prestamos', __name__, url_prefix='/prestamos')
cuotas_bp = Blueprint('cuotas', __name__, url_prefix='/cuotas')
declaraciones_bp = Blueprint('declaraciones', __name__, url_prefix='/declaraciones')
pagos_bp = Blueprint('pagos', __name__, url_prefix='/pagos')
caja_bp = Blueprint('caja', __name__, url_prefix='/caja')

# Importar rutas para registrar con los blueprints
from app.routes import main_routes, auth_routes
from app.routes import api_cliente, api_prestamo, financial_routes
from app.routes import cliente_views, prestamo_views
from app.routes import cliente_routes, prestamo_routes, cuota_routes, declaracion_routes, pago_routes, caja_routes

__all__ = [
    'main_bp',
    'auth_bp',
    'api_v1_bp',
    'clientes_view_bp',
    'prestamos_view_bp',
    'clientes_bp',
    'prestamos_bp',
    'cuotas_bp',
    'declaraciones_bp',
    'pagos_bp',
    'caja_bp'
]
