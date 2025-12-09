# Multi-stage build para optimizar el tamaño de la imagen
# Etapa 1: Node Builder - Compilar assets CSS con Tailwind
FROM node:20-alpine as node-builder

WORKDIR /app

# Copiar archivos de Node.js
COPY package*.json ./

# Instalar dependencias de Node
RUN npm install

# Copiar archivos necesarios para compilar CSS
COPY app/static/css/input.css ./app/static/css/
COPY app/ ./app/

# Compilar CSS con Tailwind
RUN npm run build:css

# Etapa 2: Python Builder - Instalar dependencias de Python
FROM python:3.10-slim as python-builder

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --user --no-cache-dir -r requirements.txt


# Etapa 3: Runtime - Imagen final
FROM python:3.10-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    PYTHONPATH=/app

# Instalar solo las dependencias de runtime necesarias
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no privilegiado para ejecutar la app
RUN useradd -m -u 1000 appuser

# Crear directorio de trabajo
WORKDIR /app

# Copiar las dependencias de Python instaladas desde el builder a /home/appuser/.local
COPY --from=python-builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Configurar PATH para que appuser pueda usar los binarios instalados
ENV PATH=/home/appuser/.local/bin:$PATH

# Copiar el código de la aplicación
COPY --chown=appuser:appuser . .

# Copiar los archivos CSS compilados desde node-builder
COPY --from=node-builder /app/app/static/css/style.css /app/app/static/css/style.css

# Copiar script de entrypoint como root antes de cambiar usuario
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Crear directorios necesarios
RUN mkdir -p instance && chown -R appuser:appuser /app

# Cambiar al usuario no privilegiado
USER appuser

# Exponer el puerto
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/', timeout=5)"

# Comando de inicio
CMD ["bash", "/usr/local/bin/docker-entrypoint.sh", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "wsgi:application"]
