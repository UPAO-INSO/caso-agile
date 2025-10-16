# Guía de Implementación - Fase 9: Seguridad

Esta guía muestra cómo aplicar las medidas de seguridad implementadas en la Fase 9.

## 📦 Componentes Disponibles

### 1. Rate Limiting
### 2. Input Validation
### 3. Input Sanitization
### 4. CSRF Protection
### 5. Security Headers (ya aplicado globalmente)
### 6. Password Hashing

---

## 🚀 Ejemplos de Uso

### 1. Rate Limiting

Aplicar rate limiting a un endpoint para prevenir abuso:

```python
from app.security import rate_limit

@api_v1_bp.route('/clientes', methods=['POST'])
@rate_limit(max_requests=10, window=60)  # 10 peticiones por minuto
def crear_cliente_api():
    # ... código del endpoint
    pass
```

**Parámetros:**
- `max_requests`: Número máximo de peticiones permitidas
- `window`: Ventana de tiempo en segundos
- `key_func`: Función personalizada para obtener el identificador (opcional)

**Ejemplo con identificador personalizado:**
```python
def get_user_id():
    return request.headers.get('User-ID', request.remote_addr)

@rate_limit(max_requests=50, window=3600, key_func=get_user_id)
def endpoint_protegido():
    pass
```

---

### 2. Input Validation

Validar datos de entrada antes de procesarlos:

```python
from app.security import validator
from flask import jsonify, request

@api_v1_bp.route('/clientes', methods=['POST'])
def crear_cliente_api():
    data = request.get_json()
    
    # Validar DNI
    is_valid, error_msg = validator.validate_dni(data.get('dni'))
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # Validar email
    is_valid, error_msg = validator.validate_email(data.get('email'))
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # Validar teléfono
    is_valid, error_msg = validator.validate_phone(data.get('telefono'))
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # Procesar datos validados...
    return jsonify({'status': 'ok'}), 201
```

**Validadores disponibles:**
- `validate_dni(dni)` - DNI peruano (8 dígitos)
- `validate_email(email)` - Formato de email
- `validate_phone(phone)` - Teléfono peruano (9 dígitos, comienza con 9)
- `validate_amount(amount, min, max)` - Monto monetario
- `validate_tea(tea)` - Tasa Efectiva Anual
- `validate_cuotas(cuotas)` - Número de cuotas (1-36)

---

### 3. Input Sanitization

Sanitizar inputs para prevenir XSS y SQL injection:

```python
from app.security import sanitizer

@api_v1_bp.route('/clientes', methods=['POST'])
def crear_cliente_api():
    data = request.get_json()
    
    # Sanitizar datos individualmente
    nombre = sanitizer.sanitize_html(data.get('nombre'))
    email = sanitizer.sanitize_html(data.get('email'))
    
    # O sanitizar todo el diccionario
    datos_limpios = sanitizer.sanitize_dict(data)
    
    # Procesar datos sanitizados...
    return jsonify({'status': 'ok'}), 201
```

**Métodos disponibles:**
- `sanitize_html(text)` - Escapar HTML para prevenir XSS
- `sanitize_sql(text)` - Limpiar para prevenir SQL injection (SQLAlchemy ya protege)
- `sanitize_filename(filename)` - Limpiar nombres de archivo
- `sanitize_dict(data)` - Sanitizar todo un diccionario recursivamente

---

### 4. CSRF Protection

Proteger endpoints contra Cross-Site Request Forgery:

```python
from app.security import require_csrf_token, csrf_protection

# En el endpoint que renderiza el formulario
@app.route('/form')
def show_form():
    session_id = request.cookies.get('session', 'default')
    csrf_token = csrf_protection.generate_token(session_id)
    return render_template('form.html', csrf_token=csrf_token)

# En el endpoint que procesa el formulario
@api_v1_bp.route('/clientes', methods=['POST'])
@require_csrf_token
def crear_cliente_api():
    # El decorator verifica el token automáticamente
    # Si el token es inválido, retorna 403
    data = request.get_json()
    # ... procesar datos
    return jsonify({'status': 'ok'}), 201
```

**En el frontend (JavaScript):**
```javascript
// Incluir el token CSRF en las peticiones
fetch('/api/v1/clientes', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken  // Token del formulario
  },
  body: JSON.stringify(data)
});
```

**En templates (formularios HTML):**
```html
<form method="POST" action="/api/v1/clientes">
  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
  <!-- resto del formulario -->
</form>
```

---

### 5. Security Headers

Los security headers se aplican automáticamente a todas las respuestas.

**Headers incluidos:**
- `X-Content-Type-Options: nosniff` - Previene MIME sniffing
- `X-Frame-Options: DENY` - Previene clickjacking
- `X-XSS-Protection: 1; mode=block` - Protección XSS del navegador
- `Content-Security-Policy` - Política de seguridad de contenido
- `Referrer-Policy` - Política de referrer
- `Permissions-Policy` - Permisos de features del navegador

**No se requiere configuración adicional** - Ya está aplicado globalmente en `app/__init__.py`.

---

### 6. Password Hashing

Hashear passwords de forma segura:

```python
from app.security import password_hasher

# Al crear/registrar usuario
password = request.form.get('password')
hashed_password, salt = password_hasher.hash_password(password)

# Guardar en BD
usuario.password_hash = hashed_password
usuario.salt = salt
db.session.commit()

# Al verificar login
password_input = request.form.get('password')
is_valid = password_hasher.verify_password(
    password_input,
    usuario.password_hash,
    usuario.salt
)

if is_valid:
    # Login exitoso
    pass
else:
    # Password incorrecto
    pass
```

---

## 📝 Ejemplo Completo de Endpoint Seguro

```python
from flask import jsonify, request
from app.security import rate_limit, validator, sanitizer, require_csrf_token
from . import api_v1_bp

@api_v1_bp.route('/clientes', methods=['POST'])
@rate_limit(max_requests=10, window=60)  # Rate limiting
@require_csrf_token  # CSRF protection
def crear_cliente_api():
    """
    Endpoint completamente seguro para crear cliente.
    """
    # 1. Obtener datos
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400
    
    # 2. Validar inputs
    validations = [
        validator.validate_dni(data.get('dni')),
        validator.validate_email(data.get('email')),
        validator.validate_phone(data.get('telefono'))
    ]
    
    for is_valid, error_msg in validations:
        if not is_valid:
            return jsonify({'error': error_msg}), 400
    
    # 3. Sanitizar inputs
    datos_limpios = sanitizer.sanitize_dict(data)
    
    # 4. Procesar datos (ahora son seguros)
    try:
        cliente = crear_cliente(
            dni=datos_limpios['dni'],
            email=datos_limpios['email'],
            telefono=datos_limpios['telefono']
        )
        
        return jsonify(cliente.to_dict()), 201
        
    except Exception as e:
        logger.error(f'Error al crear cliente: {e}')
        return jsonify({'error': 'Error interno del servidor'}), 500
```

---

## 🎯 Mejores Prácticas

### 1. Rate Limiting
- **APIs públicas:** 10-20 peticiones por minuto
- **APIs autenticadas:** 50-100 peticiones por minuto
- **Operaciones costosas:** 5-10 peticiones por minuto

### 2. Validation
- **Siempre validar en el servidor** (la validación del cliente es solo UX)
- Validar antes de sanitizar
- Retornar mensajes de error claros

### 3. Sanitization
- Sanitizar todos los inputs del usuario
- Sanitizar antes de guardar en BD
- Sanitizar antes de mostrar en templates

### 4. CSRF Protection
- Aplicar a todos los endpoints que modifican datos (POST, PUT, DELETE)
- No aplicar a APIs públicas sin estado
- Generar token por sesión

### 5. Password Security
- Nunca guardar passwords en texto plano
- Usar salt único por usuario
- Verificar complejidad de passwords

---

## 🔒 Checklist de Seguridad por Endpoint

Para cada endpoint, verificar:

- [ ] **Rate limiting aplicado** (evita abuso)
- [ ] **Inputs validados** (formato correcto)
- [ ] **Inputs sanitizados** (sin XSS/SQLi)
- [ ] **CSRF protection** (si modifica datos)
- [ ] **Autenticación** (si es endpoint privado)
- [ ] **Autorización** (permisos correctos)
- [ ] **Logging** (registrar errores)
- [ ] **Error handling** (no exponer información sensible)

---

## 📊 Monitoreo

Los headers de rate limiting se incluyen automáticamente en las respuestas:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Window: 60
```

Puedes monitorear estos headers para:
- Detectar intentos de abuso
- Ajustar límites si es necesario
- Alertar a usuarios cerca del límite

---

## ⚠️ Importante

### Para Producción:
1. **Rate Limiting:** Usar Redis en lugar de memoria
2. **CSRF:** Usar Flask-WTF o extensión dedicada
3. **HTTPS:** Obligatorio para headers de seguridad (HSTS)
4. **Secrets:** Usar variables de entorno para claves
5. **Logging:** Implementar sistema de logs centralizado

### Actualizar requirements.txt:
```bash
pip install Flask-WTF Flask-Limiter redis
```

---

**Fase 9 implementada con éxito** ✅
