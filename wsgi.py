"""
WSGI Entry Point
Punto de entrada para servidores WSGI (gunicorn, uwsgi, etc.)
"""
from app import create_app

# Crear la aplicación Flask
application = create_app()
app = application

if __name__ == '__main__':
    application.run()
