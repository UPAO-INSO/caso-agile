# app/__init__.py

import os
import importlib
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
<<<<<<< HEAD
from flask_mail import Mail
=======
from flask_mail import Mail  # Asegúrate de importar la clase Mail
>>>>>>> 58fe15451625b48ca47ccabe24faa44aa13dd7ee

load_dotenv() 

db = SQLAlchemy()
migrate = Migrate()
<<<<<<< HEAD
mail = Mail() 
=======
mail = Mail() # <--- PASO CLAVE 1: Declarar la extensión a nivel global
# ---------------------------------------------
>>>>>>> 58fe15451625b48ca47ccabe24faa44aa13dd7ee

def create_app():
    app = Flask(__name__)

<<<<<<< HEAD
    database_url = os.environ.get('DATABASE_URL')
    mail_server = os.environ.get('MAIL_SERVER')
    mail_port = os.environ.get('MAIL_PORT')
    mail_use_tls = os.environ.get('MAIL_USE_TLS')
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    mail_default_sender = os.environ.get('MAIL_DEFAULT_SENDER')

    if not database_url:
        raise RuntimeError('DATABASE_URL environment variable is required')

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['MAIL_SERVER'] = mail_server
    app.config['MAIL_PORT'] = mail_port
    app.config['MAIL_USE_TLS'] = mail_use_tls
    app.config['MAIL_USERNAME'] = mail_username
    app.config['MAIL_PASSWORD'] = mail_password
    app.config['MAIL_DEFAULT_SENDER'] = mail_default_sender

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    MODULES = ['clients', 'prestamos', 'declaraciones', 'cuotas']

    for mod_name in MODULES:
        try:
            importlib.import_module(f'.{mod_name}.model.{mod_name}', package=__name__)
        except Exception as e:
            app.logger.warning("No se pudo importar modelo %s: %s", mod_name, e)

=======
    # 1. Configurar la aplicación (mantenemos esto)
    # ... código de configuración de DATABASE_URL ...
    database_url = os.environ.get('DATABASE_URL')
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
    
    # Importar modelos aquí (para que Migrate los detecte)
    from . import models  
    
    # 3. Registrar blueprints
    # Esto ahora funciona, porque 'mail' ya existe como objeto global
>>>>>>> 58fe15451625b48ca47ccabe24faa44aa13dd7ee
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    for mod_name in MODULES:
        try:
            pkg = importlib.import_module(f'.{mod_name}', package=__name__)
            init_fn = getattr(pkg, 'init_app', None)
            if callable(init_fn):
                init_fn(app)
        except Exception as e:
            app.logger.warning("No se pudo inicializar el módulo %s: %s", mod_name, e)

    return app