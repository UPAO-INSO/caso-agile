# 🏦 Sistema de Préstamos Bancarios - Flask App

> **Versión refactorizada**: Application Factory Pattern + Service Layer  
> **Stack**: Flask 3.1 + SQLAlchemy 2.0 + Pydantic 2.0 + TailwindCSS

Aplicación web para gestión de préstamos bancarios con validación de PEP (Personas Expuestas Políticamente), cálculos financieros automáticos y generación de cronogramas de pago.

---

## ✨ Características

- ✅ **Registro de clientes** con validación DNI/RENIEC
- ✅ **Gestión de préstamos** con sistema de amortización francés
- ✅ **Validación PEP** automática contra dataset oficial
- ✅ **Declaraciones juradas** para montos > UIT o clientes PEP
- ✅ **Cronogramas de pago** con cálculo automático de cuotas
- ✅ **Envío de emails** con PDFs adjuntos
- ✅ **API REST** + vistas HTML
- ✅ **Arquitectura modular** con Service Layer Pattern

---

## 🏗️ Arquitectura

### Application Factory Pattern

```python
from app import create_app

app = create_app('development')  # o 'production', 'testing'
```

### Service Layer

```
Controllers (routes.py)     → Solo manejan HTTP
    ↓ delegan a
Services (services/)        → Lógica de negocio
    ↓ usan
Repositories (crud.py)      → Acceso a datos
    ↓ usan
Models (model/)             → Definición de datos
```

### Estructura del Proyecto

```
app/
├── __init__.py             # Application Factory
├── extensions.py           # Flask extensions (db, mail, migrate)
├── config.py              # Configuration classes
├── routes.py              # Root routes
├── services/              # ⭐ Business logic
│   ├── email_service.py
│   ├── pdf_service.py
│   ├── financial_service.py
│   ├── pep_service.py
│   └── prestamo_service.py
├── clients/               # Módulo de clientes
│   ├── routes.py
│   ├── crud.py
│   └── model/
├── prestamos/             # Módulo de préstamos
│   ├── routes.py
│   ├── crud.py
│   ├── schemas.py
│   └── model/
├── cuotas/                # Módulo de cuotas
├── declaraciones/         # Módulo de declaraciones juradas
├── common/                # Utilidades compartidas
├── static/                # CSS, JS, assets
└── templates/             # Jinja2 templates

instance/                   # ⚠️ Configuración sensible (no versionada)
└── config.py
```

---

## 🛠️ Tecnologías

### Backend

- **Python 3.10+**
- **Flask 3.1** — Framework web
- **SQLAlchemy 2.0** — ORM
- **Flask-Migrate** — Migraciones de DB
- **Pydantic 2.0** — Validación de datos
- **Flask-Mail** — Envío de emails
- **ReportLab** — Generación de PDFs
- **Pandas** — Procesamiento de datasets

### Frontend

- **Jinja2** — Motor de plantillas
- **TailwindCSS** — Framework CSS
- **Alpine.js** — Interactividad ligera

### Database

- **PostgreSQL** — Base de datos principal

---

## 📋 Requisitos

- [Python 3.10+](https://www.python.org/downloads/)
- [PostgreSQL 13+](https://www.postgresql.org/download/)
- [Docker & Docker Compose](https://www.docker.com/get-started/) (opcional, recomendado)
- [Node.js (v18+)](https://nodejs.org/)
- [npm](https://www.npmjs.com/) (instalado junto con Node)
- [Git](https://git-scm.com/)

---

## 🗄️ Base de Datos y Migraciones

### Para Nuevos Desarrolladores

#### Opción 1: Docker (Recomendado)

```bash
# Las migraciones se aplican automáticamente
docker-compose up --build
```

#### Opción 2: PostgreSQL Local

```bash
# 1. Crear base de datos
psql -U postgres
CREATE DATABASE nombre_bd;
\q

# 2. Configurar .env con DATABASE_URL
# 3. Aplicar migraciones
flask db upgrade
```

### Trabajar con Migraciones

```bash
# Ver estado actual
flask db current

# Crear nueva migración (después de modificar modelos)
flask db migrate -m "descripción del cambio"

# Aplicar migraciones pendientes
flask db upgrade

# Revertir última migración
flask db downgrade -1

# Ver historial completo
flask db history
```

### Reset de Base de Datos (Solo Desarrollo)

```bash
# Windows PowerShell
.\reset_db.ps1

# Linux/Mac
./reset_db.sh
```

📖 **Guía completa**: Ver [migrations/README.md](migrations/README.md)

---

## 🚀 Instalación del proyecto

1. **Clonar el repositorio**
   ```bash
   git clone tu_repositorio
   cd tu_repositorio
   ```
2. **Crear entorno virtual**

   ```
   python -m venv env

   env\Scripts\Activate
   ```

3. **Instalar dependencias de python y node**

   ```
   pip install -r requirements.txt

   npm install
   ```

   **Para actualizar el requirements.txt**

   _Necesario para instalaciones de nuevas dependencias_

   ```
   pip freeze > requirements.txt
   ```

4. **Ejecucion (Dos terminales)**

   Ejecucion en modo watch de tailwindcss (estilos)

   ```
   npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/style.css --watch
   ```

   Ejecucion del entorno virtual (Flask)

   ```
    python app.py
   ```
