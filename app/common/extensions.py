"""
Extensions Module
Centraliza todas las extensiones de Flask para evitar circular imports
y facilitar la configuración de la aplicación.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail

# Inicializar extensiones sin app (se vinculan en create_app)
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
