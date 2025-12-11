import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

import pytest
from app import create_app, db

@pytest.fixture
def app():
    """Crear aplicación para tests"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Cliente de prueba"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """CLI runner para tests"""
    return app.test_cli_runner()