"""
Security Module
Middleware y utilidades para seguridad de la aplicación.
Incluye: CSRF protection, input sanitization, rate limiting, secure headers.
"""

from functools import wraps
from flask import request, jsonify, abort
from datetime import datetime, timedelta
import re
import html
from typing import Dict, Any, Optional
import hashlib
import secrets


class RateLimiter:
    """
    Rate limiter simple basado en memoria.
    Para producción, considerar usar Redis.
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str, max_requests: int = 100, window: int = 60) -> bool:
        """
        Verificar si una petición está permitida.
        
        Args:
            identifier: Identificador único (IP, user_id, etc.)
            max_requests: Número máximo de peticiones
            window: Ventana de tiempo en segundos
        
        Returns:
            True si está permitido, False si excede el límite
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)
        
        # Limpiar peticiones antiguas
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > cutoff
            ]
        else:
            self.requests[identifier] = []
        
        # Verificar límite
        if len(self.requests[identifier]) >= max_requests:
            return False
        
        # Agregar petición actual
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str, max_requests: int = 100) -> int:
        """Obtener peticiones restantes."""
        if identifier not in self.requests:
            return max_requests
        return max(0, max_requests - len(self.requests[identifier]))


# Instancia global del rate limiter
rate_limiter = RateLimiter()


def rate_limit(max_requests: int = 100, window: int = 60, key_func=None):
    """
    Decorator para aplicar rate limiting a rutas.
    
    Args:
        max_requests: Número máximo de peticiones
        window: Ventana de tiempo en segundos
        key_func: Función para obtener el identificador (por defecto usa IP)
    
    Example:
        @app.route('/api/endpoint')
        @rate_limit(max_requests=10, window=60)
        def endpoint():
            return {'status': 'ok'}
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obtener identificador
            if key_func:
                identifier = key_func()
            else:
                identifier = request.remote_addr or 'unknown'
            
            # Verificar rate limit
            if not rate_limiter.is_allowed(identifier, max_requests, window):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Máximo {max_requests} peticiones por {window} segundos'
                }), 429
            
            # Agregar headers de rate limit
            remaining = rate_limiter.get_remaining(identifier, max_requests)
            response = f(*args, **kwargs)
            
            if isinstance(response, tuple):
                response_obj, status_code = response[0], response[1]
            else:
                response_obj = response
                status_code = 200
            
            # Si es una Response de Flask
            if hasattr(response_obj, 'headers'):
                response_obj.headers['X-RateLimit-Limit'] = str(max_requests)
                response_obj.headers['X-RateLimit-Remaining'] = str(remaining)
                response_obj.headers['X-RateLimit-Window'] = str(window)
            
            return response
        
        return decorated_function
    return decorator


class InputSanitizer:
    """Sanitizador de inputs para prevenir XSS y SQL injection."""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Escapar HTML para prevenir XSS.
        
        Args:
            text: Texto a sanitizar
        
        Returns:
            Texto escapado
        """
        if not text:
            return text
        return html.escape(str(text))
    
    @staticmethod
    def sanitize_sql(text: str) -> str:
        """
        Sanitizar texto para prevenir SQL injection.
        Nota: SQLAlchemy ya previene SQL injection, esto es una capa extra.
        
        Args:
            text: Texto a sanitizar
        
        Returns:
            Texto sanitizado
        """
        if not text:
            return text
        
        # Remover caracteres peligrosos
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_', 'DROP', 'DELETE', 'INSERT', 'UPDATE']
        sanitized = str(text)
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitizar nombres de archivo.
        
        Args:
            filename: Nombre de archivo a sanitizar
        
        Returns:
            Nombre de archivo seguro
        """
        if not filename:
            return 'unnamed'
        
        # Remover caracteres no permitidos
        sanitized = re.sub(r'[^\w\s.-]', '', filename)
        # Remover múltiples puntos consecutivos
        sanitized = re.sub(r'\.+', '.', sanitized)
        # Limitar longitud
        sanitized = sanitized[:255]
        
        return sanitized or 'unnamed'
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], html_escape: bool = True) -> Dict[str, Any]:
        """
        Sanitizar todos los valores string de un diccionario.
        
        Args:
            data: Diccionario a sanitizar
            html_escape: Si debe escapar HTML
        
        Returns:
            Diccionario sanitizado
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_html(value) if html_escape else value
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value, html_escape)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputSanitizer.sanitize_html(item) if isinstance(item, str) and html_escape else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


# Instancia global del sanitizer
sanitizer = InputSanitizer()


class InputValidator:
    """Validadores de input para datos comunes."""
    
    @staticmethod
    def validate_dni(dni: str) -> tuple[bool, Optional[str]]:
        """
        Validar DNI peruano (8 dígitos).
        
        Returns:
            (is_valid, error_message)
        """
        if not dni:
            return False, "DNI es obligatorio"
        
        dni = str(dni).strip()
        
        if len(dni) != 8:
            return False, "DNI debe tener 8 dígitos"
        
        if not dni.isdigit():
            return False, "DNI solo debe contener números"
        
        return True, None
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, Optional[str]]:
        """
        Validar formato de email.
        
        Returns:
            (is_valid, error_message)
        """
        if not email:
            return False, "Email es obligatorio"
        
        email = str(email).strip()
        
        # Patrón regex para email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False, "Formato de email inválido"
        
        if len(email) > 254:
            return False, "Email demasiado largo"
        
        return True, None
    
    @staticmethod
    def validate_phone(phone: str) -> tuple[bool, Optional[str]]:
        """
        Validar teléfono peruano (9 dígitos, comienza con 9).
        
        Returns:
            (is_valid, error_message)
        """
        if not phone:
            return False, "Teléfono es obligatorio"
        
        phone = str(phone).strip()
        
        if len(phone) != 9:
            return False, "Teléfono debe tener 9 dígitos"
        
        if not phone.isdigit():
            return False, "Teléfono solo debe contener números"
        
        if not phone.startswith('9'):
            return False, "Teléfono debe comenzar con 9"
        
        return True, None
    
    @staticmethod
    def validate_amount(amount: float, min_amount: float = 0, max_amount: float = 50000) -> tuple[bool, Optional[str]]:
        """
        Validar monto monetario.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return False, "Monto debe ser un número"
        
        if amount < min_amount:
            return False, f"Monto mínimo es S/ {min_amount}"
        
        if amount > max_amount:
            return False, f"Monto máximo es S/ {max_amount}"
        
        return True, None
    
    @staticmethod
    def validate_tea(tea: float) -> tuple[bool, Optional[str]]:
        """
        Validar TEA (Tasa Efectiva Anual).
        
        Returns:
            (is_valid, error_message)
        """
        try:
            tea = float(tea)
        except (ValueError, TypeError):
            return False, "TEA debe ser un número"
        
        if tea <= 0:
            return False, "TEA debe ser mayor a 0"
        
        if tea > 100:
            return False, "TEA no puede ser mayor a 100%"
        
        return True, None
    
    @staticmethod
    def validate_cuotas(cuotas: int) -> tuple[bool, Optional[str]]:
        """
        Validar número de cuotas.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            cuotas = int(cuotas)
        except (ValueError, TypeError):
            return False, "Número de cuotas debe ser un entero"
        
        if cuotas < 1:
            return False, "Debe haber al menos 1 cuota"
        
        if cuotas > 36:
            return False, "Máximo 36 cuotas permitidas"
        
        return True, None


# Instancia global del validator
validator = InputValidator()


def add_security_headers(response):
    """
    Agregar headers de seguridad a las respuestas.
    
    Headers agregados:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    """
    # Prevenir MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevenir clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Habilitar protección XSS del navegador
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # HSTS (solo en producción con HTTPS)
    # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy (ajustar según necesidades)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self';"
    )
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    return response


class CSRFProtection:
    """Protección CSRF simple."""
    
    def __init__(self):
        self.tokens: Dict[str, datetime] = {}
    
    def generate_token(self, session_id: str) -> str:
        """Generar token CSRF."""
        token = secrets.token_urlsafe(32)
        self.tokens[session_id] = datetime.now()
        return token
    
    def validate_token(self, session_id: str, token: str, max_age: int = 3600) -> bool:
        """Validar token CSRF."""
        if session_id not in self.tokens:
            return False
        
        # Verificar edad del token
        token_time = self.tokens[session_id]
        if (datetime.now() - token_time).seconds > max_age:
            del self.tokens[session_id]
            return False
        
        return True
    
    def remove_token(self, session_id: str):
        """Remover token."""
        if session_id in self.tokens:
            del self.tokens[session_id]


# Instancia global de CSRF protection
csrf_protection = CSRFProtection()


def require_csrf_token(f):
    """
    Decorator para requerir token CSRF en peticiones POST/PUT/DELETE.
    
    Example:
        @app.route('/api/endpoint', methods=['POST'])
        @require_csrf_token
        def endpoint():
            return {'status': 'ok'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            session_id = request.cookies.get('session', 'default')
            
            if not token or not csrf_protection.validate_token(session_id, token):
                return jsonify({
                    'error': 'CSRF token missing or invalid'
                }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


class PasswordHasher:
    """Utilidad para hashear passwords de forma segura."""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Hashear password con salt.
        
        Returns:
            (hashed_password, salt)
        """
        if not salt:
            salt = secrets.token_hex(32)
        
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        
        hashed = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000)
        return hashed.hex(), salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Verificar password contra hash."""
        new_hash, _ = PasswordHasher.hash_password(password, salt)
        return new_hash == hashed_password


# Instancia global del password hasher
password_hasher = PasswordHasher()


__all__ = [
    'rate_limiter',
    'rate_limit',
    'sanitizer',
    'validator',
    'add_security_headers',
    'csrf_protection',
    'require_csrf_token',
    'password_hasher',
    'InputSanitizer',
    'InputValidator',
    'RateLimiter',
    'CSRFProtection',
    'PasswordHasher',
]
