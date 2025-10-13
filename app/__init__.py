import os
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

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

    return app