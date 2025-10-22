from flask import render_template, request, jsonify
import logging
from pydantic import ValidationError
from app.prestamos.crud import (
    registrar_prestamo_completo,
    obtener_prestamo_completo,
    obtener_prestamos_cliente_completo,
    obtener_prestamos_cliente_con_cronogramas,
    obtener_prestamo_por_id,
    listar_prestamos_por_cliente_id,
    formatear_prestamos_para_lista,
    formatear_prestamo_para_detalle,
    formatear_cronograma_para_detalle,
    cambiar_estado_prestamo)
from app.common.error_handler import ErrorHandler
from .model.prestamos import EstadoPrestamoEnum
from app.clients.crud import obtener_cliente_por_id, obtener_clientes_por_estado_prestamo, gestion_cliente
from .schemas import PrestamoCreateDTO
from . import prestamos_bp

''' RUTAS DE PRÉSTAMOS
TENER EN CUENTA:
   templates : Vistas dinámicas 
   crud.py   : Lógica de Negocio
   routes.py : Rutas URL - endpoints ←------ ESTAMOS AQUÍ 
   schemas.py: Define la estructura y validación
   
Este archivo SOLO maneja→:
   - Recepción de requests HTTP
   - Validación de datos de entrada (DTO)
   - Delegación de lógica al CRUD
   - Formateo de respuestas HTTP
   - Manejo de errores HTTP
'''

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)

# ------------------------------ ENDPOINTS API ------------------------------

@prestamos_bp.route('/register', methods=['POST'])
def registrar_prestamo():
    """Endpoint para registrar un nuevo préstamo con toda su información relacionada"""
    payload = request.get_json(silent=True)
    if payload is None:
        return error_handler.respond('El cuerpo de la solicitud debe ser JSON válido.', 400)

    # Validación con Pydantic
    try:
        dto = PrestamoCreateDTO.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Errores de validación al registrar préstamo", extra={'errors': exc.errors()})
        return error_handler.respond('Datos inválidos.', 400, errors=exc.errors())

    # Obtener o crear cliente en memoria
    cliente, metadata_o_error = gestion_cliente(dto.dni, dto.fecha_nacimiento)
    
    # Si cliente es None, entonces metadata_o_error contiene el mensaje de error
    if cliente is None:
        error_msg = metadata_o_error
        return error_handler.respond(f'Error al procesar cliente: {error_msg}', 400)
    
    # Delegar toda la lógica de negocio al CRUD
    resultado, error = registrar_prestamo_completo(
        cliente=cliente,
        monto_total=dto.monto,
        interes_tea=dto.interes_tea,
        plazo=dto.plazo,
        f_otorgamiento=dto.f_otorgamiento
    )
    
    if error:
        if error == 'PRESTAMO_ACTIVO':
            return jsonify(resultado), 400
        return error_handler.respond(error, 500)
    
    return jsonify(resultado), 201


@prestamos_bp.route('/api/prestamo/<int:prestamo_id>', methods=['GET'])
def obtener_prestamo_api(prestamo_id):
    """Endpoint para obtener la información completa de un préstamo"""
    resultado, error = obtener_prestamo_completo(prestamo_id)
    
    if error:
        return jsonify({'error': error}), 404
    
    return jsonify(resultado), 200


@prestamos_bp.route('/api/cliente/<int:cliente_id>/prestamos', methods=['GET'])
def listar_prestamos_cliente_api(cliente_id):
    """Endpoint para listar todos los préstamos de un cliente"""
    resultado, error = obtener_prestamos_cliente_completo(cliente_id)
    
    if error:
        return jsonify({'error': error}), 404
    
    return jsonify(resultado), 200


# ------------------------------ ENDPOINTS DE VISTAS (HTML) ------------------------------

@prestamos_bp.route('/', methods=['GET'])
def list_clientes_con_prestamos():
    """Endpoint para listar clientes con préstamos"""
    clientes_con_prestamos = obtener_clientes_por_estado_prestamo()
    
    listado_clientes = [{
        'id': c.cliente_id,
        'nombre_completo': c.nombre_completo,
        'dni': c.dni,
        'pep': 'Sí' if c.pep else 'No',
    } for c in clientes_con_prestamos]
    
    return render_template('list_clients.html', clientes=listado_clientes, title="Consulta de Clientes con Historial")


@prestamos_bp.route('/clientes/<int:cliente_id>', methods=['GET'])
def list_prestamos_por_cliente(cliente_id):
    """Listar todos los préstamos de un cliente específico"""
    cliente = obtener_cliente_por_id(cliente_id)
    
    if cliente is None:
        return error_handler.respond('Cliente no encontrado.', 404)
        
    prestamos_del_cliente = listar_prestamos_por_cliente_id(cliente_id)
    listado_prestamos = formatear_prestamos_para_lista(prestamos_del_cliente)
    
    return render_template('list.html', 
                           cliente=cliente,
                           prestamos=listado_prestamos, 
                           title=f"Préstamos de {cliente.nombre_completo}")


@prestamos_bp.route('/prestamo/<int:prestamo_id>', methods=['GET'])
def detail_prestamo(prestamo_id):
    """Vista de detalle de un préstamo con su cronograma"""
    from app.cuotas.crud import listar_cuotas_por_prestamo
    
    prestamo = obtener_prestamo_por_id(prestamo_id)
    
    if prestamo is None:
        return error_handler.respond('Préstamo no encontrado.', 404)

    # Obtener cuotas y formatear para vista
    cronograma_list = listar_cuotas_por_prestamo(prestamo_id)
    cronograma_data = formatear_cronograma_para_detalle(cronograma_list)
    datos_prestamo = formatear_prestamo_para_detalle(prestamo)

    return render_template('detail.html', prestamo=datos_prestamo, cronograma=cronograma_data, title=f"Detalle Préstamo {prestamo_id}")


@prestamos_bp.route('/actualizar-estado/<int:prestamo_id>', methods=['POST'])
def actualizar_estado(prestamo_id):
    """Actualizar estado de préstamo: VIGENTE -> CANCELADO (irreversible)"""
    data = request.get_json()
    nuevo_estado = data.get('estado')
    
    if not nuevo_estado:
        return jsonify({'error': 'El campo estado es requerido'}), 400
    
    try:
        estado_enum = EstadoPrestamoEnum[nuevo_estado.upper()]
    except KeyError:
        return jsonify({'error': 'Estado invalido. Debe ser VIGENTE o CANCELADO'}), 400
    
    # Delegar al CRUD la lógica de validación y cambio de estado
    resultado, error, status_code = cambiar_estado_prestamo(prestamo_id, estado_enum)
    
    if error:
        return jsonify({'error': error}), status_code
    
    return jsonify(resultado), status_code


@prestamos_bp.route('/cliente/<int:cliente_id>/json', methods=['GET'])
def obtener_prestamos_cliente_json(cliente_id):
    """Endpoint JSON para obtener todos los préstamos de un cliente con sus cronogramas"""
    resultado, error = obtener_prestamos_cliente_con_cronogramas(cliente_id)
    
    if error:
        return jsonify({'error': error}), 404
    
    return jsonify(resultado), 200