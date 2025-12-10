#!/bin/bash
set -e

echo "Iniciando aplicación Flask..."

# Esperar a que PostgreSQL esté listo usando Python y psycopg2
echo "Esperando a PostgreSQL..."
python << END
import sys
import time
import psycopg2
from urllib.parse import urlparse

db_url = "$DATABASE_URL"
result = urlparse(db_url)
username = result.username
password = result.password
database = result.path[1:]
hostname = result.hostname
port = result.port

max_attempts = 30
for attempt in range(max_attempts):
    try:
        conn = psycopg2.connect(
            dbname=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        conn.close()
        print("✓ PostgreSQL está listo!")
        sys.exit(0)
    except psycopg2.OperationalError:
        if attempt < max_attempts - 1:
            print(f"PostgreSQL no está listo aún - intento {attempt + 1}/{max_attempts}")
            time.sleep(2)
        else:
            print("✗ No se pudo conectar a PostgreSQL")
            sys.exit(1)
END

echo "PostgreSQL está listo!"

# Ejecutar migraciones de Alembic
echo "Ejecutando migraciones de base de datos..."

# Intentar obtener revisión actual
current_revision=$(flask db current 2>&1 || echo "")

if [[ "$current_revision" == *"Can't locate revision"* ]]; then
    echo "⚠ Detectada inconsistencia en migraciones, limpiando..."
    # Marcar la base de datos con la revisión inicial
    flask db stamp head
    current_revision=$(flask db current 2>&1 || echo "")
fi

if [[ "$current_revision" == *"(head)"* ]]; then
    echo "✓ Base de datos ya está actualizada"
else
    echo "Aplicando migraciones..."
    if flask db upgrade; then
        echo "✓ Migraciones aplicadas exitosamente"
    else
        echo "⚠ Error al aplicar migraciones"
        exit 1
    fi
fi

echo "Base de datos actualizada!"

# Ejecutar comando pasado como argumento
echo "Iniciando servidor..."
exec "$@"
