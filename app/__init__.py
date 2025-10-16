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
    
    # Log de inicialización
    app.logger.info(f'Aplicación iniciada en modo: {config_class.__name__}')
    
    return app


def _register_models(app):
    """
    Importa todos los modelos de SQLAlchemy para que Alembic los detecte.
    Esto es necesario para las migraciones automáticas.
    """
    for mod_name in MODULES:
        try:
            # Intentar importar el modelo del módulo
            importlib.import_module(f'.{mod_name}.model.{mod_name}', package='app')
        except ImportError:
            try:
                # Intentar con estructura alternativa (models.py en lugar de model/modulo.py)
                importlib.import_module(f'.{mod_name}.models', package='app')
            except ImportError as exc:
                app.logger.warning(f'No se pudo importar modelo {mod_name}: {exc}')


def _register_blueprints(app):
    """
    Registra blueprints principales de la aplicación.
    """
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # Registrar API v1
    from app.api.v1 import api_v1_bp
    app.register_blueprint(api_v1_bp)
    
    # Registrar Views
    from app.views import clientes_view_bp, prestamos_view_bp
    app.register_blueprint(clientes_view_bp)
    app.register_blueprint(prestamos_view_bp)


def _register_modules(app):
    """
    Registra módulos dinámicamente llamando a su función init_app() si existe.
    Cada módulo puede tener su propio blueprint que se registra automáticamente.
    """
    for mod_name in MODULES:
        try:
            pkg = importlib.import_module(f'.{mod_name}', package='app')
            init_fn = getattr(pkg, 'init_app', None)
            
            if callable(init_fn):
                init_fn(app)
                app.logger.debug(f'Módulo {mod_name} inicializado correctamente')
        except Exception as exc:
            app.logger.warning(f'No se pudo inicializar el módulo {mod_name}: {exc}')