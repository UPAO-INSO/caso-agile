# app/__init__.py

import os
import importlib
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail  # Asegúrate de importar la clase Mail

# Carga las variables de entorno desde el archivo .env
load_dotenv() 

db = SQLAlchemy()
migrate = Migrate()
mail = Mail() # <--- PASO CLAVE 1: Declarar la extensión a nivel global
# ---------------------------------------------

def create_app():
    # Inicializa la aplicación Flask
    app = Flask(__name__)

    # 1. Configurar la aplicación (mantenemos esto)
    # ... código de configuración de DATABASE_URL ...
    database_url = os.environ.get('DATABASE_URL')

    # DATABASE_URL es obligatorio en esta app (Option A)
    if not database_url:
        raise RuntimeError('DATABASE_URL environment variable is required')

    # Configura la URI de la base de datos para SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configuración de Gmail (mantenemos esto)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'vbrunelliw1@upao.edu.pe'
    app.config['MAIL_PASSWORD'] = 'ierw pvxc kybo qrpe'
    app.config['MAIL_DEFAULT_SENDER'] = 'vbrunelliw1@upao.edu.pe'

    # 2. Inicializar las extensiones (usando el objeto global)
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app) # <--- PASO CLAVE 2: Inicializar el objeto global 'mail'
    
    # Importar modelos por módulo para que Flask-Migrate los detecte
    # y registrar los módulos/blueprints de forma dinámica.
    MODULES = ['clients', 'prestamos', 'declaraciones', 'cuotas']

    for mod_name in MODULES:
        try:
            importlib.import_module(f'.{mod_name}.model.{mod_name}', package=__name__)
        except Exception as e:
            # Registrar la excepción para depuración; no silenciamos.
            app.logger.warning("No se pudo importar modelo %s: %s", mod_name, e)

    # Registra blueprint principal
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Registrar módulos por dominio llamando a su init_app si existe
    for mod_name in MODULES:
        try:
            pkg = importlib.import_module(f'.{mod_name}', package=__name__)
            init_fn = getattr(pkg, 'init_app', None)
            if callable(init_fn):
                init_fn(app)
        except Exception as e:
            app.logger.warning("No se pudo inicializar el módulo %s: %s", mod_name, e)

    return app