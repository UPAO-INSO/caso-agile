"""
Cache Module
Sistema de caching para mejorar el rendimiento de la aplicación.
Proporciona decorators y utilidades para cachear respuestas, queries y cálculos costosos.
"""

from functools import wraps
from typing import Optional, Callable, Any
from flask import current_app, request
import hashlib
import json


# ============================================================================
# CACHE DECORATORS
# ============================================================================

def cache_response(timeout: int = 300, key_prefix: Optional[str] = None):
    """
    Decorator para cachear respuestas de endpoints.
    
    Args:
        timeout: Tiempo de vida del cache en segundos (default: 300 = 5 minutos)
        key_prefix: Prefijo para la clave del cache (default: nombre de la función)
    
    Ejemplo:
        @app.route('/api/v1/clientes')
        @cache_response(timeout=600, key_prefix='clientes_list')
        def listar_clientes():
            return {'clientes': Cliente.query.all()}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Verificar si el cache está habilitado
            cache = current_app.extensions.get('cache')
            if not cache:
                return func(*args, **kwargs)
            
            # Generar clave de cache
            cache_key = _generate_cache_key(func, key_prefix, args, kwargs)
            
            # Intentar obtener del cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                current_app.logger.debug(f'Cache HIT: {cache_key}')
                return cached_response
            
            # Si no está en cache, ejecutar función
            current_app.logger.debug(f'Cache MISS: {cache_key}')
            response = func(*args, **kwargs)
            
            # Guardar en cache
            cache.set(cache_key, response, timeout=timeout)
            
            return response
        
        return wrapper
    return decorator


def cache_query(timeout: int = 300, key_prefix: Optional[str] = None):
    """
    Decorator para cachear resultados de queries SQLAlchemy.
    
    Args:
        timeout: Tiempo de vida del cache en segundos
        key_prefix: Prefijo para la clave del cache
    
    Ejemplo:
        @cache_query(timeout=600, key_prefix='cliente')
        def obtener_cliente_por_dni(dni: str):
            return Cliente.query.filter_by(dni=dni).first()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = current_app.extensions.get('cache')
            if not cache:
                return func(*args, **kwargs)
            
            # Generar clave
            cache_key = _generate_cache_key(func, key_prefix, args, kwargs)
            
            # Intentar obtener del cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                current_app.logger.debug(f'Query Cache HIT: {cache_key}')
                return cached_result
            
            # Ejecutar query
            current_app.logger.debug(f'Query Cache MISS: {cache_key}')
            result = func(*args, **kwargs)
            
            # Guardar en cache (solo si hay resultado)
            if result is not None:
                cache.set(cache_key, result, timeout=timeout)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_pattern: str):
    """
    Decorator para invalidar cache cuando se modifica un recurso.
    
    Args:
        key_pattern: Patrón de claves a invalidar (ej: 'clientes_*')
    
    Ejemplo:
        @app.route('/api/v1/clientes', methods=['POST'])
        @invalidate_cache('clientes_*')
        def crear_cliente():
            # Invalida todos los caches de clientes
            cliente = Cliente(**data)
            db.session.add(cliente)
            db.session.commit()
            return cliente.to_dict()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Ejecutar función primero
            result = func(*args, **kwargs)
            
            # Invalidar cache después
            cache = current_app.extensions.get('cache')
            if cache:
                try:
                    # Invalidar por patrón (si el backend lo soporta)
                    if hasattr(cache, 'delete_many'):
                        cache.delete_many(key_pattern)
                        current_app.logger.info(f'Cache invalidated: {key_pattern}')
                    else:
                        # Fallback: limpiar todo el cache
                        cache.clear()
                        current_app.logger.info('Cache cleared (pattern not supported)')
                except Exception as e:
                    current_app.logger.warning(f'Cache invalidation failed: {e}')
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# CACHE HELPERS
# ============================================================================

def _generate_cache_key(func: Callable, prefix: Optional[str], args: tuple, kwargs: dict) -> str:
    """
    Genera una clave única para el cache basada en la función y sus argumentos.
    
    Args:
        func: Función a cachear
        prefix: Prefijo personalizado
        args: Argumentos posicionales
        kwargs: Argumentos con nombre
    
    Returns:
        Clave de cache única
    """
    # Usar prefijo personalizado o nombre de función
    key_parts = [prefix or func.__name__]
    
    # Agregar path y query params del request (si existe)
    if request:
        key_parts.append(request.path)
        if request.args:
            key_parts.append(str(sorted(request.args.items())))
    
    # Agregar argumentos de la función
    if args:
        key_parts.append(str(args))
    if kwargs:
        key_parts.append(str(sorted(kwargs.items())))
    
    # Generar hash MD5 de la clave
    key_string = '|'.join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f'cache:{prefix or func.__name__}:{key_hash}'


def clear_cache_by_prefix(prefix: str):
    """
    Limpia todas las entradas del cache con un prefijo específico.
    
    Args:
        prefix: Prefijo de las claves a limpiar (ej: 'clientes')
    
    Ejemplo:
        # Limpiar todos los caches de clientes
        clear_cache_by_prefix('clientes')
    """
    cache = current_app.extensions.get('cache')
    if not cache:
        return
    
    try:
        if hasattr(cache, 'delete_many'):
            cache.delete_many(f'cache:{prefix}:*')
            current_app.logger.info(f'Cache cleared for prefix: {prefix}')
        else:
            cache.clear()
            current_app.logger.info('Entire cache cleared (prefix delete not supported)')
    except Exception as e:
        current_app.logger.error(f'Failed to clear cache: {e}')


def get_cache_stats() -> dict:
    """
    Obtiene estadísticas del cache.
    
    Returns:
        Diccionario con estadísticas del cache
    """
    cache = current_app.extensions.get('cache')
    if not cache:
        return {'enabled': False}
    
    stats = {'enabled': True}
    
    # Intentar obtener estadísticas (depende del backend)
    if hasattr(cache, 'get_stats'):
        try:
            stats.update(cache.get_stats())
        except Exception:
            pass
    
    return stats


# ============================================================================
# MEMOIZATION
# ============================================================================

def memoize(timeout: int = 3600):
    """
    Decorator para memoizar resultados de funciones (cache en memoria).
    Similar a cache_query pero para funciones puras (sin side effects).
    
    Args:
        timeout: Tiempo de vida en segundos (default: 1 hora)
    
    Ejemplo:
        @memoize(timeout=1800)
        def calcular_tea_complejo(monto, tasa, cuotas):
            # Cálculo costoso
            return resultado
    """
    def decorator(func: Callable) -> Callable:
        cache_dict = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave simple
            key = str(args) + str(sorted(kwargs.items()))
            
            # Verificar cache en memoria
            if key in cache_dict:
                current_app.logger.debug(f'Memoization HIT: {func.__name__}')
                return cache_dict[key]
            
            # Calcular resultado
            current_app.logger.debug(f'Memoization MISS: {func.__name__}')
            result = func(*args, **kwargs)
            
            # Guardar en cache (limitado a 100 entradas)
            if len(cache_dict) >= 100:
                # Limpiar la entrada más antigua
                cache_dict.pop(next(iter(cache_dict)))
            
            cache_dict[key] = result
            return result
        
        # Agregar método para limpiar cache
        wrapper.clear_cache = lambda: cache_dict.clear()
        
        return wrapper
    return decorator


# ============================================================================
# COMPRESSION
# ============================================================================

def compress_response(func: Callable) -> Callable:
    """
    Decorator para comprimir respuestas con gzip.
    Solo aplica para respuestas grandes (>1KB).
    
    Ejemplo:
        @app.route('/api/v1/clientes')
        @compress_response
        def listar_clientes():
            return {'clientes': Cliente.query.all()}
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import make_response
        import gzip
        
        # Ejecutar función
        response = func(*args, **kwargs)
        
        # Convertir a Response object si es necesario
        if not hasattr(response, 'data'):
            response = make_response(response)
        
        # Verificar si el cliente acepta gzip
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_encoding:
            return response
        
        # Comprimir solo si el contenido es suficientemente grande (>1KB)
        if len(response.data) < 1024:
            return response
        
        # Comprimir
        compressed_data = gzip.compress(response.data)
        
        # Solo usar compresión si reduce el tamaño
        if len(compressed_data) < len(response.data):
            response.data = compressed_data
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = len(compressed_data)
            current_app.logger.debug(
                f'Response compressed: {len(response.data)} -> {len(compressed_data)} bytes'
            )
        
        return response
    
    return wrapper


# ============================================================================
# QUERY OPTIMIZATION
# ============================================================================

def eager_load(*relationships):
    """
    Helper para cargar relaciones de SQLAlchemy de forma eager (evita N+1).
    
    Args:
        *relationships: Nombres de las relaciones a cargar
    
    Ejemplo:
        from sqlalchemy.orm import joinedload
        
        # Sin eager loading (N+1 problem)
        clientes = Cliente.query.all()
        for cliente in clientes:
            print(cliente.prestamos)  # Query adicional por cada cliente
        
        # Con eager loading (1 query)
        clientes = Cliente.query.options(
            *eager_load('prestamos', 'declaraciones')
        ).all()
    """
    from sqlalchemy.orm import joinedload
    return [joinedload(rel) for rel in relationships]


def paginate_query(query, page: int = 1, per_page: int = 20):
    """
    Helper para paginar queries de forma eficiente.
    
    Args:
        query: Query de SQLAlchemy
        page: Número de página (1-indexed)
        per_page: Elementos por página
    
    Returns:
        Diccionario con items y metadata de paginación
    
    Ejemplo:
        query = Cliente.query.order_by(Cliente.id)
        result = paginate_query(query, page=2, per_page=10)
        # {
        #   'items': [...],
        #   'total': 100,
        #   'page': 2,
        #   'per_page': 10,
        #   'pages': 10,
        #   'has_next': True,
        #   'has_prev': True
        # }
    """
    # Obtener total (cached)
    total = query.count()
    
    # Calcular offset
    offset = (page - 1) * per_page
    
    # Obtener items
    items = query.limit(per_page).offset(offset).all()
    
    # Calcular metadata
    pages = (total + per_page - 1) // per_page
    has_next = page < pages
    has_prev = page > 1
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
        'has_next': has_next,
        'has_prev': has_prev
    }


def configure_cache(app):
    """
    Configura el sistema de caching para la aplicación Flask.
    
    Args:
        app: Instancia de Flask
    
    Returns:
        Cache: Instancia del cache configurado
    """
    from flask_caching import Cache
    
    # Inicializar Flask-Caching
    cache = Cache()
    cache.init_app(app)
    
    # Logging
    cache_type = app.config.get('CACHE_TYPE', 'SimpleCache')
    timeout = app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
    
    app.logger.info(f'Cache configurado: {cache_type}')
    app.logger.info(f'Cache timeout por defecto: {timeout}s')
    
    if cache_type == 'RedisCache':
        redis_url = app.config.get('CACHE_REDIS_URL', 'redis://localhost:6379/0')
        app.logger.info(f'Redis URL: {redis_url}')
    elif cache_type == 'FileSystemCache':
        cache_dir = app.config.get('CACHE_DIR', 'cache')
        app.logger.info(f'Cache directory: {cache_dir}')
    
    return cache


__all__ = [
    # Configuration
    'configure_cache',
    
    # Decorators
    'cache_response',
    'cache_query',
    'invalidate_cache',
    'memoize',
    'compress_response',
    
    # Helpers
    'clear_cache_by_prefix',
    'get_cache_stats',
    'eager_load',
    'paginate_query'
]
