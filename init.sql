-- Script de inicialización de la base de datos
-- Este archivo se ejecutará automáticamente cuando el contenedor se cree por primera vez
-- Crear extensiones si son necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Asegurar que la base de datos use UTF-8
SET client_encoding = 'UTF8';
-- Mensaje de confirmación
SELECT 'Base de datos inicializada correctamente' as status;