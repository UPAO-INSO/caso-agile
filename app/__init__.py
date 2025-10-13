import os
from flask import Flask
from dotenv import load_dotenv
from .models import db

# Carga las variables de entorno desde el archivo .env
load_dotenv()

def create_app():
    app = Flask(__name__)

    # 1. Configurar la aplicación
    # Lee la URL de la base de datos desde la variable de entorno
    database_url = os.environ.get('DATABASE_URL')
    
    # Configura la URI de la base de datos para SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    # Desactiva una función de seguimiento de SQLAlchemy que no necesitamos y consume recursos
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    with app.app_context():
        from . import models
    
    return app
