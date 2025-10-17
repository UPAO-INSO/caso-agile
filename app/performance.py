"""
Performance Optimization Module
Herramientas para monitorear y optimizar el rendimiento de la aplicación.
Incluye profiling de queries, optimización de database, y métricas.
"""

from functools import wraps
from typing import Callable, Optional, List, Dict, Any
from flask import current_app, g, request
from sqlalchemy import event
from sqlalchemy.engine import Engine
from datetime import datetime
import time


# ============================================================================
# QUERY PROFILING
# ============================================================================

class QueryProfiler:
    """
    Profiler para queries de SQLAlchemy.
    Registra todas las queries ejecutadas y su tiempo de ejecución.
    """
    
    def __init__(self):
        self.queries: List[Dict[str, Any]] = []
        self.enabled = False
    
    def start(self):
        """Inicia el profiling de queries."""
        self.queries = []
        self.enabled = True
    
    def stop(self):
        """Detiene el profiling de queries."""
        self.enabled = False
    
    def record_query(self, statement: str, parameters: tuple, duration: float):
        """
        Registra una query ejecutada.
        
        Args:
            statement: SQL statement
            parameters: Parámetros de la query
            duration: Duración en segundos
        """
        if not self.enabled:
            return
        
        self.queries.append({
            'statement': statement,
            'parameters': parameters,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de las queries ejecutadas.
        
        Returns:
            Diccionario con estadísticas
        """
        if not self.queries:
            return {
                'total_queries': 0,
                'total_time': 0,
                'avg_time': 0,
                'slowest_query': None
            }
        
        total_time = sum(q['duration'] for q in self.queries)
        avg_time = total_time / len(self.queries)
        slowest = max(self.queries, key=lambda q: q['duration'])
        
        return {
            'total_queries': len(self.queries),
            'total_time': round(total_time * 1000, 2),  # ms
            'avg_time': round(avg_time * 1000, 2),  # ms
            'slowest_query': {
                'statement': slowest['statement'][:200],
                'duration': round(slowest['duration'] * 1000, 2)  # ms
            },
            'queries': [
                {
                    'statement': q['statement'][:200],
                    'duration': round(q['duration'] * 1000, 2)
                }
                for q in self.queries
            ]
        }
    
    def get_slow_queries(self, threshold_ms: float = 100) -> List[Dict[str, Any]]:
        """
        Obtiene queries que exceden un umbral de tiempo.
        
        Args:
            threshold_ms: Umbral en milisegundos
        
        Returns:
            Lista de queries lentas
        """
        threshold_s = threshold_ms / 1000
        return [
            {
                'statement': q['statement'],
                'parameters': q['parameters'],
                'duration': round(q['duration'] * 1000, 2),
                'timestamp': q['timestamp']
            }
            for q in self.queries
            if q['duration'] > threshold_s
        ]


# Instancia global del profiler
_profiler = QueryProfiler()


def configure_query_profiling(app):
    """
    Configura el profiling de queries para la aplicación.
    
    Args:
        app: Instancia de Flask app
    """
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Guarda el tiempo de inicio antes de ejecutar query."""
        conn.info.setdefault('query_start_time', []).append(time.time())
    
    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Calcula duración después de ejecutar query."""
        total = time.time() - conn.info['query_start_time'].pop()
        _profiler.record_query(statement, parameters, total)
        
        # Log queries lentas en desarrollo
        if app.debug and total > 0.1:  # >100ms
            app.logger.warning(
                f'Slow query detected ({round(total * 1000, 2)}ms): '
                f'{statement[:200]}'
            )
    
    @app.before_request
    def start_profiling():
        """Inicia profiling al inicio del request."""
        if app.config.get('ENABLE_QUERY_PROFILING', False):
            _profiler.start()
    
    @app.after_request
    def log_query_stats(response):
        """Log de estadísticas al final del request."""
        if app.config.get('ENABLE_QUERY_PROFILING', False):
            stats = _profiler.get_stats()
            _profiler.stop()
            
            # Log si hay queries lentas
            if stats['total_queries'] > 0:
                app.logger.info(
                    f"Request {request.path}: {stats['total_queries']} queries, "
                    f"{stats['total_time']}ms total"
                )
                
                # Agregar header con stats
                response.headers['X-Query-Count'] = str(stats['total_queries'])
                response.headers['X-Query-Time'] = f"{stats['total_time']}ms"
        
        return response


def get_profiler() -> QueryProfiler:
    """Obtiene la instancia global del profiler."""
    return _profiler


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

def monitor_performance(threshold_ms: float = 500):
    """
    Decorator para monitorear rendimiento de funciones.
    Log de warning si excede el umbral.
    
    Args:
        threshold_ms: Umbral en milisegundos
    
    Ejemplo:
        @monitor_performance(threshold_ms=1000)
        def procesar_prestamo(prestamo_id):
            # Procesamiento costoso
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = (time.time() - start_time) * 1000
                
                # Log si excede umbral
                if duration > threshold_ms:
                    current_app.logger.warning(
                        f'Performance warning: {func.__name__} took {duration:.2f}ms '
                        f'(threshold: {threshold_ms}ms)'
                    )
                else:
                    current_app.logger.debug(
                        f'{func.__name__} completed in {duration:.2f}ms'
                    )
        
        return wrapper
    return decorator


def time_function(func: Callable) -> Callable:
    """
    Decorator simple para medir tiempo de ejecución.
    
    Ejemplo:
        @time_function
        def calcular_cuotas(monto, tasa, plazo):
            return cuotas
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        
        current_app.logger.info(f'{func.__name__} took {duration:.2f}ms')
        
        return result
    
    return wrapper


# ============================================================================
# DATABASE OPTIMIZATION
# ============================================================================

class DatabaseOptimizer:
    """
    Utilidades para optimizar operaciones de base de datos.
    """
    
    @staticmethod
    def bulk_insert(model_class, data_list: List[dict], batch_size: int = 100):
        """
        Inserta múltiples registros de forma eficiente usando bulk insert.
        
        Args:
            model_class: Clase del modelo SQLAlchemy
            data_list: Lista de diccionarios con datos
            batch_size: Tamaño del batch
        
        Ejemplo:
            data = [
                {'dni': '12345678', 'nombre': 'Juan'},
                {'dni': '87654321', 'nombre': 'María'}
            ]
            DatabaseOptimizer.bulk_insert(Cliente, data, batch_size=100)
        """
        from app import db
        
        total = len(data_list)
        for i in range(0, total, batch_size):
            batch = data_list[i:i + batch_size]
            db.session.bulk_insert_mappings(model_class, batch)
        
        db.session.commit()
        current_app.logger.info(f'Bulk insert: {total} records inserted')
    
    @staticmethod
    def bulk_update(model_class, data_list: List[dict], batch_size: int = 100):
        """
        Actualiza múltiples registros de forma eficiente.
        
        Args:
            model_class: Clase del modelo SQLAlchemy
            data_list: Lista de diccionarios con datos (debe incluir 'id')
            batch_size: Tamaño del batch
        """
        from app import db
        
        total = len(data_list)
        for i in range(0, total, batch_size):
            batch = data_list[i:i + batch_size]
            db.session.bulk_update_mappings(model_class, batch)
        
        db.session.commit()
        current_app.logger.info(f'Bulk update: {total} records updated')
    
    @staticmethod
    def optimize_indexes(model_class):
        """
        Analiza y sugiere índices para un modelo.
        
        Args:
            model_class: Clase del modelo SQLAlchemy
        
        Returns:
            Lista de sugerencias de índices
        """
        from sqlalchemy import inspect
        
        inspector = inspect(model_class)
        suggestions = []
        
        # Analizar columnas frecuentemente filtradas
        for column in inspector.columns:
            # Sugerir índice si no existe
            if column.name in ['dni', 'email', 'codigo', 'numero']:
                if not any(column.name in idx.columns for idx in inspector.indexes):
                    suggestions.append({
                        'column': column.name,
                        'reason': 'Columna frecuentemente filtrada sin índice',
                        'suggestion': f'Crear índice en {model_class.__name__}.{column.name}'
                    })
        
        return suggestions


# ============================================================================
# RESPONSE OPTIMIZATION
# ============================================================================

def optimize_json_response(data: Any, exclude_fields: Optional[List[str]] = None) -> dict:
    """
    Optimiza respuestas JSON eliminando campos innecesarios.
    
    Args:
        data: Datos a serializar (modelo, lista, dict)
        exclude_fields: Campos a excluir
    
    Returns:
        Diccionario optimizado
    
    Ejemplo:
        cliente = Cliente.query.get(1)
        response = optimize_json_response(
            cliente,
            exclude_fields=['password', 'created_at']
        )
    """
    exclude_fields = exclude_fields or []
    
    if isinstance(data, list):
        return [optimize_json_response(item, exclude_fields) for item in data]
    
    if hasattr(data, 'to_dict'):
        result = data.to_dict()
    elif isinstance(data, dict):
        result = data.copy()
    else:
        return data
    
    # Excluir campos
    for field in exclude_fields:
        result.pop(field, None)
    
    return result


def paginate_and_optimize(query, page: int, per_page: int, exclude_fields: Optional[List[str]] = None):
    """
    Pagina y optimiza respuesta en un solo paso.
    
    Args:
        query: Query de SQLAlchemy
        page: Número de página
        per_page: Elementos por página
        exclude_fields: Campos a excluir
    
    Returns:
        Diccionario con items optimizados y metadata
    """
    from app.cache import paginate_query
    
    # Paginar
    result = paginate_query(query, page, per_page)
    
    # Optimizar items
    result['items'] = [
        optimize_json_response(item, exclude_fields)
        for item in result['items']
    ]
    
    return result


# ============================================================================
# LAZY LOADING HELPERS
# ============================================================================

def lazy_load_relationship(model_instance, relationship_name: str, filters: Optional[dict] = None):
    """
    Carga una relación de forma lazy solo cuando se necesita.
    
    Args:
        model_instance: Instancia del modelo
        relationship_name: Nombre de la relación
        filters: Filtros adicionales
    
    Returns:
        Relación cargada
    
    Ejemplo:
        cliente = Cliente.query.get(1)
        # Solo cargar préstamos activos
        prestamos = lazy_load_relationship(
            cliente,
            'prestamos',
            filters={'estado': 'ACTIVO'}
        )
    """
    from sqlalchemy.orm import lazyload
    
    # Obtener relación
    relationship = getattr(model_instance.__class__, relationship_name)
    query = relationship.property.query_class(relationship.property.mapper.class_)
    
    # Aplicar filtros
    if filters:
        query = query.filter_by(**filters)
    
    return query.all()


# ============================================================================
# METRICS COLLECTION
# ============================================================================

class PerformanceMetrics:
    """
    Recolector de métricas de rendimiento.
    """
    
    def __init__(self):
        self.metrics = {
            'requests': 0,
            'avg_response_time': 0,
            'total_response_time': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'slow_requests': 0
        }
    
    def record_request(self, duration_ms: float, cache_hit: bool = False):
        """Registra una request."""
        self.metrics['requests'] += 1
        self.metrics['total_response_time'] += duration_ms
        self.metrics['avg_response_time'] = (
            self.metrics['total_response_time'] / self.metrics['requests']
        )
        
        if cache_hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1
        
        if duration_ms > 500:
            self.metrics['slow_requests'] += 1
    
    def get_metrics(self) -> dict:
        """Obtiene métricas actuales."""
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        hit_rate = (
            (self.metrics['cache_hits'] / cache_total * 100)
            if cache_total > 0 else 0
        )
        
        return {
            **self.metrics,
            'cache_hit_rate': round(hit_rate, 2)
        }
    
    def reset(self):
        """Resetea métricas."""
        self.metrics = {
            'requests': 0,
            'avg_response_time': 0,
            'total_response_time': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'slow_requests': 0
        }


# Instancia global de métricas
_metrics = PerformanceMetrics()


def get_metrics() -> PerformanceMetrics:
    """Obtiene la instancia global de métricas."""
    return _metrics


# ============================================================================
# CONFIGURATION
# ============================================================================

def configure_performance(app):
    """
    Configura el sistema de optimización de performance.
    
    Args:
        app: Instancia de Flask
    """
    # Configurar query profiling
    enable_profiling = app.config.get('ENABLE_QUERY_PROFILING', False)
    if enable_profiling:
        configure_query_profiling(app)
        app.logger.info('Query profiling habilitado')
    
    # Configurar compresión
    enable_compression = app.config.get('ENABLE_COMPRESSION', True)
    if enable_compression:
        from flask_compress import Compress
        Compress(app)
        app.logger.info('Compresión de respuestas habilitada')
    
    # Configurar monitoreo de performance
    @app.before_request
    def start_timer():
        """Inicia timer para medir duración del request."""
        g.start_time = time.time()
    
    @app.after_request
    def log_performance(response):
        """Registra métricas de performance del request."""
        if hasattr(g, 'start_time'):
            duration = (time.time() - g.start_time) * 1000  # ms
            
            # Registrar en métricas
            _metrics.record_request(duration)
            
            # Log de requests lentos
            slow_threshold = app.config.get('SLOW_REQUEST_THRESHOLD', 500)
            if duration > slow_threshold:
                app.logger.warning(
                    f'Slow request: {request.method} {request.path} '
                    f'took {duration:.2f}ms (threshold: {slow_threshold}ms)'
                )
            
            # Agregar header con duración
            response.headers['X-Response-Time'] = f'{duration:.2f}ms'
        
        return response
    
    app.logger.info('Sistema de performance configurado')
    app.logger.info(f'Slow request threshold: {app.config.get("SLOW_REQUEST_THRESHOLD", 500)}ms')


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Configuration
    'configure_performance',
    
    # Query Profiling
    'QueryProfiler',
    'configure_query_profiling',
    'get_profiler',
    
    # Performance Monitoring
    'monitor_performance',
    'time_function',
    
    # Database Optimization
    'DatabaseOptimizer',
    
    # Response Optimization
    'optimize_json_response',
    'paginate_and_optimize',
    'lazy_load_relationship',
    
    # Metrics
    'PerformanceMetrics',
    'get_metrics'
]
