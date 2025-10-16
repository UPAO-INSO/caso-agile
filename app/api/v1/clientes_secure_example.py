"""
API v1 - Endpoints de Clientes (CON SEGURIDAD - Fase 9)
Ejemplo de cómo aplicar todas las medidas de seguridad
"""
from flask import jsonify, request
import logging

from . import api_v1_bp
from app.clients.crud import (
    listar_clientes,
    obtener_cliente_por_id,
    obtener_cliente_por_dni,
    actualizar_cliente,
    eliminar_cliente,
    prestamo_activo_cliente,
    consultar_dni_api,
    validar_pep_en_dataset,
    crear_cliente
)
from app.prestamos.model.prestamos import EstadoPrestamoEnum
from app.common.error_handler import ErrorHandler

# Importar utilidades de seguridad
from app.security import rate_limit, validator, sanitizer, require_csrf_token

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)


@api_v1_bp.route('/clientes', methods=['POST'])
@rate_limit(max_requests=10, window=60)  # Máximo 10 clientes por minuto
@require_csrf_token  # Protección CSRF
def crear_cliente_api_seguro():
    """
    Crea un nuevo cliente (VERSIÓN SEGURA)
    
    Request body:
    {
        "dni": "12345678",
        "correo_electronico": "email@example.com",
        "pep_declarado": false
    }
    
    Headers:
    - X-CSRF-Token: token_csrf (obligatorio)
    
    Rate Limit: 10 peticiones por minuto
    """
    data = request.get_json()
    
    if not data:
        return error_handler.respond('Datos inválidos', 400)
    
    # 1. VALIDACIÓN DE INPUTS
    dni = data.get('dni')
    correo_electronico = data.get('correo_electronico')
    pep_declarado = data.get('pep_declarado', False)
    
    # Validar DNI
    is_valid_dni, error_msg_dni = validator.validate_dni(dni)
    if not is_valid_dni:
        return error_handler.respond(error_msg_dni, 400)
    
    # Validar Email
    is_valid_email, error_msg_email = validator.validate_email(correo_electronico)
    if not is_valid_email:
        return error_handler.respond(error_msg_email, 400)
    
    # 2. SANITIZACIÓN DE INPUTS
    datos_sanitizados = sanitizer.sanitize_dict({
        'dni': dni,
        'correo_electronico': correo_electronico,
        'pep_declarado': pep_declarado
    })
    
    # 3. PROCESAMIENTO SEGURO
    try:
        cliente_dict, error = crear_cliente(
            datos_sanitizados['dni'],
            datos_sanitizados['correo_electronico'],
            datos_sanitizados['pep_declarado']
        )
        
        if error:
            return error_handler.respond(error, 400)
        
        logger.info(f'Cliente creado exitosamente: {datos_sanitizados["dni"]}')
        return jsonify(cliente_dict), 201
        
    except Exception as e:
        logger.error(f'Error al crear cliente: {e}')
        return error_handler.respond('Error interno del servidor', 500)


@api_v1_bp.route('/clientes', methods=['GET'])
@rate_limit(max_requests=30, window=60)  # Listado permite más peticiones
def listar_clientes_api_seguro():
    """
    Lista todos los clientes (VERSIÓN SEGURA)
    
    Rate Limit: 30 peticiones por minuto
    """
    try:
        clientes = listar_clientes()
        return jsonify([c.to_dict() for c in clientes]), 200
    except Exception as e:
        logger.error(f'Error al listar clientes: {e}')
        return error_handler.respond('Error interno del servidor', 500)


@api_v1_bp.route('/clientes/<int:cliente_id>', methods=['GET'])
@rate_limit(max_requests=50, window=60)
def obtener_cliente_api_seguro(cliente_id):
    """
    Obtiene un cliente por ID (VERSIÓN SEGURA)
    
    Rate Limit: 50 peticiones por minuto
    """
    # Validar que el ID sea positivo
    if cliente_id <= 0:
        return error_handler.respond('ID de cliente inválido', 400)
    
    try:
        cliente = obtener_cliente_por_id(cliente_id)
        
        if not cliente:
            return error_handler.respond('Cliente no encontrado', 404)
        
        return jsonify(cliente.to_dict()), 200
    except Exception as e:
        logger.error(f'Error al obtener cliente {cliente_id}: {e}')
        return error_handler.respond('Error interno del servidor', 500)


@api_v1_bp.route('/clientes/dni/<string:dni>', methods=['GET'])
@rate_limit(max_requests=20, window=60)
def obtener_cliente_por_dni_api_seguro(dni):
    """
    Busca un cliente por DNI (VERSIÓN SEGURA)
    
    Rate Limit: 20 peticiones por minuto
    """
    # 1. VALIDAR DNI
    is_valid, error_msg = validator.validate_dni(dni)
    if not is_valid:
        return error_handler.respond(error_msg, 400)
    
    # 2. SANITIZAR DNI
    dni_limpio = sanitizer.sanitize_html(dni)
    
    try:
        cliente = obtener_cliente_por_dni(dni_limpio)
        
        if not cliente:
            return error_handler.respond('Cliente no encontrado', 404)
        
        return jsonify({'cliente': cliente.to_dict()}), 200
    except Exception as e:
        logger.error(f'Error al buscar cliente por DNI {dni_limpio}: {e}')
        return error_handler.respond('Error interno del servidor', 500)


@api_v1_bp.route('/clientes/<int:cliente_id>', methods=['PUT'])
@rate_limit(max_requests=10, window=60)
@require_csrf_token  # PUT requiere CSRF
def actualizar_cliente_api_seguro(cliente_id):
    """
    Actualiza un cliente (VERSIÓN SEGURA)
    
    Request body:
    {
        "correo_electronico": "nuevo@email.com",
        "pep_declarado": true
    }
    
    Headers:
    - X-CSRF-Token: token_csrf (obligatorio)
    
    Rate Limit: 10 peticiones por minuto
    """
    # Validar ID
    if cliente_id <= 0:
        return error_handler.respond('ID de cliente inválido', 400)
    
    data = request.get_json()
    
    if not data:
        return error_handler.respond('Datos inválidos', 400)
    
    # 1. VALIDACIÓN
    correo = data.get('correo_electronico')
    if correo:
        is_valid, error_msg = validator.validate_email(correo)
        if not is_valid:
            return error_handler.respond(error_msg, 400)
    
    # 2. SANITIZACIÓN
    datos_sanitizados = sanitizer.sanitize_dict(data)
    
    try:
        cliente_actualizado = actualizar_cliente(cliente_id, **datos_sanitizados)
        
        if not cliente_actualizado:
            return error_handler.respond('Cliente no encontrado', 404)
        
        logger.info(f'Cliente {cliente_id} actualizado exitosamente')
        return jsonify(cliente_actualizado.to_dict()), 200
        
    except Exception as e:
        logger.error(f'Error al actualizar cliente {cliente_id}: {e}')
        return error_handler.respond('Error interno del servidor', 500)


@api_v1_bp.route('/clientes/<int:cliente_id>', methods=['DELETE'])
@rate_limit(max_requests=5, window=60)  # DELETE es más restrictivo
@require_csrf_token  # DELETE requiere CSRF
def eliminar_cliente_api_seguro(cliente_id):
    """
    Elimina un cliente (VERSIÓN SEGURA)
    
    Headers:
    - X-CSRF-Token: token_csrf (obligatorio)
    
    Rate Limit: 5 peticiones por minuto (operación sensible)
    """
    # Validar ID
    if cliente_id <= 0:
        return error_handler.respond('ID de cliente inválido', 400)
    
    try:
        # Verificar que no tenga préstamos activos
        prestamo_data = prestamo_activo_cliente(cliente_id)
        
        if prestamo_data and prestamo_data.get('tiene_prestamo_activo'):
            return error_handler.respond(
                'No se puede eliminar cliente con préstamos activos',
                409  # Conflict
            )
        
        success = eliminar_cliente(cliente_id)
        
        if not success:
            return error_handler.respond('Cliente no encontrado', 404)
        
        logger.warning(f'Cliente {cliente_id} eliminado')
        return jsonify({'message': 'Cliente eliminado exitosamente'}), 200
        
    except Exception as e:
        logger.error(f'Error al eliminar cliente {cliente_id}: {e}')
        return error_handler.respond('Error interno del servidor', 500)


@api_v1_bp.route('/clientes/consultar-dni/<string:dni>', methods=['GET'])
@rate_limit(max_requests=5, window=60)  # API externa, muy restrictivo
def consultar_dni_api_seguro(dni):
    """
    Consulta DNI en API externa (VERSIÓN SEGURA)
    
    Rate Limit: 5 peticiones por minuto (API externa costosa)
    """
    # 1. VALIDAR DNI
    is_valid, error_msg = validator.validate_dni(dni)
    if not is_valid:
        return error_handler.respond(error_msg, 400)
    
    # 2. SANITIZAR DNI
    dni_limpio = sanitizer.sanitize_html(dni)
    
    try:
        resultado = consultar_dni_api(dni_limpio)
        
        if not resultado:
            return error_handler.respond('DNI no encontrado en RENIEC', 404)
        
        # 3. SANITIZAR RESPUESTA antes de enviar al cliente
        resultado_sanitizado = sanitizer.sanitize_dict(resultado)
        
        logger.info(f'Consulta DNI exitosa: {dni_limpio}')
        return jsonify(resultado_sanitizado), 200
        
    except Exception as e:
        logger.error(f'Error al consultar DNI {dni_limpio}: {e}')
        return error_handler.respond(
            'Error al consultar DNI en servicio externo',
            503  # Service Unavailable
        )


@api_v1_bp.route('/clientes/validar-pep/<string:dni>', methods=['GET'])
@rate_limit(max_requests=10, window=60)
def validar_pep_api_seguro(dni):
    """
    Valida si un DNI es PEP (VERSIÓN SEGURA)
    
    Rate Limit: 10 peticiones por minuto
    """
    # 1. VALIDAR DNI
    is_valid, error_msg = validator.validate_dni(dni)
    if not is_valid:
        return error_handler.respond(error_msg, 400)
    
    # 2. SANITIZAR DNI
    dni_limpio = sanitizer.sanitize_html(dni)
    
    try:
        resultado = validar_pep_en_dataset(dni_limpio)
        
        logger.info(f'Validación PEP para DNI {dni_limpio}: {resultado}')
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f'Error al validar PEP para DNI {dni_limpio}: {e}')
        return error_handler.respond('Error interno del servidor', 500)


@api_v1_bp.route('/clientes/verificar-prestamo/<int:cliente_id>', methods=['GET'])
@rate_limit(max_requests=30, window=60)
def verificar_prestamo_activo_api_seguro(cliente_id):
    """
    Verifica si un cliente tiene préstamo activo (VERSIÓN SEGURA)
    
    Rate Limit: 30 peticiones por minuto
    """
    # Validar ID
    if cliente_id <= 0:
        return error_handler.respond('ID de cliente inválido', 400)
    
    try:
        prestamo_data = prestamo_activo_cliente(cliente_id)
        
        if prestamo_data is None:
            return error_handler.respond('Cliente no encontrado', 404)
        
        return jsonify(prestamo_data), 200
        
    except Exception as e:
        logger.error(f'Error al verificar préstamo para cliente {cliente_id}: {e}')
        return error_handler.respond('Error interno del servidor', 500)


# =========================================
# NOTAS DE IMPLEMENTACIÓN
# =========================================
"""
Este archivo muestra cómo aplicar todas las medidas de seguridad de Fase 9:

1. RATE LIMITING (@rate_limit)
   - GET: 20-50 peticiones/min (operaciones de lectura)
   - POST: 10 peticiones/min (creación)
   - PUT: 10 peticiones/min (actualización)
   - DELETE: 5 peticiones/min (eliminación - más restrictivo)
   - APIs externas: 5 peticiones/min (muy restrictivo)

2. CSRF PROTECTION (@require_csrf_token)
   - POST, PUT, DELETE requieren token CSRF
   - GET no requiere (operaciones de solo lectura)

3. INPUT VALIDATION (validator.validate_*)
   - Validar ANTES de procesar
   - Retornar errores 400 con mensajes claros

4. INPUT SANITIZATION (sanitizer.sanitize_*)
   - Sanitizar todos los inputs del usuario
   - Sanitizar respuestas de APIs externas
   - Prevenir XSS y SQL injection

5. ERROR HANDLING
   - Try-catch en todos los endpoints
   - Logging de errores
   - No exponer detalles internos
   - Códigos HTTP apropiados

6. LOGGING
   - Log de operaciones exitosas (INFO)
   - Log de operaciones sensibles (WARNING)
   - Log de errores (ERROR)

Para usar estos endpoints seguros, reemplazar las rutas actuales o crear
versiones "/v2/" con estas mejoras de seguridad.
"""
