"""
Application Factory
Crea y configura la aplicación Flask usando el patrón Factory.
Permite crear múltiples instancias con diferentes configuraciones (dev, prod, test).
"""

import os
import importlib
from flask import Flask
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Importar extensiones centralizadas
from app.extensions import db, migrate, mail
from app.config import get_config

# Módulos que se registrarán automáticamente
MODULES = ['clients', 'prestamos', 'declaraciones', 'cuotas']


def create_app(config_name=None):
    """
    Application Factory para crear instancia de Flask.
    
    Args:
        config_name: Nombre del ambiente ('development', 'production', 'testing')
                    Si es None, usa FLASK_ENV de variables de entorno
    
    Returns:
        Instancia de Flask configurada y lista para usar
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # Cargar configuración desde config.py
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Cargar configuración sensible desde instance/config.py (si existe)
    try:
        app.config.from_pyfile('config.py', silent=True)
    except Exception as e:
        app.logger.debug(f'No se pudo cargar instance/config.py: {e}')
    
    # Asegurar que existe el directorio instance/
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError as e:
        app.logger.warning(f'No se pudo crear directorio instance/: {e}')
    
    # Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Registrar modelos de SQLAlchemy (para migrations)
    _register_models(app)
    
    # Registrar blueprints principales
    _register_blueprints(app)
    
    # Registrar módulos dinámicamente
    _register_modules(app)
    
    # Configurar logging
    _configure_logging(app)
    
    # Configurar manejo de errores
    _configure_error_handlers(app)
    
    # Configurar cache y optimización
    _configure_cache(app)
    _configure_performance(app)
    
    # Configurar seguridad
    _configure_security(app)
    
    # Log de inicialización
    app.logger.info(f'Aplicación iniciada en modo: {config_class.__name__}')
    
    return app


def _register_models(app):
    """
    Importa todos los modelos de SQLAlchemy para que Alembic los detecte.
    Esto es necesario para las migraciones automáticas.
    """
    # Importar todos los modelos desde el paquete centralizado
    from app.models import (
        Cliente, 
        Prestamo, 
        Cuota, 
        DeclaracionJurada
    )
    app.logger.info('Modelos registrados correctamente')


def _register_blueprints(app):
    """
    Registra blueprints principales de la aplicación.
    """
    from app.routes import (
        main_bp,
        api_v1_bp,
        clientes_view_bp,
        prestamos_view_bp,
        clientes_bp,
        prestamos_bp,
        cuotas_bp,
        declaraciones_bp
    )
    
    # Registrar blueprint principal
    app.register_blueprint(main_bp)
    
    # Registrar API v1
    app.register_blueprint(api_v1_bp)
    
    # Registrar vistas HTML
    app.register_blueprint(clientes_view_bp)
    app.register_blueprint(prestamos_view_bp)
    
    # Registrar módulos
    app.register_blueprint(clientes_bp)
    app.register_blueprint(prestamos_bp)
    app.register_blueprint(cuotas_bp)
    app.register_blueprint(declaraciones_bp)
    
    app.logger.info('Blueprints registrados correctamente')


def _register_modules(app):
    """
    Función heredada - ya no es necesaria con la nueva estructura.
    Los módulos ahora se registran directamente en _register_blueprints.
    """
    pass

def _configure_security(app):
    """
    Configura las medidas de seguridad de la aplicación.
    - Headers de seguridad
    - CORS (si es necesario)
    - Rate limiting
    """
    from app.security import add_security_headers
    
    # Agregar security headers a todas las respuestas
    @app.after_request
    def apply_security_headers(response):
        return add_security_headers(response)
    
    app.logger.info('Security headers configurados')

def _configure_logging(app):
    """
    Configura el sistema de logging estructurado.
    - Logging a archivo con rotación
    - Logging a consola
    - Logging de requests/responses
    """
    from app.logging_config import configure_logging
    configure_logging(app)
    app.logger.info('Sistema de logging configurado')

def _configure_error_handlers(app):
    """
    Configura el manejo centralizado de errores.
    - Excepciones personalizadas
    - Errores HTTP (4xx, 5xx)
    - Errores de base de datos
    - Páginas de error personalizadas
    """
    from app.errors import register_error_handlers
    register_error_handlers(app)
    app.logger.info('Error handlers configurados')

def _configure_cache(app):
    """
    Configura el sistema de caching.
    - Flask-Caching con múltiples backends (SimpleCache, Redis, FileSystem)
    - Cache para respuestas de API
    - Cache para queries de base de datos
    """
    from app.cache import configure_cache
    configure_cache(app)
    app.logger.info('Sistema de cache configurado')

def _configure_performance(app):
    """
    Configura las herramientas de optimización de rendimiento.
    - Query profiling
    - Compression middleware
    - Performance monitoring
    """
    from app.performance import configure_performance
    configure_performance(app)
    app.logger.info('Performance optimization configurado')
