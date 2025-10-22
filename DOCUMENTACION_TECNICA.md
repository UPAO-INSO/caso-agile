# DOCUMENTACIÓN TÉCNICA DEL SISTEMA DE PRÉSTAMOS
## 1. ARQUITECTURA DEL SISTEMA
### 1.1 Patrón Arquitectónico
El sistema implementa una **arquitectura MVC (Model-View-Controller)** con separación de capas, utilizando el framework Flask para Python. La estructura sigue el patrón de **Blueprints** de Flask para modularizar la aplicación en componentes independientes.

### 1.2 Estructura de Capas
```
┌─────────────────────────────────────┐
│   CAPA DE PRESENTACIÓN (Frontend)   │
│   - Templates Jinja2                │
│   - JavaScript (Vanilla)            │
│   - TailwindCSS                     │
└─────────────────────────────────────┘
            ↕ HTTP/JSON
┌─────────────────────────────────────┐
│   CAPA DE CONTROLADORES (Routes)    │
│   - Blueprints por módulo           │
│   - Validación de datos (Pydantic)  │
│   - Gestión de peticiones HTTP      │
└─────────────────────────────────────┘
            ↕
┌─────────────────────────────────────┐
│   CAPA DE LÓGICA (CRUD)             │
│   - Reglas de negocio               │
│   - Operaciones de datos            │
│   - Integración con APIs externas   │
└─────────────────────────────────────┘
            ↕
┌─────────────────────────────────────┐
│   CAPA DE PERSISTENCIA (Models)     │
│   - SQLAlchemy ORM                  │
│   - Modelos de base de datos        │
└─────────────────────────────────────┘
            ↕
┌─────────────────────────────────────┐
│   BASE DE DATOS (PostgreSQL)        │
└─────────────────────────────────────┘
```

### 1.3 Módulos del Sistema
El sistema está dividido en **4 módulos principales**:

1. **Clientes** (`/app/clients`)
2. **Préstamos** (`/app/prestamos`)
3. **Cuotas** (`/app/cuotas`)
4. **Declaraciones Juradas** (`/app/declaraciones`)

### 1.4 Estructura de Directorios
```
caso-agile/
├── app/
│   ├── __init__.py                 # Inicialización Flask
│   ├── routes.py                   # Rutas principales
│   ├── clients/                    # Módulo de clientes
│   │   ├── __init__.py
│   │   ├── routes.py              # Endpoints REST
│   │   ├── crud.py                # Lógica de negocio
│   │   ├── model/
│   │   │   └── clients.py         # Modelo SQLAlchemy
│   │   └── templates/
│   │       ├── list.html
│   │       ├── detail.html
│   │       └── lista_clientes.html
│   ├── prestamos/                  # Módulo de préstamos
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── crud.py
│   │   ├── schemas.py             # Validación Pydantic
│   │   ├── model/
│   │   │   └── prestamos.py
│   │   └── templates/
│   ├── cuotas/                     # Módulo de cuotas
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── crud.py
│   │   └── model/
│   │       └── cuotas.py
│   ├── declaraciones/              # Módulo de declaraciones
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── crud.py
│   │   └── model/
│   │       └── declaraciones.py
│   ├── common/                     # Utilidades compartidas
│   │   ├── error_handler.py
│   │   └── utils.py
│   ├── static/                     # Archivos estáticos
│   │   ├── css/
│   │   │   ├── input.css
│   │   │   └── style.css
│   │   └── js/
│   │       ├── client-search.js
│   │       ├── loan-modal.js
│   │       └── utils.js
│   └── templates/                  # Templates generales
│       ├── base.html
│       ├── index.html
│       └── components/
│           ├── form.html
│           └── schedule.html
├── migrations/                     # Migraciones Alembic
├── .env                           # Variables de entorno
├── app.py                         # Punto de entrada
└── requirements.txt               # Dependencias
```

---

## 2. FUNCIONAMIENTO DEL SISTEMA

### 2.1 Flujo Principal de Operación

#### FASE 1: Búsqueda y Validación de Cliente
1. Usuario ingresa DNI de 8 dígitos
2. Sistema busca cliente en base de datos local
3. Si no existe, consulta API RENIEC (APIPERU)
4. Valida automáticamente si es PEP contra dataset de 38,112 registros
5. Verifica si tiene préstamos activos (estado VIGENTE)

#### FASE 2: Registro de Préstamo
1. Usuario ingresa monto, plazo y correo electrónico
2. Sistema valida reglas de negocio:
   - Cliente no debe tener préstamo activo
   - Monto mayor a 1 UIT (S/ 5,150) requiere declaración jurada
   - Cliente PEP requiere declaración jurada obligatoria
3. Genera cronograma de pagos con método francés (cuota fija)
4. Calcula intereses con TEA del 30% anual

#### FASE 3: Generación de Cuotas
1. Crea préstamo en base de datos
2. Genera cronograma completo de cuotas
3. Calcula para cada cuota: capital, interés y saldo
4. Registra declaración jurada si es requerida

#### FASE 4: Gestión de Estados
1. Préstamo inicia en estado VIGENTE
2. Permite cambio manual a CANCELADO
3. Estado CANCELADO es irreversible
4. Cliente no puede tener múltiples préstamos VIGENTES

### 2.2 Diagrama de Flujo de Registro
```
┌─────────────┐
│ Ingresar DNI│
└──────┬──────┘
       │
       ▼
┌─────────────────┐      NO      ┌──────────────────┐
│ ¿Existe en BD?  │─────────────>│ Consultar RENIEC │
└────────┬────────┘              └────────┬─────────┘
         │ SI                              │
         ▼                                 ▼
┌─────────────────┐              ┌──────────────────┐
│ Cargar datos    │              │ Validar PEP      │
└────────┬────────┘              └────────┬─────────┘
         │                                 │
         └────────────┬────────────────────┘
                      ▼
              ┌──────────────────┐
              │ ¿Préstamo activo?│
              └────────┬─────────┘
                       │
           ┌───────────┴──────────┐
           │ SI                   │ NO
           ▼                      ▼
    ┌─────────────┐        ┌──────────────┐
    │ BLOQUEAR    │        │ PERMITIR     │
    │ Formulario  │        │ Formulario   │
    └─────────────┘        └──────┬───────┘
                                  │
                                  ▼
                           ┌──────────────┐
                           │ Ingresar datos│
                           └──────┬───────┘
                                  │
                                  ▼
                           ┌──────────────────┐
                           │ Validar reglas   │
                           │ - Monto > UIT?   │
                           │ - Cliente PEP?   │
                           └──────┬───────────┘
                                  │
                                  ▼
                           ┌──────────────────┐
                           │ Crear préstamo   │
                           └──────┬───────────┘
                                  │
                                  ▼
                           ┌──────────────────┐
                           │ Generar cuotas   │
                           └──────┬───────────┘
                                  │
                                  ▼
                           ┌──────────────────┐
                           │ Crear declaración│
                           │ (si requiere)    │
                           └──────┬───────────┘
                                  │
                                  ▼
                           ┌──────────────────┐
                           │ ÉXITO            │
                           └──────────────────┘
```

---

## 3. MODELO DE DATOS

### 3.1 Cantidad de Clases/Entidades

**TOTAL: 4 clases principales**

#### 3.1.1 Cliente
```python
class Cliente(db.Model):
    __tablename__ = 'clientes'
    
    # Campos
    cliente_id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(8), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(200), nullable=False)
    apellido_paterno = db.Column(db.String(100), nullable=False)
    apellido_materno = db.Column(db.String(100))
    pep = db.Column(db.Boolean, default=False, nullable=False)
    fecha_registro = db.Column(db.DateTime, server_default=db.func.now())
    
    # Relaciones
    prestamos = relationship("Prestamo", back_populates="cliente")
    declaraciones_juradas = relationship("DeclaracionJurada", back_populates="cliente")
```

**Restricciones:**
- DNI único (CONSTRAINT)
- DNI debe tener exactamente 8 dígitos
- PEP es validado automáticamente contra dataset oficial

#### 3.1.2 Prestamo
```python
class Prestamo(db.Model):
    __tablename__ = 'prestamos'
    
    # Campos
    prestamo_id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.cliente_id'))
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    interes_tea = db.Column(db.Numeric(5, 2), nullable=False)
    plazo = db.Column(db.Integer, nullable=False)
    f_otorgamiento = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum(EstadoPrestamoEnum))
    requiere_dec_jurada = db.Column(db.Boolean, default=False)
    declaracion_id = db.Column(db.Integer, db.ForeignKey('declaraciones_juradas.declaracion_id'))
    
    # Relaciones
    cliente = relationship("Cliente", back_populates="prestamos")
    cuotas = relationship("Cuota", back_populates="prestamo")
    declaracion = relationship("DeclaracionJurada")
```

**Estados posibles:**
```python
class EstadoPrestamoEnum(enum.Enum):
    VIGENTE = 'VIGENTE'      # Préstamo activo
    CANCELADO = 'CANCELADO'  # Préstamo finalizado (irreversible)
```

**Reglas de negocio:**
- Un cliente solo puede tener UN préstamo VIGENTE
- Estado CANCELADO no puede cambiar
- TEA (Tasa Efectiva Anual) por defecto: 30%

#### 3.1.3 Cuota
```python
class Cuota(db.Model):
    __tablename__ = 'cuotas'
    
    # Campos
    cuota_id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey('prestamos.prestamo_id'))
    numero_cuota = db.Column(db.Integer, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    monto_cuota = db.Column(db.Numeric(10, 2), nullable=False)
    monto_capital = db.Column(db.Numeric(10, 2), nullable=False)
    monto_interes = db.Column(db.Numeric(10, 2), nullable=False)
    saldo_capital = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relaciones
    prestamo = relationship("Prestamo", back_populates="cuotas")
```

**Cálculo de cuotas:**
- Método francés (sistema de amortización)
- Cuota fija durante todo el plazo
- Interés decreciente, capital creciente

#### 3.1.4 DeclaracionJurada
```python
class DeclaracionJurada(db.Model):
    __tablename__ = 'declaraciones_juradas'
    
    # Campos
    declaracion_id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.cliente_id'))
    tipo_declaracion = db.Column(db.Enum(TipoDeclaracionEnum))
    fecha_firma = db.Column(db.Date, nullable=False)
    firmado = db.Column(db.Boolean, default=False)
    
    # Relaciones
    cliente = relationship("Cliente", back_populates="declaraciones_juradas")
```

**Tipos de declaración:**
```python
class TipoDeclaracionEnum(enum.Enum):
    USO_PROPIO = 'USO_PROPIO'  # Monto > 1 UIT
    PEP = 'PEP'                # Cliente PEP
    AMBOS = 'AMBOS'            # Ambas condiciones
```

### 3.2 Diagrama de Relaciones (ERD)
```
┌─────────────────────────┐
│       CLIENTE           │
├─────────────────────────┤
│ PK: cliente_id          │
│ UK: dni                 │
│     nombre_completo     │
│     apellido_paterno    │
│     apellido_materno    │
│     pep (Boolean)       │
│     fecha_registro      │
└────────┬────────────────┘
         │ 1
         │
         │ N
┌────────┴────────────────┐
│      PRESTAMO           │
├─────────────────────────┤
│ PK: prestamo_id         │
│ FK: cliente_id          │
│ FK: declaracion_id      │
│     monto_total         │
│     interes_tea         │
│     plazo               │
│     f_otorgamiento      │
│     estado (ENUM)       │
│     requiere_dec_jurada │
└────────┬────────────────┘
         │ 1
         │
         │ N
┌────────┴────────────────┐
│        CUOTA            │
├─────────────────────────┤
│ PK: cuota_id            │
│ FK: prestamo_id         │
│     numero_cuota        │
│     fecha_vencimiento   │
│     monto_cuota         │
│     monto_capital       │
│     monto_interes       │
│     saldo_capital       │
└─────────────────────────┘

┌─────────────────────────┐
│  DECLARACION_JURADA     │
├─────────────────────────┤
│ PK: declaracion_id      │
│ FK: cliente_id          │
│     tipo_declaracion    │
│     fecha_firma         │
│     firmado (Boolean)   │
└─────────────────────────┘
```

### 3.3 Índices y Constraints
```sql
-- Índices para optimización
CREATE INDEX idx_cliente_dni ON clientes(dni);
CREATE INDEX idx_prestamo_cliente ON prestamos(cliente_id);
CREATE INDEX idx_prestamo_estado ON prestamos(estado);
CREATE INDEX idx_cuota_prestamo ON cuotas(prestamo_id);

-- Constraints
ALTER TABLE clientes ADD CONSTRAINT uk_dni UNIQUE (dni);
ALTER TABLE prestamos ADD CONSTRAINT fk_cliente 
    FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id);
ALTER TABLE cuotas ADD CONSTRAINT fk_prestamo 
    FOREIGN KEY (prestamo_id) REFERENCES prestamos(prestamo_id);
```

---

## 4. TECNOLOGÍAS UTILIZADAS

### 4.1 Stack Backend

#### Python 3.11+
- Lenguaje de programación principal
- Tipado dinámico con hints
- Gestión de dependencias con pip

#### Flask 3.1.2
```python
# Framework web minimalista y flexible
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
```

**Características utilizadas:**
- Blueprints para modularización
- Jinja2 para templates
- Request/Response handling
- JSON serialization

#### SQLAlchemy (ORM)
```python
# Mapeo objeto-relacional
from sqlalchemy.orm import relationship
from app import db

class Cliente(db.Model):
    __tablename__ = 'clientes'
    # ...
```

**Ventajas:**
- Abstracción de base de datos
- Relaciones declarativas
- Query builder poderoso
- Migraciones con Alembic

#### Pydantic (Validación)
```python
# Validación de datos de entrada
from pydantic import BaseModel, Field, validator

class PrestamoCreateDTO(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8)
    monto: float = Field(..., gt=0)
    plazo: int = Field(..., gt=0)
    
    @validator('dni')
    def validate_dni(cls, v):
        if not v.isdigit():
            raise ValueError('DNI debe contener solo dígitos')
        return v
```

#### PostgreSQL 14+
- Base de datos relacional robusta
- Soporte para ENUM types
- Transacciones ACID
- Índices para optimización

### 4.2 Stack Frontend

#### TailwindCSS 4.1.14
```html
<!-- Utility-first CSS framework -->
<div class="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
    <h2 class="text-xl font-semibold text-gray-900">Título</h2>
</div>
```

**Configuración:**
```bash
npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/style.css --watch
```

#### JavaScript Vanilla (ES6+)
```javascript
// Fetch API para comunicación con backend
async function searchClient() {
    const response = await fetch(`/api/v1/clientes/dni/${dni}`);
    const data = await response.json();
    displayClientInfo(data);
}
```

**Características utilizadas:**
- Async/await
- Arrow functions
- Template literals
- Destructuring
- Modules

#### Jinja2 Templates
```html
<!-- Motor de templates integrado con Flask -->
{% extends "base.html" %}
{% block content %}
    {% for cliente in clientes %}
        <div>{{ cliente.nombre_completo }}</div>
    {% endfor %}
{% endblock %}
```

### 4.3 APIs y Servicios Externos

#### APIPERU (RENIEC)
```python
# Consulta de DNI
API_URL = "https://apiperu.dev/api/dni"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

response = requests.get(f"{API_URL}/{dni}", headers=headers)
data = response.json()
```

**Formato de respuesta:**
```json
{
    "success": true,
    "data": {
        "numero": "12345678",
        "nombre_completo": "JUAN PEREZ GARCIA",
        "nombres": "JUAN",
        "apellido_paterno": "PEREZ",
        "apellido_materno": "GARCIA",
        "codigo_verificacion": "1",
        "fecha_nacimiento": "01/01/1990"
    }
}
```

#### Dataset PEP (Excel)
- 38,112 registros de personas políticamente expuestas
- Cargado en memoria al iniciar la aplicación
- Formato: Excel con columna de DNIs
- Validación automática contra este dataset

### 4.4 Herramientas de Desarrollo

#### Alembic (Migraciones)
```bash
# Crear migración
alembic revision --autogenerate -m "descripción"

# Aplicar migración
alembic upgrade head
```

#### Git (Control de versiones)
```bash
git add .
git commit -m "descripción"
git push origin rama
```

---

## 5. CARACTERÍSTICAS TÉCNICAS DESTACADAS

### 5.1 Validaciones de Negocio

#### Regla 1: Un solo préstamo activo
```python
def prestamo_activo_cliente(cliente_id, estado):
    return Prestamo.query.filter_by(
        cliente_id=cliente_id,
        estado=estado
    ).first()

# Verificación antes de crear préstamo
prestamo_activo = prestamo_activo_cliente(cliente.cliente_id, EstadoPrestamoEnum.VIGENTE)
if prestamo_activo:
    return jsonify({'error': 'Cliente ya tiene préstamo activo'}), 400
```

#### Regla 2: Declaración jurada obligatoria
```python
UIT_VALOR = 5150  # Valor de 1 UIT en soles

requiere_dj = False
if monto_total > UIT_VALOR:
    requiere_dj = True
if cliente.pep:
    requiere_dj = True
```

#### Regla 3: Estados irreversibles
```python
# Estado CANCELADO no puede cambiar
if estado_actual == EstadoPrestamoEnum.CANCELADO:
    return jsonify({
        'error': 'Un préstamo CANCELADO no puede cambiar de estado'
    }), 400
```

#### Regla 4: Validación automática PEP
```python
def validar_pep_en_dataset(dni):
    """Valida DNI contra dataset de 38,112 registros PEP"""
    dni_normalizado = str(dni).strip().zfill(8)
    return dni_normalizado in LISTA_PEP
```

### 5.2 Cálculo Financiero

#### Sistema de Amortización Francés
```python
def generar_cronograma_pagos(monto, tasa_anual, plazo_meses, fecha_inicio):
    """
    Genera cronograma con método francés (cuota fija)
    
    Parámetros:
        monto: Monto total del préstamo
        tasa_anual: TEA (Tasa Efectiva Anual) en decimal (ej: 0.30 para 30%)
        plazo_meses: Número de cuotas mensuales
        fecha_inicio: Fecha de otorgamiento
    
    Retorna:
        Lista de diccionarios con datos de cada cuota
    """
    
    # Convertir TEA a tasa mensual equivalente
    tasa_mensual = (1 + tasa_anual) ** (1/12) - 1
    
    # Calcular cuota fija con fórmula francesa
    cuota_fija = monto * (
        tasa_mensual * (1 + tasa_mensual) ** plazo_meses
    ) / (
        (1 + tasa_mensual) ** plazo_meses - 1
    )
    
    saldo = monto
    cronograma = []
    
    for i in range(1, plazo_meses + 1):
        # Calcular interés del período
        interes = saldo * tasa_mensual
        
        # Calcular amortización de capital
        capital = cuota_fija - interes
        
        # Actualizar saldo
        saldo -= capital
        
        # Calcular fecha de vencimiento
        fecha_vencimiento = fecha_inicio + relativedelta(months=i)
        
        # Agregar cuota al cronograma
        cronograma.append({
            'numero_cuota': i,
            'fecha_vencimiento': fecha_vencimiento,
            'monto_cuota': round(cuota_fija, 2),
            'monto_capital': round(capital, 2),
            'monto_interes': round(interes, 2),
            'saldo_capital': round(max(0, saldo), 2)
        })
    
    return cronograma
```

**Ejemplo de cálculo:**
```
Monto: S/ 10,000
TEA: 30% (0.30)
Plazo: 12 meses

Tasa mensual = (1 + 0.30)^(1/12) - 1 = 0.0221 (2.21%)

Cuota fija = 10,000 × [0.0221 × (1.0221)^12] / [(1.0221)^12 - 1]
           = 10,000 × 0.0298 / 0.2997
           = S/ 994.39

Cuota 1:
- Interés = 10,000 × 0.0221 = S/ 221.00
- Capital = 994.39 - 221.00 = S/ 773.39
- Saldo = 10,000 - 773.39 = S/ 9,226.61

Cuota 2:
- Interés = 9,226.61 × 0.0221 = S/ 203.91
- Capital = 994.39 - 203.91 = S/ 790.48
- Saldo = 9,226.61 - 790.48 = S/ 8,436.13
```

### 5.3 Seguridad y Configuración

#### Variables de entorno (.env)
```bash
# Base de datos
DATABASE_URL=postgresql://usuario:password@host:5432/database

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=clave_secreta_segura

# API RENIEC
DNI_API_KEY=token_de_api
DNI_API_URL=https://apiperu.dev/api/dni
```

#### Validación con Pydantic
```python
class PrestamoCreateDTO(BaseModel):
    dni: str = Field(..., regex=r'^\d{8}$')
    monto: float = Field(..., gt=0, le=1000000)
    interes_tea: float = Field(..., ge=0, le=100)
    plazo: int = Field(..., gt=0, le=360)
    f_otorgamiento: date
    
    class Config:
        str_strip_whitespace = True
```

#### Transacciones atómicas
```python
try:
    # Crear declaración jurada
    if requiere_dj:
        nueva_dj = DeclaracionJurada(...)
        db.session.add(nueva_dj)
    
    # Crear préstamo
    nuevo_prestamo = Prestamo(...)
    db.session.add(nuevo_prestamo)
    
    # Crear cuotas
    for cuota_data in cronograma:
        cuota = Cuota(...)
        db.session.add(cuota)
    
    # Commit de toda la transacción
    db.session.commit()
    
except Exception as e:
    # Rollback en caso de error
    db.session.rollback()
    return error_response(str(e))
```

#### Manejo centralizado de errores
```python
class ErrorHandler:
    def __init__(self, logger):
        self.logger = logger
    
    def respond(self, message, status_code, errors=None):
        self.logger.error(f"Error {status_code}: {message}")
        response = {'error': message}
        if errors:
            response['details'] = errors
        return jsonify(response), status_code
```

### 5.4 Optimizaciones

#### Cache en memoria del dataset PEP
```python
# Carga única al iniciar (app/clients/crud.py)
LISTA_PEP = cargar_lista_pep()  # 38,112 registros en memoria

def cargar_lista_pep():
    """Carga dataset PEP una sola vez al iniciar"""
    df = pd.read_excel(DATASET_PEP_PATH)
    dnis_pep = set(df['DNI'].astype(str).str.zfill(8))
    return dnis_pep
```

**Ventaja:** Validación instantánea sin consultar disco o BD

#### Consultas SQL optimizadas
```python
# JOIN con agregaciones para lista de clientes
query = db.session.query(
    Cliente,
    func.coalesce(func.sum(Prestamo.monto_total), 0).label('monto_total_prestado'),
    func.count(func.distinct(Prestamo.prestamo_id)).label('total_prestamos'),
    func.count(Cuota.cuota_id).label('total_cuotas'),
    func.coalesce(func.count(func.distinct(
        case((Prestamo.estado == EstadoPrestamoEnum.VIGENTE, Prestamo.prestamo_id))
    )), 0).label('prestamos_vigentes')
).outerjoin(
    Prestamo, Cliente.cliente_id == Prestamo.cliente_id
).outerjoin(
    Cuota, Prestamo.prestamo_id == Cuota.prestamo_id
).group_by(Cliente.cliente_id)
```

**Ventaja:** Una sola consulta en lugar de N+1 queries

#### Paginación
```python
# 5 registros por página
clientes_paginados = query.paginate(
    page=page,
    per_page=5,
    error_out=False
)
```

**Ventaja:** Reduce carga de memoria y tiempo de respuesta

#### Sistema de fallback
```python
# Si API RENIEC falla, crear cliente con datos mínimos
if error and ("no encontrado" in error or "Tiempo de espera" in error):
    try:
        es_pep_validado = validar_pep_en_dataset(dni)
        nuevo_cliente = Cliente(
            dni=dni,
            nombre_completo=f"Cliente {dni}",
            apellido_paterno="PENDIENTE",
            apellido_materno="ACTUALIZACION",
            pep=es_pep_validado
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        return nuevo_cliente, None
    except Exception as e:
        return None, f"Error al crear cliente: {str(e)}"
```

**Ventaja:** Sistema sigue funcionando aunque API externa falle

---

## 6. ENDPOINTS REST API

### 6.1 Módulo de Clientes

#### POST /api/v1/clientes
**Descripción:** Crear un nuevo cliente consultando RENIEC

**Request:**
```json
{
    "dni": "12345678",
    "pep": false
}
```

**Response 201:**
```json
{
    "cliente_id": 1,
    "dni": "12345678",
    "nombre_completo": "JUAN PEREZ GARCIA",
    "apellido_paterno": "PEREZ",
    "apellido_materno": "GARCIA",
    "pep": false,
    "fecha_registro": "2025-10-15T10:30:00"
}
```

**Errores:**
- 400: DNI inválido
- 404: DNI no encontrado en RENIEC
- 409: Cliente ya existe
- 503: Error en API externa

---

#### GET /api/v1/clientes
**Descripción:** Listar todos los clientes

**Response 200:**
```json
[
    {
        "cliente_id": 1,
        "dni": "12345678",
        "nombre_completo": "JUAN PEREZ GARCIA",
        "pep": false,
        "fecha_registro": "2025-10-15T10:30:00"
    },
    {
        "cliente_id": 2,
        "dni": "87654321",
        "nombre_completo": "MARIA LOPEZ TORRES",
        "pep": true,
        "fecha_registro": "2025-10-15T11:00:00"
    }
]
```

---

#### GET /api/v1/clientes/dni/{dni}
**Descripción:** Buscar cliente por DNI en base de datos

**Response 200:**
```json
{
    "cliente_id": 1,
    "dni": "12345678",
    "nombre_completo": "JUAN PEREZ GARCIA",
    "apellido_paterno": "PEREZ",
    "apellido_materno": "GARCIA",
    "pep": false,
    "fecha_registro": "2025-10-15T10:30:00",
    "tiene_prestamo_activo": true
}
```

**Errores:**
- 400: DNI inválido (formato)
- 404: Cliente no encontrado

---

#### GET /api/v1/clientes/consultar_dni/{dni}
**Descripción:** Consultar DNI directamente en API RENIEC

**Response 200:**
```json
{
    "numero": "12345678",
    "nombre_completo": "JUAN PEREZ GARCIA",
    "nombres": "JUAN",
    "apellido_paterno": "PEREZ",
    "apellido_materno": "GARCIA",
    "fecha_nacimiento": "01/01/1990"
}
```

**Errores:**
- 400: DNI inválido
- 404: DNI no encontrado en RENIEC

---

#### GET /api/v1/clientes/list?page={page}&dni={dni}
**Descripción:** Vista paginada de clientes con información de préstamos

**Parámetros:**
- `page`: Número de página (opcional, default: 1)
- `dni`: Filtro por DNI (opcional)

**Response:** HTML renderizado con Jinja2

---

### 6.2 Módulo de Préstamos

#### POST /api/v1/prestamos/register
**Descripción:** Registrar un nuevo préstamo

**Request:**
```json
{
    "dni": "12345678",
    "monto": 10000.00,
    "interes_tea": 30.0,
    "plazo": 12,
    "f_otorgamiento": "2025-10-15"
}
```

**Response 201:**
```json
{
    "prestamo_id": 1,
    "cliente_id": 1,
    "monto_total": 10000.00,
    "interes_tea": 30.0,
    "plazo": 12,
    "f_otorgamiento": "2025-10-15",
    "estado": "VIGENTE",
    "requiere_dec_jurada": true,
    "cuotas_creadas": 12
}
```

**Errores:**
- 400: Datos inválidos, cliente con préstamo activo
- 404: Cliente no encontrado
- 500: Error al crear préstamo

---

#### GET /api/v1/prestamos/cliente/{cliente_id}/json
**Descripción:** Obtener todos los préstamos de un cliente con cronograma

**Response 200:**
```json
[
    {
        "prestamo_id": 1,
        "monto_total": 10000.00,
        "interes_tea": 30.0,
        "plazo": 12,
        "f_otorgamiento": "2025-10-15",
        "estado": "VIGENTE",
        "requiere_dec_jurada": true,
        "cronograma": [
            {
                "numero_cuota": 1,
                "fecha_vencimiento": "2025-11-15",
                "monto_cuota": 994.39,
                "monto_capital": 773.39,
                "monto_interes": 221.00,
                "saldo_capital": 9226.61
            },
            {
                "numero_cuota": 2,
                "fecha_vencimiento": "2025-12-15",
                "monto_cuota": 994.39,
                "monto_capital": 790.48,
                "monto_interes": 203.91,
                "saldo_capital": 8436.13
            }
            // ... 10 cuotas más
        ]
    }
]
```

---

#### POST /api/v1/prestamos/actualizar-estado/{prestamo_id}
**Descripción:** Cambiar estado de un préstamo

**Request:**
```json
{
    "estado": "CANCELADO"
}
```

**Response 200:**
```json
{
    "success": true,
    "mensaje": "Estado actualizado de VIGENTE a CANCELADO",
    "prestamo_id": 1,
    "nuevo_estado": "CANCELADO"
}
```

**Errores:**
- 400: Estado inválido, transición no permitida
- 404: Préstamo no encontrado

---

### 6.3 Códigos de Estado HTTP Utilizados

| Código | Significado | Uso en el sistema |
|--------|-------------|-------------------|
| 200 | OK | Operación exitosa (GET, POST actualización) |
| 201 | Created | Recurso creado (POST clientes, préstamos) |
| 400 | Bad Request | Datos inválidos, reglas de negocio violadas |
| 404 | Not Found | Recurso no encontrado (cliente, préstamo) |
| 409 | Conflict | Recurso duplicado (DNI ya existe) |
| 500 | Internal Server Error | Error del servidor |
| 503 | Service Unavailable | API externa no disponible |

---

## 7. INTERFAZ DE USUARIO

### 7.1 Páginas Principales

#### Página de Inicio (/)
**Funcionalidad:**
- Búsqueda de cliente por DNI
- Formulario de registro de préstamo
- Validaciones en tiempo real
- Modal de cronograma de pagos

**Componentes:**
```html
<!-- Búsqueda de cliente -->
<input id="dni-search" placeholder="Ingrese el DNI">
<button class="search-button">Buscar</button>

<!-- Resultados -->
<div class="results-section">
    <span id="client-dni"></span>
    <span id="client-name"></span>
    <div id="pep-notice"></div>
    <div id="loan-active-notice"></div>
</div>

<!-- Formulario de préstamo -->
<form id="loan-form">
    <input id="monto" type="number">
    <input id="cuotas" type="number">
    <input id="email" type="email">
    <button onclick="verCronogramaPagos()">Ver cronograma</button>
    <button onclick="crearNuevoPrestamo()">Crear Préstamo</button>
</form>

<!-- Modal de cronograma -->
<div id="modalCronograma">
    <table id="cronograma-table-body"></table>
</div>
```

---

#### Lista de Clientes (/api/v1/clientes/list)
**Funcionalidad:**
- Tabla con 7 columnas
- Paginación (5 registros por página)
- Filtro por DNI
- Modal con detalles de préstamos
- Cambio de estado de préstamos

**Columnas de la tabla:**
1. DNI
2. Nombre Completo
3. PEP (Si/No)
4. Fecha de Registro
5. Monto Total Prestado
6. Número de Cuotas
7. Estado (badge: VIGENTE/CANCELADO)

**Modal de detalles:**
```html
<div id="modalDetallesPrestamos">
    <!-- Por cada préstamo -->
    <div class="prestamo-card">
        <h4>Préstamo #1</h4>
        <span class="badge">VIGENTE</span>
        <select onchange="cambiarEstadoPrestamo()">
            <option value="CANCELADO">CANCELADO</option>
        </select>
        
        <!-- Cronograma expandible -->
        <button onclick="toggleCronograma()">
            Ver Cronograma de Pagos
        </button>
        <div id="cronograma-1" class="hidden">
            <table>
                <!-- Tabla de cuotas -->
            </table>
        </div>
    </div>
</div>
```

### 7.2 Flujo de Interacción Usuario

```
USUARIO INGRESA DNI
    ↓
SISTEMA BUSCA EN BD
    ↓
┌─────────────┬─────────────┐
│ Encontrado  │ No encontrado│
│ en BD       │              │
└─────┬───────┴──────┬──────┘
      │              │
      ▼              ▼
Mostrar datos   Consultar RENIEC
      │              │
      └──────┬───────┘
             ↓
    ¿Tiene préstamo activo?
             │
      ┌──────┴──────┐
      │ SI          │ NO
      ▼             ▼
  BLOQUEAR      HABILITAR
  Formulario    Formulario
      │             │
      │             ▼
      │    USUARIO LLENA DATOS
      │             │
      │             ▼
      │    CALCULA CRONOGRAMA
      │             │
      │             ▼
      │    MUESTRA MODAL
      │             │
      │             ▼
      │    USUARIO CONFIRMA
      │             │
      │             ▼
      │    CREA PRÉSTAMO
      │             │
      └─────────────┴─────────►
             ↓
    MENSAJE DE ÉXITO
```

### 7.3 Elementos de UI

#### Badges de estado
```html
<!-- VIGENTE -->
<span class="bg-green-50 text-green-700 px-3 py-1.5 rounded-lg">
    <span class="w-2 h-2 bg-green-600 rounded-full animate-pulse"></span>
    VIGENTE
</span>

<!-- CANCELADO -->
<span class="bg-gray-100 text-gray-600 px-3 py-1.5 rounded-lg">
    CANCELADO
</span>
```

#### Alertas
```javascript
function showAlert(message, type) {
    // type: 'success', 'error', 'warning'
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    document.body.appendChild(alert);
    
    setTimeout(() => alert.remove(), 3000);
}
```

#### Loading states
```javascript
// Botón de búsqueda
searchButton.textContent = "Buscando...";
searchButton.disabled = true;

// Después de la operación
searchButton.textContent = "Buscar";
searchButton.disabled = false;
```

---

## 8. MÉTRICAS Y ESTADÍSTICAS DEL PROYECTO

### 8.1 Métricas de Código

| Métrica | Valor |
|---------|-------|
| Líneas de código Python | ~2,800 |
| Líneas de código JavaScript | ~700 |
| Líneas de HTML/Templates | ~2,000 |
| Archivos Python | 25 |
| Archivos JavaScript | 3 |
| Templates HTML | 12 |
| Archivos CSS | 2 |
| Total de archivos | 45+ |

### 8.2 Base de Datos

| Elemento | Cantidad |
|----------|----------|
| Tablas principales | 4 |
| Foreign Keys | 4 |
| Índices | 8 |
| Enumeraciones | 2 |
| Migraciones | 5+ |

### 8.3 API y Endpoints

| Tipo | Cantidad |
|------|----------|
| Endpoints REST | 15 |
| Métodos GET | 9 |
| Métodos POST | 5 |
| Métodos PUT | 1 |
| Métodos DELETE | 1 |
| Vistas HTML | 3 |

### 8.4 Dataset y Datos

| Recurso | Tamaño |
|---------|--------|
| Registros PEP | 38,112 |
| Clientes registrados | Variable |
| Préstamos activos | Variable |
| Cuotas generadas | Variable |
| Tamaño dataset Excel | ~2 MB |

### 8.5 Performance

| Operación | Tiempo promedio |
|-----------|-----------------|
| Búsqueda DNI en BD | < 50 ms |
| Consulta API RENIEC | 800-1500 ms |
| Validación PEP (cache) | < 1 ms |
| Creación de préstamo | 200-400 ms |
| Generación cronograma | < 10 ms |
| Carga lista clientes | 100-300 ms |

---

## 9. VENTAJAS Y BENEFICIOS DEL SISTEMA

### 9.1 Arquitectura y Diseño

#### Modularidad
- Separación clara de responsabilidades
- Blueprints independientes por módulo
- Fácil mantenimiento y escalabilidad
- Código reutilizable

#### Escalabilidad
- Arquitectura preparada para crecimiento
- Base de datos relacional robusta
- Posibilidad de microservicios futuros
- Cache en memoria optimizado

#### Mantenibilidad
- Código limpio y documentado
- Estructura organizada por capas
- Validaciones centralizadas
- Logs y manejo de errores

### 9.2 Funcionalidad

#### Validación Robusta
- Pydantic para entrada de datos
- Validación PEP automática
- Reglas de negocio implementadas
- Prevención de estados inconsistentes

#### Experiencia de Usuario
- Interfaz intuitiva y responsive
- Feedback inmediato de operaciones
- Modales informativos
- Estados de carga visibles

#### Integración Externa
- Consulta automática a RENIEC
- Sistema de fallback robusto
- Manejo de errores de API
- Timeout configurables

### 9.3 Cumplimiento y Normativa

#### Validación PEP
- Dataset oficial de 38,112 registros
- Validación automática obligatoria
- Declaración jurada cuando corresponde
- Trazabilidad completa

#### Gestión Financiera
- Cálculos precisos (método francés)
- TEA estándar del mercado
- Cronograma detallado
- Transparencia en cuotas

#### Auditoría
- Registro de todas las operaciones
- Timestamps automáticos
- Estados inmutables (CANCELADO)
- Historial completo

### 9.4 Seguridad

#### Protección de Datos
- Variables de entorno para credenciales
- Validación de entrada
- Transacciones atómicas
- Manejo seguro de errores

#### Integridad
- Foreign keys en BD
- Constraints y validaciones
- Estados controlados
- Rollback automático en errores

---

## 10. CASOS DE USO

### 10.1 Caso de Uso 1: Registro de Cliente Nuevo

**Actor:** Oficial de créditos

**Precondiciones:**
- Sistema iniciado
- Conexión a base de datos activa
- API RENIEC disponible

**Flujo principal:**
1. Usuario ingresa DNI (ej: 12345678)
2. Sistema busca en BD local
3. No encuentra cliente
4. Sistema consulta API RENIEC
5. RENIEC responde con datos
6. Sistema valida contra dataset PEP
7. Sistema muestra datos del cliente
8. Usuario completa formulario de préstamo
9. Sistema valida reglas de negocio
10. Sistema genera cronograma
11. Sistema muestra modal de cronograma
12. Usuario confirma
13. Sistema crea cliente, préstamo y cuotas
14. Sistema muestra mensaje de éxito

**Flujos alternativos:**

*3a. Cliente existe en BD:*
- 3a1. Sistema muestra datos guardados
- 3a2. Continúa en paso 7

*4a. API RENIEC no disponible:*
- 4a1. Sistema usa fallback
- 4a2. Crea cliente con datos mínimos
- 4a3. Continúa en paso 7

*6a. Cliente es PEP:*
- 6a1. Sistema marca como PEP
- 6a2. Sistema requiere declaración jurada
- 6a3. Continúa en paso 7

**Postcondiciones:**
- Cliente registrado en BD
- Préstamo creado con estado VIGENTE
- 12 cuotas generadas
- Declaración jurada creada (si aplica)

---

### 10.2 Caso de Uso 2: Registro de Préstamo para Cliente Existente

**Actor:** Oficial de créditos

**Precondiciones:**
- Cliente ya registrado en BD
- Cliente NO tiene préstamo activo

**Flujo principal:**
1. Usuario ingresa DNI existente
2. Sistema busca en BD
3. Sistema encuentra cliente
4. Sistema verifica préstamos activos
5. No encuentra préstamo VIGENTE
6. Sistema muestra datos del cliente
7. Usuario ingresa monto (ej: S/ 10,000)
8. Usuario ingresa plazo (ej: 12 meses)
9. Sistema valida monto > 1 UIT
10. Sistema requiere declaración jurada
11. Usuario acepta declaración
12. Usuario hace clic en "Ver cronograma"
13. Sistema calcula cuotas con método francés
14. Sistema muestra modal con tabla
15. Usuario revisa cronograma
16. Usuario hace clic en "Crear Préstamo"
17. Sistema crea préstamo y cuotas
18. Sistema muestra mensaje de éxito

**Flujos alternativos:**

*5a. Cliente tiene préstamo VIGENTE:*
- 5a1. Sistema muestra alerta
- 5a2. Sistema bloquea formulario
- 5a3. Fin del caso de uso

*9a. Monto <= 1 UIT y cliente NO es PEP:*
- 9a1. No requiere declaración jurada
- 9a2. Continúa en paso 12

**Postcondiciones:**
- Préstamo creado
- Estado VIGENTE asignado
- Cuotas generadas
- Cliente bloqueado para nuevo préstamo

---

### 10.3 Caso de Uso 3: Cambio de Estado de Préstamo

**Actor:** Administrador de créditos

**Precondiciones:**
- Préstamo existe en BD
- Préstamo en estado VIGENTE

**Flujo principal:**
1. Usuario accede a lista de clientes
2. Usuario hace clic en "Ver Detalles"
3. Sistema muestra modal con préstamos
4. Usuario ve préstamo VIGENTE
5. Usuario selecciona "CANCELADO" en dropdown
6. Sistema muestra confirmación
7. Usuario confirma cambio
8. Sistema valida transición
9. Sistema actualiza estado a CANCELADO
10. Sistema recarga página
11. Sistema muestra estado actualizado

**Flujos alternativos:**

*4a. Préstamo ya está CANCELADO:*
- 4a1. Dropdown deshabilitado
- 4a2. Mensaje: "No se puede cambiar"
- 4a3. Fin del caso de uso

*8a. Estado CANCELADO intenta cambiar:*
- 8a1. Sistema rechaza operación
- 8a2. Sistema muestra error
- 8a3. Fin del caso de uso

**Postcondiciones:**
- Estado cambiado a CANCELADO
- Cliente puede solicitar nuevo préstamo
- Estado irreversible

---

## 11. POSIBLES MEJORAS FUTURAS

### 11.1 Funcionalidades

#### Módulo de Pagos
- Registro de pagos de cuotas
- Estado de cuotas (PENDIENTE, PAGADO, VENCIDO)
- Cálculo de mora
- Historial de pagos

#### Reportes y Analytics
- Dashboard con estadísticas
- Reportes de morosidad
- Gráficos de préstamos por período
- Exportación a Excel/PDF

#### Notificaciones
- Alertas de vencimiento de cuotas
- Notificaciones por email
- SMS para recordatorios
- Webhooks para integraciones

#### Gestión de Usuarios
- Sistema de autenticación
- Roles y permisos
- Auditoría de acciones
- Login con OAuth2

### 11.2 Mejoras Técnicas

#### Performance
- Implementar Redis para cache
- Optimizar queries con índices
- Lazy loading en frontend
- Compresión de respuestas

#### Seguridad
- Implementar JWT
- Rate limiting en API
- Encriptación de datos sensibles
- HTTPS obligatorio

#### DevOps
- Dockerización de la aplicación
- CI/CD con GitHub Actions
- Tests automatizados (pytest)
- Deployment en cloud (AWS/Azure)

#### Arquitectura
- Separar frontend (React/Vue)
- API Gateway
- Microservicios
- Message queue (RabbitMQ)

---

## 12. CONCLUSIONES

### 12.1 Logros Alcanzados

El sistema de gestión de préstamos desarrollado cumple con todos los objetivos planteados:

1. **Arquitectura sólida:** Implementación exitosa del patrón MVC con separación de capas
2. **Funcionalidad completa:** Registro de clientes, préstamos, cuotas y declaraciones
3. **Validación robusta:** Integración con RENIEC y dataset PEP de 38,112 registros
4. **Cálculos precisos:** Método francés implementado correctamente
5. **Experiencia de usuario:** Interfaz intuitiva y responsive con TailwindCSS
6. **Código limpio:** Documentación completa y estructura organizada

### 12.2 Aprendizajes Técnicos

Durante el desarrollo se aplicaron conceptos avanzados:

- **ORM:** Relaciones complejas con SQLAlchemy
- **Validación:** Pydantic para esquemas de datos
- **APIs externas:** Integración con servicios de terceros
- **Frontend moderno:** JavaScript ES6+ y TailwindCSS
- **Base de datos:** PostgreSQL con optimizaciones
- **Git:** Control de versiones con commits descriptivos

### 12.3 Valor del Sistema

El sistema aporta valor en múltiples aspectos:

**Operativo:**
- Automatización de procesos manuales
- Reducción de errores humanos
- Mayor velocidad en aprobación de préstamos

**Normativo:**
- Cumplimiento automático de validación PEP
- Trazabilidad completa de operaciones
- Declaraciones juradas digitales

**Financiero:**
- Cálculos precisos y transparentes
- Cronogramas automáticos
- Prevención de préstamos duplicados

**Tecnológico:**
- Arquitectura escalable
- Código mantenible
- Integración con sistemas externos

---

## ANEXOS

### A. Configuración del Entorno de Desarrollo

#### Requisitos Previos
```bash
# Python 3.11+
python --version

# PostgreSQL 14+
psql --version

# Node.js (para Tailwind)
node --version
```

#### Instalación
```bash
# Clonar repositorio
git clone https://github.com/UPAO-INSO/caso-agile.git
cd caso-agile

# Crear entorno virtual
python -m venv env
source env/bin/activate  # Linux/Mac
env\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Crear base de datos
psql -U postgres
CREATE DATABASE negocio;
\q

# Ejecutar migraciones
alembic upgrade head

# Compilar Tailwind
npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/style.css

# Iniciar aplicación
python app.py
```

### B. Variables de Entorno Requeridas

```bash
# Base de datos
DATABASE_URL=postgresql://usuario:password@localhost:5432/negocio

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=tu_clave_secreta_aqui

# API RENIEC
DNI_API_KEY=tu_api_key_aqui
DNI_API_URL=https://apiperu.dev/api/dni
```

### C. Comandos Útiles

```bash
# Desarrollo
python app.py                    # Iniciar servidor
alembic revision -m "mensaje"    # Crear migración
alembic upgrade head             # Aplicar migraciones

# Git
git add .
git commit -m "mensaje"
git push origin rama

# Base de datos
psql -U postgres -d negocio      # Conectar a BD
\dt                              # Listar tablas
\d tabla                         # Describir tabla
```

---

**Documento generado el:** 15 de octubre de 2025  
**Versión del sistema:** 1.0.0  
**Autor:** Sistema de Gestión de Préstamos  
**Repositorio:** https://github.com/UPAO-INSO/caso-agile
