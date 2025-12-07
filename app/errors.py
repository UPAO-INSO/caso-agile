"""
Error Handling Module
Manejo centralizado de errores HTTP y excepciones de la aplicación.
Proporciona respuestas consistentes en JSON (API) y HTML (Views).
"""

import logging
import traceback
from functools import wraps
from typing import Tuple, Dict, Any, Optional
from flask import jsonify, render_template, request, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError


class AppException(Exception):
    """Excepción base de la aplicación"""
    
    def __init__(self, message: str, status_code: int = 500, payload: Optional[Dict] = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir excepción a diccionario para respuesta JSON"""
        rv = dict(self.payload)
        rv['error'] = self.message
        rv['status_code'] = self.status_code
        return rv


class ValidationError(AppException):
    """Error de validación de datos"""
    
    def __init__(self, message: str = "Error de validación", payload: Optional[Dict] = None):
        super().__init__(message, status_code=400, payload=payload)


class NotFoundError(AppException):
    """Recurso no encontrado"""
    
    def __init__(self, message: str = "Recurso no encontrado", payload: Optional[Dict] = None):
        super().__init__(message, status_code=404, payload=payload)


class UnauthorizedError(AppException):
    """Usuario no autorizado"""
    
    def __init__(self, message: str = "No autorizado", payload: Optional[Dict] = None):
        super().__init__(message, status_code=401, payload=payload)


class ForbiddenError(AppException):
    """Acceso prohibido"""
    
    def __init__(self, message: str = "Acceso prohibido", payload: Optional[Dict] = None):
        super().__init__(message, status_code=403, payload=payload)


class ConflictError(AppException):
    """Conflicto con el estado actual del recurso"""
    
    def __init__(self, message: str = "Conflicto", payload: Optional[Dict] = None):
        super().__init__(message, status_code=409, payload=payload)


class RateLimitError(AppException):
    """Límite de rate exceeded"""
    
    def __init__(self, message: str = "Demasiadas peticiones", payload: Optional[Dict] = None):
        super().__init__(message, status_code=429, payload=payload)


class ServiceUnavailableError(AppException):
    """Servicio no disponible"""
    
    def __init__(self, message: str = "Servicio no disponible", payload: Optional[Dict] = None):
        super().__init__(message, status_code=503, payload=payload)


def register_error_handlers(app):
    """
    Registra todos los manejadores de errores en la aplicación.
    
    Args:
        app: Instancia de Flask
    """
    
    # Custom exceptions
    app.register_error_handler(AppException, handle_app_exception)
    app.register_error_handler(ValidationError, handle_app_exception)
    app.register_error_handler(NotFoundError, handle_app_exception)
    app.register_error_handler(UnauthorizedError, handle_app_exception)
    app.register_error_handler(ForbiddenError, handle_app_exception)
    app.register_error_handler(ConflictError, handle_app_exception)
    app.register_error_handler(RateLimitError, handle_app_exception)
    app.register_error_handler(ServiceUnavailableError, handle_app_exception)
    
    # HTTP exceptions
    app.register_error_handler(400, handle_http_error)
    app.register_error_handler(401, handle_http_error)
    app.register_error_handler(403, handle_http_error)
    app.register_error_handler(404, handle_http_error)
    app.register_error_handler(405, handle_http_error)
    app.register_error_handler(409, handle_http_error)
    app.register_error_handler(429, handle_http_error)
    app.register_error_handler(500, handle_http_error)
    app.register_error_handler(502, handle_http_error)
    app.register_error_handler(503, handle_http_error)
    
    # Database exceptions
    app.register_error_handler(SQLAlchemyError, handle_database_error)
    app.register_error_handler(IntegrityError, handle_integrity_error)
    app.register_error_handler(OperationalError, handle_operational_error)
    
    # Generic exception
    app.register_error_handler(Exception, handle_generic_exception)
    
    app.logger.info('Error handlers registrados correctamente')


def handle_app_exception(error: AppException):
    """
    Maneja excepciones personalizadas de la aplicación.
    
    Args:
        error: Instancia de AppException
    
    Returns:
        Respuesta JSON o HTML según el tipo de petición
    """
    log_error(error, level='warning')
    
    if is_api_request():
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    return render_template(
        'errors/error.html',
        error_code=error.status_code,
        error_message=error.message
    ), error.status_code


def handle_http_error(error: HTTPException):
    """
    Maneja errores HTTP estándar (4xx, 5xx).
    
    Args:
        error: Instancia de HTTPException de Werkzeug
    
    Returns:
        Respuesta JSON o HTML según el tipo de petición
    """
    status_code = error.code or 500
    
    # Log según severidad
    if status_code >= 500:
        log_error(error, level='error')
    else:
        log_error(error, level='warning')
    
    if is_api_request():
        return jsonify({
            'error': error.description or get_error_message(status_code),
            'status_code': status_code
        }), status_code
    
    return render_template(
        f'errors/{status_code}.html',
        error_code=status_code,
        error_message=error.description or get_error_message(status_code)
    ), status_code


def handle_database_error(error: SQLAlchemyError):
    """
    Maneja errores generales de base de datos.
    
    Args:
        error: Instancia de SQLAlchemyError
    
    Returns:
        Respuesta JSON o HTML con error 500
    """
    log_error(error, level='error', include_trace=True)
    
    message = 'Error de base de datos'
    
    if current_app.config.get('DEBUG'):
        message = f'{message}: {str(error)}'
    
    if is_api_request():
        return jsonify({
            'error': message,
            'status_code': 500
        }), 500
    
    return render_template(
        'errors/500.html',
        error_code=500,
        error_message=message
    ), 500


def handle_integrity_error(error: IntegrityError):
    """
    Maneja errores de integridad de base de datos (constraints, duplicados).
    
    Args:
        error: Instancia de IntegrityError
    
    Returns:
        Respuesta JSON o HTML con error 409
    """
    log_error(error, level='warning')
    
    # Extraer mensaje más amigable
    message = 'Conflicto con datos existentes'
    
    if 'UNIQUE constraint failed' in str(error):
        message = 'El registro ya existe'
    elif 'FOREIGN KEY constraint failed' in str(error):
        message = 'Referencia a registro inexistente'
    elif 'NOT NULL constraint failed' in str(error):
        message = 'Campos requeridos faltantes'
    
    if current_app.config.get('DEBUG'):
        message = f'{message}: {str(error)}'
    
    if is_api_request():
        return jsonify({
            'error': message,
            'status_code': 409
        }), 409
    
    return render_template(
        'errors/409.html',
        error_code=409,
        error_message=message
    ), 409


def handle_operational_error(error: OperationalError):
    """
    Maneja errores operacionales de base de datos (conexión, timeout).
    
    Args:
        error: Instancia de OperationalError
    
    Returns:
        Respuesta JSON o HTML con error 503
    """
    log_error(error, level='error', include_trace=True)
    
    message = 'Base de datos no disponible'
    
    if current_app.config.get('DEBUG'):
        message = f'{message}: {str(error)}'
    
    if is_api_request():
        return jsonify({
            'error': message,
            'status_code': 503
        }), 503
    
    return render_template(
        'errors/503.html',
        error_code=503,
        error_message=message
    ), 503


def handle_generic_exception(error: Exception):
    """
    Maneja cualquier excepción no capturada.
    
    Args:
        error: Instancia de Exception
    
    Returns:
        Respuesta JSON o HTML con error 500
    """
    log_error(error, level='critical', include_trace=True)
    
    message = 'Error interno del servidor'
    
    if current_app.config.get('DEBUG'):
        message = f'{message}: {str(error)}'
    
    if is_api_request():
        return jsonify({
            'error': message,
            'status_code': 500
        }), 500
    
    return render_template(
        'errors/500.html',
        error_code=500,
        error_message=message
    ), 500


def handle_errors(func):
    """
    Decorator para manejar errores en endpoints.
    Captura excepciones y retorna respuestas apropiadas.
    
    Uso:
        @app.route('/endpoint')
        @handle_errors
        def endpoint():
            # código que puede lanzar excepciones
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppException as e:
            # Ya están manejadas por handle_app_exception
            raise
        except HTTPException as e:
            # Ya están manejadas por handle_http_error
            raise
        except SQLAlchemyError as e:
            # Ya están manejadas por handle_database_error
            raise
        except Exception as e:
            # Log y convertir a error genérico
            log_error(e, level='error', include_trace=True)
            
            if is_api_request():
                return jsonify({
                    'error': 'Error interno del servidor',
                    'status_code': 500
                }), 500
            
            return render_template(
                'errors/500.html',
                error_code=500,
                error_message='Error interno del servidor'
            ), 500
    
    return wrapper


def is_api_request() -> bool:
    """
    Detecta si la petición es para API (debe retornar JSON).
    
    Returns:
        True si es petición API, False si es petición de View (HTML)
    """
    # Verificar si la ruta comienza con /api/
    if request.path.startswith('/api/'):
        return True
    
    # Verificar si el cliente acepta JSON
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > request.accept_mimetypes['text/html']


def get_error_message(status_code: int) -> str:
    """
    Obtiene mensaje de error amigable por código HTTP.
    
    Args:
        status_code: Código de estado HTTP
    
    Returns:
        Mensaje de error descriptivo
    """
    messages = {
        400: 'Solicitud inválida',
        401: 'No autorizado',
        403: 'Acceso prohibido',
        404: 'Página no encontrada',
        405: 'Método no permitido',
        409: 'Conflicto con el estado actual',
        429: 'Demasiadas peticiones',
        500: 'Error interno del servidor',
        502: 'Gateway inválido',
        503: 'Servicio no disponible'
    }
    return messages.get(status_code, f'Error {status_code}')


def log_error(error: Exception, level: str = 'error', include_trace: bool = False):
    """
    Registra un error en los logs con información contextual.
    
    Args:
        error: Excepción a registrar
        level: Nivel de log ('debug', 'info', 'warning', 'error', 'critical')
        include_trace: Si se debe incluir el stack trace
    """
    logger = current_app.logger
    
    # Información del request
    context = {
        'method': request.method,
        'path': request.path,
        'ip': request.remote_addr,
        'user_agent': request.user_agent.string if request.user_agent else 'Unknown'
    }
    
    # Mensaje base
    error_type = type(error).__name__
    error_msg = str(error)
    
    log_message = f'{error_type}: {error_msg} | Context: {context}'
    
    # Log según nivel
    log_func = getattr(logger, level, logger.error)
    log_func(log_message)
    
    # Stack trace si se solicita
    if include_trace:
        trace = traceback.format_exc()
        logger.error(f'Stack trace:\n{trace}')


__all__ = [
    # Exceptions
    'AppException',
    'ValidationError',
    'NotFoundError',
    'UnauthorizedError',
    'ForbiddenError',
    'ConflictError',
    'RateLimitError',
    'ServiceUnavailableError',
    
    # Handlers
    'register_error_handlers',
    'handle_app_exception',
    'handle_http_error',
    'handle_database_error',
    'handle_integrity_error',
    'handle_operational_error',
    'handle_generic_exception',
    
    # Decorators
    'handle_errors',
    
    # Helpers
    'is_api_request',
    'get_error_message',
    'log_error'
]
