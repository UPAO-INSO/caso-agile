#!/bin/bash
set -e

echo "Iniciando aplicación Flask..."

# Esperar a que PostgreSQL esté listo
echo "Esperando a PostgreSQL..."
until pg_isready -h postgres -U postgres; do
  echo "PostgreSQL no está listo aún - esperando..."
  sleep 2
done

echo "PostgreSQL está listo!"

# Ejecutar migraciones de Alembic
echo "Ejecutando migraciones de base de datos..."

# Verificar si hay revisión actual
current_revision=$(flask db current 2>&1 || echo "")

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
