"""
Configuration Module
Define clases de configuración para diferentes ambientes (Development, Production, Testing).
Las variables sensibles deben cargarse desde variables de entorno o instance/config.py
"""

import os
from datetime import timedelta


def _str_to_bool(value):
    """Convierte string a boolean de forma segura"""
    if value is None:
        return False
    return str(value).strip().lower() in {'true', '1', 'yes', 'on'}


class Config:
    """Configuración base compartida por todos los ambientes"""
    
    # Secret Key (REQUERIDO)
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError('SECRET_KEY environment variable is required for session management')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError('DATABASE_URL environment variable is required')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # No mostrar queries SQL por defecto
    
    # Mail Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = _str_to_bool(os.environ.get('MAIL_USE_TLS', 'true'))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True  # Solo en HTTPS (override en dev)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.environ.get('LOG_DIR', 'logs')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', str(10 * 1024 * 1024)))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))
    LOG_REQUESTS = _str_to_bool(os.environ.get('LOG_REQUESTS', 'true'))
    LOG_RESPONSES = _str_to_bool(os.environ.get('LOG_RESPONSES', 'true'))
    
    # API Externa DNI
    DNI_API_KEY = os.environ.get('DNI_API_KEY')
    DNI_API_URL = os.environ.get('DNI_API_URL', 'https://api.apis.net.pe/v2/reniec/dni')


class DevelopmentConfig(Config):
    """Configuración para ambiente de desarrollo"""
    
    DEBUG = True
    TESTING = False
    
    # Permitir cookies sin HTTPS en desarrollo
    SESSION_COOKIE_SECURE = False
    
    # Mostrar queries SQL en desarrollo
    SQLALCHEMY_ECHO = False  # Cambiar a True si necesitas debug SQL
    
    # Mail debug (imprimir en consola en lugar de enviar)
    MAIL_DEBUG = True
    
    # Logging más verboso en desarrollo
    LOG_LEVEL = 'DEBUG'
    LOG_REQUESTS = True
    LOG_RESPONSES = True


class ProductionConfig(Config):
    """Configuración para ambiente de producción"""
    
    DEBUG = False
    TESTING = False
    
    # Forzar HTTPS
    SESSION_COOKIE_SECURE = True
    
    # Logging más estricto
    SQLALCHEMY_ECHO = False
    
    # Mail production
    MAIL_DEBUG = False


class TestingConfig(Config):
    """Configuración para tests automatizados"""
    
    DEBUG = False
    TESTING = True
    
    # Database en memoria para tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Deshabilitar CSRF en tests
    WTF_CSRF_ENABLED = False
    
    # No enviar emails reales en tests
    MAIL_SUPPRESS_SEND = True
    
    # Cookies sin HTTPS en tests
    SESSION_COOKIE_SECURE = False


# Mapeo de nombres a clases de configuración
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Obtiene la clase de configuración apropiada.
    
    Args:
        config_name: Nombre del ambiente ('development', 'production', 'testing')
                    Si es None, usa la variable FLASK_ENV o 'default'
    
    Returns:
        Clase de configuración correspondiente
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, DevelopmentConfig)
