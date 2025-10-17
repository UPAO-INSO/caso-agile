# 📘 Guía de Uso: Fase 11 - Optimization & Performance

## 📑 Tabla de Contenidos

1. [Sistema de Cache](#sistema-de-cache)
2. [Optimización de Queries](#optimización-de-queries)
3. [Compresión de Respuestas](#compresión-de-respuestas)
4. [Monitoreo de Rendimiento](#monitoreo-de-rendimiento)
5. [Mejores Prácticas](#mejores-prácticas)

---

## 🗄️ Sistema de Cache

### Configuración

El sistema de cache soporta múltiples backends:

```python
# Development (SimpleCache - en memoria)
CACHE_TYPE = 'SimpleCache'
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutos

# Production (RedisCache - distribuido)
CACHE_TYPE = 'RedisCache'
CACHE_REDIS_URL = 'redis://localhost:6379/0'
CACHE_DEFAULT_TIMEOUT = 600  # 10 minutos

# Alternativa (FileSystemCache - persistente)
CACHE_TYPE = 'FileSystemCache'
CACHE_DIR = 'cache'
CACHE_DEFAULT_TIMEOUT = 300
```

### Uso Básico

#### 1. Cache de Respuestas de API

```python
from app.cache import cache_response

@app.route('/api/v1/clientes')
@cache_response(timeout=600, key_prefix='clientes_list')
def listar_clientes():
    """
    Lista de clientes cacheada por 10 minutos.
    La clave incluye automáticamente query params.
    """
    clientes = Cliente.query.all()
    return jsonify([c.to_dict() for c in clientes])

# Cache diferente por página
@app.route('/api/v1/prestamos')
@cache_response(timeout=300, key_prefix='prestamos')
def listar_prestamos():
    page = request.args.get('page', 1, type=int)
    # Clave: cache:prestamos:{hash(path + params)}
    return paginate_and_optimize(Prestamo.query, page, 20)
```

#### 2. Cache de Queries

```python
from app.cache import cache_query

@cache_query(timeout=600, key_prefix='cliente')
def obtener_cliente_por_dni(dni: str):
    """
    Query cacheada - evita hits a DB repetidos.
    """
    return Cliente.query.filter_by(dni=dni).first()

# Uso
cliente = obtener_cliente_por_dni('12345678')  # DB hit
cliente = obtener_cliente_por_dni('12345678')  # Cache hit (rápido)
```

#### 3. Invalidación de Cache

```python
from app.cache import invalidate_cache, clear_cache_by_prefix

@app.route('/api/v1/clientes', methods=['POST'])
@invalidate_cache('clientes_*')
def crear_cliente():
    """
    Invalida todos los caches de clientes después de crear uno nuevo.
    """
    cliente = Cliente(**data)
    db.session.add(cliente)
    db.session.commit()
    return jsonify(cliente.to_dict()), 201

# Invalidación manual
def actualizar_configuracion():
    # ... actualizar config ...
    clear_cache_by_prefix('config')
```

#### 4. Memoización (Cache en Memoria)

Para funciones puras sin side effects:

```python
from app.cache import memoize

@memoize(timeout=1800)  # 30 minutos
def calcular_tea_efectivo(monto: float, tasa: float, cuotas: int) -> float:
    """
    Cálculo costoso cacheado en memoria.
    Ideal para cálculos matemáticos complejos.
    """
    # Cálculo complejo...
    return tea

# Uso
tea1 = calcular_tea_efectivo(10000, 0.05, 12)  # Calcula
tea2 = calcular_tea_efectivo(10000, 0.05, 12)  # Retorna cached

# Limpiar cache manualmente
calcular_tea_efectivo.clear_cache()
```

### Estadísticas de Cache

```python
from app.cache import get_cache_stats

@app.route('/admin/cache/stats')
def cache_stats():
    """Endpoint para monitorear cache."""
    stats = get_cache_stats()
    return jsonify(stats)
    # {
    #   'enabled': True,
    #   'hits': 1250,
    #   'misses': 350,
    #   'hit_rate': 78.1
    # }
```

---

## 🚀 Optimización de Queries

### 1. Evitar Problema N+1

#### ❌ Problema (N+1 queries)

```python
# Esto genera 1 query + N queries adicionales
clientes = Cliente.query.all()  # 1 query
for cliente in clientes:
    print(cliente.prestamos)  # N queries (uno por cliente)
```

#### ✅ Solución (Eager Loading)

```python
from app.cache import eager_load
from sqlalchemy.orm import joinedload

# Una sola query con JOIN
clientes = Cliente.query.options(
    *eager_load('prestamos', 'declaraciones')
).all()

for cliente in clientes:
    print(cliente.prestamos)  # Sin queries adicionales
```

### 2. Paginación Eficiente

```python
from app.cache import paginate_query

@app.route('/api/v1/clientes')
def listar_clientes():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Cliente.query.order_by(Cliente.id)
    result = paginate_query(query, page, per_page)

    return jsonify({
        'items': [c.to_dict() for c in result['items']],
        'total': result['total'],
        'page': result['page'],
        'pages': result['pages'],
        'has_next': result['has_next'],
        'has_prev': result['has_prev']
    })
```

### 3. Paginación + Optimización

```python
from app.performance import paginate_and_optimize

@app.route('/api/v1/clientes')
@cache_response(timeout=300)
def listar_clientes():
    page = request.args.get('page', 1, type=int)

    # Pagina y excluye campos innecesarios
    result = paginate_and_optimize(
        Cliente.query,
        page=page,
        per_page=20,
        exclude_fields=['password', 'created_at']
    )

    return jsonify(result)
```

### 4. Bulk Operations

Para operaciones masivas (más eficiente que loops):

```python
from app.performance import DatabaseOptimizer

# Inserción masiva
data = [
    {'dni': '12345678', 'nombre': 'Juan', 'apellido': 'Pérez'},
    {'dni': '87654321', 'nombre': 'María', 'apellido': 'García'},
    # ... 1000 registros ...
]

DatabaseOptimizer.bulk_insert(Cliente, data, batch_size=100)
# Inserta 1000 registros en ~10 queries (vs 1000 queries individuales)

# Actualización masiva
updates = [
    {'id': 1, 'estado': 'ACTIVO'},
    {'id': 2, 'estado': 'INACTIVO'},
    # ...
]

DatabaseOptimizer.bulk_update(Cliente, updates, batch_size=100)
```

### 5. Lazy Loading Selectivo

```python
from app.performance import lazy_load_relationship

# Cargar solo préstamos activos de un cliente
cliente = Cliente.query.get(1)
prestamos_activos = lazy_load_relationship(
    cliente,
    'prestamos',
    filters={'estado': 'ACTIVO'}
)
```

---

## 📦 Compresión de Respuestas

### Compresión Automática

Flask-Compress se configura automáticamente para comprimir respuestas >1KB:

```python
# Configuración en config.py
ENABLE_COMPRESSION = True
COMPRESSION_MIN_SIZE = 1024  # 1KB

# Flask-Compress automáticamente:
# - Detecta Accept-Encoding: gzip en headers
# - Comprime respuestas grandes (>1KB)
# - Agrega Content-Encoding: gzip
# - Reduce tamaño de respuesta en 70-90%
```

### Compresión Manual

```python
from app.cache import compress_response

@app.route('/api/v1/reportes/completo')
@compress_response
def reporte_completo():
    """
    Para respuestas específicas que siempre deben comprimirse.
    """
    data = generar_reporte_grande()  # 5MB de datos
    return jsonify(data)
    # Response: ~500KB con compresión gzip
```

### Verificar Compresión

```bash
# Request con curl
curl -H "Accept-Encoding: gzip" http://localhost:5000/api/v1/clientes -v

# Response headers:
# Content-Encoding: gzip
# Content-Length: 1234 (comprimido)
```

---

## 📊 Monitoreo de Rendimiento

### 1. Query Profiling

#### Habilitar en Development

```python
# config.py - DevelopmentConfig
ENABLE_QUERY_PROFILING = True
SLOW_QUERY_THRESHOLD = 0.1  # 100ms
```

#### Ver Estadísticas

```python
from app.performance import get_profiler

@app.route('/admin/queries')
def query_stats():
    """Ver todas las queries del request."""
    profiler = get_profiler()
    stats = profiler.get_stats()

    return jsonify(stats)
    # {
    #   'total_queries': 15,
    #   'total_time': 450.23,  # ms
    #   'avg_time': 30.01,  # ms
    #   'slowest_query': {
    #     'statement': 'SELECT * FROM clientes...',
    #     'duration': 125.45  # ms
    #   },
    #   'queries': [...]
    # }

@app.route('/admin/queries/slow')
def slow_queries():
    """Ver solo queries lentas."""
    profiler = get_profiler()
    slow = profiler.get_slow_queries(threshold_ms=100)

    return jsonify(slow)
```

### 2. Performance Monitoring

#### Decorador para Funciones

```python
from app.performance import monitor_performance

@monitor_performance(threshold_ms=1000)
def procesar_prestamo_complejo(prestamo_id):
    """
    Log de warning si toma >1000ms.
    """
    # Procesamiento costoso...
    return resultado
```

#### Decorador Simple

```python
from app.performance import time_function

@time_function
def calcular_cuotas(monto, tasa, plazo):
    """Siempre log del tiempo de ejecución."""
    # Cálculos...
    return cuotas
    # Log: "calcular_cuotas took 45.23ms"
```

### 3. Métricas Globales

```python
from app.performance import get_metrics

@app.route('/admin/metrics')
def metrics():
    """Métricas de rendimiento de la aplicación."""
    metrics = get_metrics()
    return jsonify(metrics.get_metrics())
    # {
    #   'requests': 10000,
    #   'avg_response_time': 125.45,  # ms
    #   'cache_hits': 7500,
    #   'cache_misses': 2500,
    #   'cache_hit_rate': 75.0,  # %
    #   'slow_requests': 150
    # }
```

### 4. Headers de Performance

En desarrollo, cada response incluye headers con stats:

```http
X-Query-Count: 5
X-Query-Time: 45.23ms
```

---

## 🎯 Mejores Prácticas

### 1. Estrategia de Cache

```python
# ✅ Cache para datos que cambian poco
@cache_response(timeout=3600)  # 1 hora
def obtener_configuracion():
    return Config.query.all()

# ✅ Cache para listados
@cache_response(timeout=300)  # 5 minutos
def listar_clientes():
    return Cliente.query.all()

# ❌ NO cachear datos que cambian frecuentemente
@cache_response(timeout=60)  # Demasiado corto
def obtener_saldo_actual():
    return calcular_saldo()  # Cambia constantemente
```

### 2. Invalidación Proactiva

```python
# ✅ Invalidar después de modificar datos
@invalidate_cache('clientes_*')
def actualizar_cliente(id):
    cliente = Cliente.query.get(id)
    cliente.nombre = 'Nuevo Nombre'
    db.session.commit()
    # Cache de clientes se invalida automáticamente

# ✅ Invalidar múltiples caches relacionados
@invalidate_cache('prestamos_*')
@invalidate_cache('clientes_*')
def crear_prestamo(cliente_id):
    # Invalida caches de préstamos y clientes
    pass
```

### 3. Optimización de Queries

```python
# ✅ Eager loading para relaciones frecuentes
clientes = Cliente.query.options(
    joinedload(Cliente.prestamos)
).all()

# ✅ Seleccionar solo campos necesarios
clientes = db.session.query(
    Cliente.id,
    Cliente.nombre,
    Cliente.dni
).all()

# ✅ Usar índices en columnas filtradas
# En modelo:
class Cliente(db.Model):
    dni = db.Column(db.String(8), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
```

### 4. Compresión Inteligente

```python
# ✅ Comprimir respuestas grandes
@compress_response
def export_all_data():
    # 10MB de datos -> 1MB comprimido
    return jsonify(all_data)

# ❌ No comprimir respuestas pequeñas (overhead)
# Flask-Compress automáticamente solo comprime >1KB
```

### 5. Monitoreo en Producción

```python
# ✅ Deshabilitar profiling en producción (overhead)
# config.py - ProductionConfig
ENABLE_QUERY_PROFILING = False

# ✅ Mantener compresión habilitada
ENABLE_COMPRESSION = True

# ✅ Usar Redis para cache distribuido
CACHE_TYPE = 'RedisCache'
CACHE_REDIS_URL = 'redis://production-server:6379/0'
```

---

## 📈 Ejemplo Completo

```python
from flask import Blueprint
from app.cache import cache_response, invalidate_cache, paginate_query
from app.performance import monitor_performance, paginate_and_optimize

api_bp = Blueprint('api', __name__)

# Lista de clientes (cacheada y optimizada)
@api_bp.route('/api/v1/clientes')
@cache_response(timeout=300, key_prefix='clientes_list')
def listar_clientes():
    page = request.args.get('page', 1, type=int)

    # Eager loading + paginación + optimización
    query = Cliente.query.options(
        joinedload(Cliente.prestamos)
    ).order_by(Cliente.id)

    result = paginate_and_optimize(
        query,
        page=page,
        per_page=20,
        exclude_fields=['password', 'internal_notes']
    )

    return jsonify(result)

# Crear cliente (invalida cache)
@api_bp.route('/api/v1/clientes', methods=['POST'])
@invalidate_cache('clientes_*')
@monitor_performance(threshold_ms=500)
def crear_cliente():
    data = request.get_json()

    # Validar...
    cliente = Cliente(**data)
    db.session.add(cliente)
    db.session.commit()

    return jsonify(cliente.to_dict()), 201

# Reporte complejo (monitoreo + cache)
@api_bp.route('/api/v1/reportes/prestamos')
@cache_response(timeout=600, key_prefix='reporte_prestamos')
@monitor_performance(threshold_ms=2000)
def reporte_prestamos():
    # Query optimizada
    prestamos = Prestamo.query.options(
        joinedload(Prestamo.cliente),
        joinedload(Prestamo.cuotas)
    ).all()

    # Generar reporte (operación costosa)
    reporte = generar_reporte_completo(prestamos)

    return jsonify(reporte)
```

---

## 🔍 Troubleshooting

### Cache no funciona

```python
# Verificar configuración
from app.cache import get_cache_stats
stats = get_cache_stats()
print(stats)  # {'enabled': True/False}

# Limpiar cache manualmente
from app.cache import clear_cache_by_prefix
clear_cache_by_prefix('clientes')
```

### Queries lentas

```python
# Habilitar profiling
ENABLE_QUERY_PROFILING = True

# Ver queries lentas
from app.performance import get_profiler
profiler = get_profiler()
slow = profiler.get_slow_queries(threshold_ms=100)
```

### Compresión no aplica

```bash
# Verificar que cliente soporta gzip
curl -H "Accept-Encoding: gzip" http://localhost:5000/api/v1/clientes -v

# Verificar tamaño de respuesta (debe ser >1KB)
```

---

## 📚 Referencias

- **Flask-Caching**: https://flask-caching.readthedocs.io/
- **Flask-Compress**: https://github.com/colour-science/flask-compress
- **SQLAlchemy Performance**: https://docs.sqlalchemy.org/en/20/faq/performance.html
- **Redis**: https://redis.io/docs/

---

**Próximo paso**: Phase 5 - Unit Tests
