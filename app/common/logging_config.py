"""
Logging Module
Sistema de logging estructurado con diferentes niveles y handlers.
Proporciona logging a archivos, consola y servicios externos (opcional).
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional
from flask import Flask, request, has_request_context


def configure_logging(app: Flask):
    """
    Configura el sistema de logging de la aplicación.
    
    Args:
        app: Instancia de Flask
    """
    # Obtener configuración
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    log_dir = app.config.get('LOG_DIR', 'logs')
    log_file = app.config.get('LOG_FILE', 'app.log')
    max_bytes = app.config.get('LOG_MAX_BYTES', 10 * 1024 * 1024)  # 10MB
    backup_count = app.config.get('LOG_BACKUP_COUNT', 5)
    
    # Crear directorio de logs si no existe
    os.makedirs(log_dir, exist_ok=True)
    
    # Limpiar handlers existentes
    app.logger.handlers.clear()
    
    # Configurar nivel de log
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    app.logger.setLevel(log_level_value)
    
    # Formato de logs
    formatter = CustomFormatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s | %(request_info)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level_value)
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)
    
    # Handler para archivo (rotating)
    file_path = os.path.join(log_dir, log_file)
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level_value)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    
    # Handler para errores (archivo separado)
    error_file_path = os.path.join(log_dir, 'error.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    app.logger.addHandler(error_handler)
    
    # Registrar request logging
    register_request_logging(app)
    
    app.logger.info('Sistema de logging configurado correctamente')
    app.logger.info(f'Nivel de log: {log_level}')
    app.logger.info(f'Directorio de logs: {log_dir}')


class CustomFormatter(logging.Formatter):
    """
    Formatter personalizado que agrega información del request.
    """
    
    def format(self, record):
        """Formatea el record agregando información del request"""
        # Agregar información del request si existe
        if has_request_context():
            record.request_info = f'[{request.method} {request.path}] [IP: {request.remote_addr}]'
        else:
            record.request_info = '[No Request Context]'
        
        return super().format(record)


def register_request_logging(app: Flask):
    """
    Registra logging automático de requests y responses.
    
    Args:
        app: Instancia de Flask
    """
    
    @app.before_request
    def log_request():
        """Log cada request entrante"""
        if not app.config.get('LOG_REQUESTS', True):
            return
        
        # Ignorar rutas estáticas
        if request.path.startswith('/static/'):
            return
        
        app.logger.info(
            f'Request: {request.method} {request.path} | '
            f'IP: {request.remote_addr} | '
            f'User-Agent: {request.user_agent.string[:50] if request.user_agent else "Unknown"}'
        )
        
        # Log de query params (solo en debug)
        if app.debug and request.args:
            app.logger.debug(f'Query params: {dict(request.args)}')
        
        # Log de body (solo en debug y POST/PUT/PATCH)
        if app.debug and request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                app.logger.debug(f'JSON body: {request.get_json()}')
    
    @app.after_request
    def log_response(response):
        """Log cada response saliente"""
        if not app.config.get('LOG_RESPONSES', True):
            return response
        
        # Ignorar rutas estáticas
        if request.path.startswith('/static/'):
            return response
        
        app.logger.info(
            f'Response: {response.status_code} | '
            f'{request.method} {request.path} | '
            f'Size: {response.content_length or 0} bytes'
        )
        
        return response
    
    app.logger.info('Request/Response logging configurado')


class Logger:
    """
    Helper class para logging estructurado.
    Proporciona métodos convenientes para logging con contexto.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def debug(self, message: str, **context):
        """Log a nivel DEBUG con contexto adicional"""
        self._log(logging.DEBUG, message, context)
    
    def info(self, message: str, **context):
        """Log a nivel INFO con contexto adicional"""
        self._log(logging.INFO, message, context)
    
    def warning(self, message: str, **context):
        """Log a nivel WARNING con contexto adicional"""
        self._log(logging.WARNING, message, context)
    
    def error(self, message: str, **context):
        """Log a nivel ERROR con contexto adicional"""
        self._log(logging.ERROR, message, context)
    
    def critical(self, message: str, **context):
        """Log a nivel CRITICAL con contexto adicional"""
        self._log(logging.CRITICAL, message, context)
    
    def _log(self, level: int, message: str, context: dict):
        """Log interno con formato estructurado"""
        if context:
            context_str = ' | '.join([f'{k}={v}' for k, v in context.items()])
            message = f'{message} | {context_str}'
        
        self.logger.log(level, message)
    
    # Métodos específicos de dominio
    
    def log_user_action(self, user_id: str, action: str, details: Optional[str] = None):
        """Log de acciones de usuario"""
        self.info(
            f'User action: {action}',
            user_id=user_id,
            details=details or 'N/A'
        )
    
    def log_database_operation(self, operation: str, table: str, record_id: Optional[str] = None):
        """Log de operaciones de base de datos"""
        self.debug(
            f'DB operation: {operation}',
            table=table,
            record_id=record_id or 'N/A'
        )
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """Log de llamadas a API"""
        self.info(
            f'API call: {method} {endpoint}',
            status=status_code,
            duration_ms=f'{duration_ms:.2f}'
        )
    
    def log_external_service(self, service: str, operation: str, success: bool, duration_ms: Optional[float] = None):
        """Log de llamadas a servicios externos"""
        level = logging.INFO if success else logging.WARNING
        message = f'External service: {service} | {operation}'
        
        context = {'success': success}
        if duration_ms:
            context['duration_ms'] = f'{duration_ms:.2f}'
        
        self._log(level, message, context)
    
    def log_security_event(self, event_type: str, severity: str, details: str):
        """Log de eventos de seguridad"""
        level = logging.WARNING if severity in ['medium', 'high'] else logging.INFO
        
        self._log(
            level,
            f'Security event: {event_type}',
            {'severity': severity, 'details': details}
        )


import time
from functools import wraps

def log_performance(func):
    """
    Decorator para medir y loggear el tiempo de ejecución de funciones.
    
    Uso:
        @log_performance
        def slow_function():
            # código que tarda mucho
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log si tarda más de 100ms
            if duration_ms > 100:
                logging.getLogger(func.__module__).warning(
                    f'Slow function: {func.__name__} took {duration_ms:.2f}ms'
                )
            else:
                logging.getLogger(func.__module__).debug(
                    f'Function: {func.__name__} took {duration_ms:.2f}ms'
                )
            
            return result
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logging.getLogger(func.__module__).error(
                f'Function {func.__name__} failed after {duration_ms:.2f}ms: {str(e)}'
            )
            raise
    
    return wrapper


__all__ = [
    'configure_logging',
    'CustomFormatter',
    'register_request_logging',
    'Logger',
    'log_performance'
]
