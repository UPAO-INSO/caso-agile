import os
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail

# Carga las variables de entorno desde el archivo .env
load_dotenv() 

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    # Inicializa la aplicación Flask
    app = Flask(__name__)

    # 1. Configurar la aplicación
    # Lee la URL de la base de datos desde la variable de entorno
    database_url = os.environ.get('DATABASE_URL')
    
    # Configura la URI de la base de datos para SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    # Desactiva una función de seguimiento de SQLAlchemy que no necesitamos
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializa la extensión SQLAlchemy con la aplicación
    # db.init_app(app)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Importar modelos aquí (para que Migrate los detecte)
    from . import models  
    
    # Registra blueprints (Si existen)
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    app = Flask(__name__)

    # Configuración de Gmail
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'vbrunelliw1@upao.edu.pe'
    app.config['MAIL_PASSWORD'] = 'ierw pvxc kybo qrpe'
    app.config['MAIL_DEFAULT_SENDER'] = 'vbrunelliw1@upao.edu.pe'

    mail = Mail(app)

    return app