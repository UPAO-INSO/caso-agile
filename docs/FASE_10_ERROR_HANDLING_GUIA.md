# 📚 Guía de Uso - Fase 10: Error Handling

## 📋 Índice

1. [Excepciones Personalizadas](#excepciones-personalizadas)
2. [Manejo de Errores en Endpoints](#manejo-de-errores-en-endpoints)
3. [Páginas de Error Personalizadas](#páginas-de-error-personalizadas)
4. [Sistema de Logging](#sistema-de-logging)
5. [Mejores Prácticas](#mejores-prácticas)

---

## 🎯 Excepciones Personalizadas

### Excepciones Disponibles

La aplicación proporciona 7 excepciones personalizadas para diferentes situaciones:

```python
from app.errors import (
    ValidationError,      # 400 - Error de validación
    UnauthorizedError,    # 401 - No autorizado
    ForbiddenError,       # 403 - Acceso prohibido
    NotFoundError,        # 404 - Recurso no encontrado
    ConflictError,        # 409 - Conflicto con estado actual
    RateLimitError,       # 429 - Límite de peticiones excedido
    ServiceUnavailableError  # 503 - Servicio no disponible
)
```

### Uso en Endpoints

#### Ejemplo 1: Validación de Datos

```python
from flask import request
from app.errors import ValidationError

@api_v1_bp.route('/clientes', methods=['POST'])
def crear_cliente():
    data = request.get_json()

    # Validar campos requeridos
    if not data.get('dni'):
        raise ValidationError(
            message='El DNI es requerido',
            payload={'field': 'dni'}
        )

    if not data.get('nombres'):
        raise ValidationError(
            message='El nombre es requerido',
            payload={'field': 'nombres'}
        )

    # Validar formato de DNI
    dni = data.get('dni')
    if len(dni) != 8 or not dni.isdigit():
        raise ValidationError(
            message='El DNI debe tener 8 dígitos',
            payload={'field': 'dni', 'value': dni}
        )

    # Continuar con la creación...
    return {'message': 'Cliente creado'}, 201
```

**Respuesta en caso de error:**

```json
{
  "error": "El DNI debe tener 8 dígitos",
  "status_code": 400,
  "field": "dni",
  "value": "12345"
}
```

#### Ejemplo 2: Recurso No Encontrado

```python
from app.errors import NotFoundError
from app.clients.models import Cliente

@api_v1_bp.route('/clientes/<int:id>', methods=['GET'])
def obtener_cliente(id):
    cliente = Cliente.query.get(id)

    if not cliente:
        raise NotFoundError(
            message=f'Cliente con ID {id} no encontrado',
            payload={'resource': 'Cliente', 'id': id}
        )

    return cliente.to_dict(), 200
```

**Respuesta en caso de error:**

```json
{
  "error": "Cliente con ID 123 no encontrado",
  "status_code": 404,
  "resource": "Cliente",
  "id": 123
}
```

#### Ejemplo 3: Conflicto (Duplicado)

```python
from app.errors import ConflictError
from sqlalchemy.exc import IntegrityError

@api_v1_bp.route('/clientes', methods=['POST'])
def crear_cliente():
    try:
        cliente = Cliente(**data)
        db.session.add(cliente)
        db.session.commit()
        return cliente.to_dict(), 201

    except IntegrityError:
        db.session.rollback()
        raise ConflictError(
            message=f'Ya existe un cliente con DNI {data["dni"]}',
            payload={'field': 'dni', 'value': data['dni']}
        )
```

**Respuesta en caso de error:**

```json
{
  "error": "Ya existe un cliente con DNI 12345678",
  "status_code": 409,
  "field": "dni",
  "value": "12345678"
}
```

#### Ejemplo 4: Acceso Prohibido

```python
from app.errors import ForbiddenError
from flask import session

@api_v1_bp.route('/admin/usuarios', methods=['GET'])
def listar_usuarios():
    user_role = session.get('role')

    if user_role != 'admin':
        raise ForbiddenError(
            message='Necesitas permisos de administrador',
            payload={'required_role': 'admin', 'user_role': user_role}
        )

    # Continuar con operación admin...
    return {'usuarios': [...]}, 200
```

#### Ejemplo 5: Servicio No Disponible

```python
from app.errors import ServiceUnavailableError
import requests

@api_v1_bp.route('/consultar-sunat', methods=['POST'])
def consultar_sunat():
    try:
        response = requests.post('https://api.sunat.gob.pe/...', timeout=5)
        response.raise_for_status()
        return response.json(), 200

    except requests.exceptions.RequestException as e:
        raise ServiceUnavailableError(
            message='El servicio de SUNAT no está disponible',
            payload={'service': 'SUNAT', 'error': str(e)}
        )
```

---

## 🛡️ Manejo de Errores en Endpoints

### Decorator @handle_errors

El decorator `@handle_errors` captura automáticamente excepciones no controladas:

```python
from app.errors import handle_errors

@api_v1_bp.route('/prestamos/<int:id>', methods=['PUT'])
@handle_errors
def actualizar_prestamo(id):
    # Cualquier excepción no capturada será manejada automáticamente
    prestamo = Prestamo.query.get_or_404(id)
    prestamo.monto = request.json['monto']
    db.session.commit()
    return prestamo.to_dict(), 200
```

### Manejo Manual con Try-Except

```python
from app.errors import ValidationError, NotFoundError, log_error

@api_v1_bp.route('/prestamos', methods=['POST'])
def crear_prestamo():
    try:
        data = request.get_json()

        # Validar datos
        if data.get('monto', 0) <= 0:
            raise ValidationError('El monto debe ser mayor a cero')

        # Verificar cliente existe
        cliente = Cliente.query.get(data['cliente_id'])
        if not cliente:
            raise NotFoundError(f'Cliente {data["cliente_id"]} no encontrado')

        # Crear préstamo
        prestamo = Prestamo(**data)
        db.session.add(prestamo)
        db.session.commit()

        return prestamo.to_dict(), 201

    except ValidationError:
        # Ya está manejado por el error handler global
        raise

    except NotFoundError:
        # Ya está manejado por el error handler global
        raise

    except Exception as e:
        # Log del error inesperado
        log_error(e, level='error', include_trace=True)
        db.session.rollback()
        raise
```

---

## 🎨 Páginas de Error Personalizadas

### Páginas Disponibles

La aplicación incluye páginas de error personalizadas para los códigos más comunes:

- **404.html** - Página no encontrada
- **500.html** - Error interno del servidor
- **403.html** - Acceso prohibido
- **409.html** - Conflicto
- **503.html** - Servicio no disponible
- **error.html** - Página genérica para otros errores

### Personalización

Todas las páginas heredan de `base.html` y usan Tailwind CSS. Para personalizar:

```html
{% extends "base.html" %} {% block title %}Mi Error Personalizado{% endblock %}
{% block content %}
<div class="min-h-screen flex items-center justify-center">
  <div class="max-w-lg w-full bg-white rounded-2xl shadow-xl p-12">
    <h1 class="text-6xl font-bold text-red-600 mb-4">{{ error_code }}</h1>
    <p class="text-xl text-gray-600 mb-8">{{ error_message }}</p>

    <!-- Botones de acción -->
    <div class="flex gap-4">
      <button
        onclick="window.history.back()"
        class="px-6 py-3 bg-blue-600 text-white rounded-lg"
      >
        Volver Atrás
      </button>
      <a href="/" class="px-6 py-3 bg-gray-200 rounded-lg"> Ir al Inicio </a>
    </div>
  </div>
</div>
{% endblock %}
```

### Detección Automática API vs Views

El sistema detecta automáticamente si la petición es para API (retorna JSON) o Views (retorna HTML):

```python
# Petición a /api/v1/clientes
# → Retorna JSON: {"error": "...", "status_code": 404}

# Petición a /views/clientes
# → Retorna HTML: página 404.html
```

---

## 📊 Sistema de Logging

### Configuración en config.py

```python
# Nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = 'INFO'

# Directorio de logs
LOG_DIR = 'logs'

# Archivo principal de logs
LOG_FILE = 'app.log'

# Tamaño máximo por archivo (10MB)
LOG_MAX_BYTES = 10 * 1024 * 1024

# Número de backups (5 archivos)
LOG_BACKUP_COUNT = 5

# Loggear requests/responses
LOG_REQUESTS = True
LOG_RESPONSES = True
```

### Archivos de Log Generados

```
logs/
├── app.log         # Todos los logs (INFO, WARNING, ERROR)
├── app.log.1       # Backup 1 (cuando app.log > 10MB)
├── app.log.2       # Backup 2
├── ...
├── error.log       # Solo errores (ERROR, CRITICAL)
└── error.log.1     # Backup de errores
```

### Uso Básico en Código

```python
from flask import current_app

# Niveles de log
current_app.logger.debug('Mensaje de debug')
current_app.logger.info('Mensaje informativo')
current_app.logger.warning('Advertencia')
current_app.logger.error('Error')
current_app.logger.critical('Error crítico')
```

### Logger Estructurado

Para logging más avanzado, usa la clase `Logger`:

```python
from app.logging_config import Logger
from flask import current_app

logger = Logger(current_app.logger)

# Log con contexto
logger.info('Usuario creado', user_id=123, username='juan')
# Output: Usuario creado | user_id=123 | username=juan

# Log de acción de usuario
logger.log_user_action(
    user_id='123',
    action='crear_prestamo',
    details='Monto: S/ 5000'
)

# Log de operación de BD
logger.log_database_operation(
    operation='INSERT',
    table='prestamos',
    record_id='456'
)

# Log de llamada a API
logger.log_api_call(
    endpoint='/api/v1/clientes',
    method='POST',
    status_code=201,
    duration_ms=45.2
)

# Log de servicio externo
logger.log_external_service(
    service='SUNAT',
    operation='consultar_ruc',
    success=True,
    duration_ms=1200.5
)

# Log de evento de seguridad
logger.log_security_event(
    event_type='failed_login',
    severity='medium',
    details='3 intentos fallidos desde IP 192.168.1.1'
)
```

### Decorator para Medir Performance

```python
from app.logging_config import log_performance

@log_performance
def calcular_tea(monto, tasa, cuotas):
    # Función que tarda mucho
    import time
    time.sleep(0.5)
    return resultado

# Si tarda >100ms, se loggea automáticamente:
# WARNING: Slow function: calcular_tea took 502.34ms
```

### Formato de Logs

```
2025-10-16 19:04:25 | INFO     | app | Aplicación iniciada en modo: DevelopmentConfig | [No Request Context]
2025-10-16 19:04:30 | INFO     | app | Request: GET /api/v1/clientes | IP: 127.0.0.1 | User-Agent: Mozilla/5.0...
2025-10-16 19:04:30 | INFO     | app | Response: 200 | GET /api/v1/clientes | Size: 1024 bytes
2025-10-16 19:04:35 | WARNING  | app | ValidationError: DNI debe tener 8 dígitos | Context: {'method': 'POST', 'path': '/api/v1/clientes', 'ip': '127.0.0.1', 'user_agent': '...'}
2025-10-16 19:04:40 | ERROR    | app | IntegrityError: UNIQUE constraint failed | Context: {...}
```

---

## ✅ Mejores Prácticas

### 1. Usar Excepciones Específicas

❌ **Mal:**

```python
if not cliente:
    return {'error': 'No encontrado'}, 404
```

✅ **Bien:**

```python
from app.errors import NotFoundError

if not cliente:
    raise NotFoundError(f'Cliente {id} no encontrado')
```

### 2. Incluir Contexto en Excepciones

❌ **Mal:**

```python
raise ValidationError('Datos inválidos')
```

✅ **Bien:**

```python
raise ValidationError(
    message='El DNI debe tener 8 dígitos',
    payload={
        'field': 'dni',
        'value': dni,
        'expected': '8 digits',
        'received': len(dni)
    }
)
```

### 3. Rollback en Errores de BD

❌ **Mal:**

```python
try:
    db.session.add(cliente)
    db.session.commit()
except Exception:
    raise  # No hace rollback
```

✅ **Bien:**

```python
try:
    db.session.add(cliente)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    log_error(e, level='error')
    raise
```

### 4. No Exponer Detalles Internos en Producción

❌ **Mal:**

```python
except Exception as e:
    return {'error': str(e)}, 500  # Expone traceback
```

✅ **Bien:**

```python
except Exception as e:
    log_error(e, level='error', include_trace=True)

    if current_app.config.get('DEBUG'):
        return {'error': str(e)}, 500
    else:
        return {'error': 'Error interno del servidor'}, 500
```

### 5. Loggear con Nivel Apropiado

```python
# DEBUG: Información detallada para debugging
logger.debug(f'Procesando cliente: {cliente_id}')

# INFO: Eventos normales importantes
logger.info(f'Cliente {cliente_id} creado exitosamente')

# WARNING: Situaciones inesperadas pero no críticas
logger.warning(f'Cliente {cliente_id} ya existe, actualizando...')

# ERROR: Errores que deben ser investigados
logger.error(f'Fallo al crear cliente {cliente_id}: {error}')

# CRITICAL: Errores críticos que requieren acción inmediata
logger.critical('Base de datos no disponible')
```

### 6. Usar Try-Except Específico

❌ **Mal:**

```python
try:
    # código
except:  # Captura TODO, incluso KeyboardInterrupt
    pass
```

✅ **Bien:**

```python
try:
    # código
except ValidationError:
    # Manejar error de validación
    raise
except NotFoundError:
    # Manejar recurso no encontrado
    raise
except SQLAlchemyError as e:
    # Manejar error de BD
    db.session.rollback()
    log_error(e, level='error')
    raise
```

### 7. Proporcionar Acciones Útiles en Errores

✅ **Bien:**

```python
raise ValidationError(
    message='El monto del préstamo excede el límite permitido',
    payload={
        'field': 'monto',
        'max_allowed': 50000,
        'provided': 75000,
        'suggestion': 'Reduce el monto o solicita aprobación especial'
    }
)
```

---

## 🎯 Ejemplo Completo

```python
from flask import Blueprint, request, current_app
from app.errors import (
    ValidationError, NotFoundError, ConflictError,
    handle_errors, log_error
)
from app.logging_config import Logger, log_performance
from app.models import Cliente, db
from sqlalchemy.exc import IntegrityError

api_bp = Blueprint('clientes_api', __name__)
logger = Logger(current_app.logger)

@api_bp.route('/clientes', methods=['POST'])
@handle_errors
@log_performance
def crear_cliente():
    """
    Crear un nuevo cliente con manejo completo de errores y logging.
    """
    # 1. Validar request
    if not request.is_json:
        raise ValidationError('Content-Type debe ser application/json')

    data = request.get_json()

    # 2. Validar campos requeridos
    required_fields = ['dni', 'nombres', 'email']
    for field in required_fields:
        if field not in data:
            raise ValidationError(
                f'Campo requerido: {field}',
                payload={'field': field}
            )

    # 3. Validar formato de DNI
    dni = data['dni']
    if len(dni) != 8 or not dni.isdigit():
        raise ValidationError(
            'El DNI debe tener 8 dígitos',
            payload={'field': 'dni', 'value': dni}
        )

    # 4. Intentar crear cliente
    try:
        cliente = Cliente(**data)
        db.session.add(cliente)
        db.session.commit()

        # Log exitoso
        logger.log_user_action(
            user_id=request.remote_addr,
            action='crear_cliente',
            details=f'DNI: {dni}'
        )

        logger.log_database_operation(
            operation='INSERT',
            table='clientes',
            record_id=str(cliente.id)
        )

        return cliente.to_dict(), 201

    except IntegrityError:
        db.session.rollback()

        # Log de conflicto
        logger.warning(
            f'Intento de crear cliente duplicado',
            dni=dni,
            ip=request.remote_addr
        )

        raise ConflictError(
            f'Ya existe un cliente con DNI {dni}',
            payload={'field': 'dni', 'value': dni}
        )

    except Exception as e:
        db.session.rollback()

        # Log de error inesperado
        log_error(e, level='error', include_trace=True)
        raise

@api_bp.route('/clientes/<int:id>', methods=['GET'])
@handle_errors
def obtener_cliente(id):
    """
    Obtener un cliente por ID con manejo de errores.
    """
    cliente = Cliente.query.get(id)

    if not cliente:
        logger.warning(f'Cliente no encontrado', cliente_id=id)
        raise NotFoundError(
            f'Cliente {id} no encontrado',
            payload={'resource': 'Cliente', 'id': id}
        )

    logger.info(f'Cliente consultado', cliente_id=id)
    return cliente.to_dict(), 200
```

---

## 📚 Recursos Adicionales

- **Documentación de Flask**: https://flask.palletsprojects.com/en/latest/errorhandling/
- **Logging en Python**: https://docs.python.org/3/library/logging.html
- **HTTP Status Codes**: https://httpstatuses.com/

---

**Fase 10: Error Handling - Guía de Uso** ✅
