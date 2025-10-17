# Docker - Guía de Uso de PostgreSQL

## 📦 Prerequisitos

- Docker Desktop instalado y ejecutándose
- Puerto 5432 disponible (o cambiar el puerto en docker-compose.yml)

## 🚀 Comandos Principales

### Iniciar la base de datos

```bash
docker-compose up -d
```

### Detener la base de datos

```bash
docker-compose down
```

### Ver logs de la base de datos

```bash
docker-compose logs -f postgres
```

### Acceder al contenedor de PostgreSQL

```bash
docker exec -it caso_agile_db psql -U postgres -d caso_agile
```

### Reiniciar la base de datos

```bash
docker-compose restart postgres
```

### Eliminar la base de datos y volúmenes (⚠️ CUIDADO: Borra todos los datos)

```bash
docker-compose down -v
```

## 🔧 Configuración

La configuración está en `docker-compose.yml`:

- **Puerto**: 5432 (puedes cambiarlo si está en uso)
- **Usuario**: postgres
- **Contraseña**: Bryger170180
- **Base de datos**: caso_agile

## 📊 Verificar que está funcionando

```bash
# Ver el estado del contenedor
docker-compose ps

# Verificar conectividad
docker exec -it caso_agile_db pg_isready -U postgres
```

## 🔌 Conectar desde tu aplicación Flask

Tu archivo `.env` ya está configurado correctamente:

```
DATABASE_URL=postgresql://postgres:Bryger170180@localhost:5432/caso_agile
```

## 📝 Backup y Restore

### Hacer backup

```bash
docker exec caso_agile_db pg_dump -U postgres caso_agile > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restaurar backup

```bash
docker exec -i caso_agile_db psql -U postgres caso_agile < backup_20250115_120000.sql
```

## 🛠️ Troubleshooting

### Puerto ya en uso

Si el puerto 5432 está ocupado, edita `docker-compose.yml`:

```yaml
ports:
  - "5433:5432" # Usar puerto 5433 en tu máquina
```

Y actualiza `.env`:

```
DATABASE_URL=postgresql://postgres:Bryger170180@localhost:5433/caso_agile
```

### Ver logs de errores

```bash
docker-compose logs postgres
```

### Recrear la base de datos desde cero

```bash
docker-compose down -v
docker-compose up -d
```
