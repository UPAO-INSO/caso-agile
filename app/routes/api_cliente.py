"""
API v1 - Endpoints de Clientes
Endpoints REST que retornan JSON
"""
from flask import jsonify, request
import logging

from app.routes import api_v1_bp
from app.crud import (
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
from app.models import EstadoPrestamoEnum
from app.common.error_handler import ErrorHandler

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)


@api_v1_bp.route('/clientes', methods=['POST'])
def crear_cliente_api():
    """
    Crea un nuevo cliente
    
    Request body:
    {
        "dni": "12345678",
        "correo_electronico": "email@example.com",
        "pep_declarado": false
    }
    """
    data = request.get_json()
    
    if not data:
        return error_handler.respond('Datos inválidos', 400)
    
    dni = data.get('dni')
    correo_electronico = data.get('correo_electronico')
    pep_declarado = data.get('pep_declarado', False)
    
    if not dni or not correo_electronico:
        return error_handler.respond('DNI y correo electrónico son requeridos', 400)
    
    cliente_dict, error = crear_cliente(dni, correo_electronico, pep_declarado)
    
    if error:
        return error_handler.respond(error, 400)
    
    return jsonify(cliente_dict), 201


@api_v1_bp.route('/clientes', methods=['GET'])
def listar_clientes_api():
    """Lista todos los clientes"""
    clientes = listar_clientes()
    return jsonify([c.to_dict() for c in clientes]), 200


@api_v1_bp.route('/clientes/<int:cliente_id>', methods=['GET'])
def obtener_cliente_api(cliente_id):
    """Obtiene un cliente por ID"""
    cliente = obtener_cliente_por_id(cliente_id)
    
    if not cliente:
        return error_handler.respond('Cliente no encontrado', 404)
    
    return jsonify(cliente.to_dict()), 200


@api_v1_bp.route('/clientes/<int:cliente_id>', methods=['PUT'])
def actualizar_cliente_api(cliente_id):
    """
    Actualiza un cliente
    
    Request body:
    {
        "pep": true
    }
    """
    data = request.get_json()
    
    if not data:
        return error_handler.respond('Datos inválidos', 400)
    
    pep = data.get('pep')
    cliente, error = actualizar_cliente(cliente_id, pep=pep)
    
    if error:
        return error_handler.respond(error, 404 if 'no encontrado' in error else 500)
    
    return jsonify(cliente.to_dict()), 200


@api_v1_bp.route('/clientes/<int:cliente_id>', methods=['DELETE'])
def eliminar_cliente_api(cliente_id):
    """Elimina un cliente"""
    success, error = eliminar_cliente(cliente_id)
    
    if not success:
        return error_handler.respond(error, 404 if 'no encontrado' in error else 500)
    
    return jsonify({'message': 'Cliente eliminado exitosamente'}), 200


@api_v1_bp.route('/clientes/dni/<string:dni>', methods=['GET'])
def buscar_cliente_por_dni_api(dni):
    """Busca un cliente por DNI"""
    cliente = obtener_cliente_por_dni(dni)
    
    if not cliente:
        return error_handler.respond('Cliente no encontrado', 404)
    
    # Incluir información de préstamo activo si existe
    prestamo_activo = prestamo_activo_cliente(
        cliente.cliente_id,
        EstadoPrestamoEnum.VIGENTE
    )
    
    cliente_dict = cliente.to_dict()
    cliente_dict['tiene_prestamo_activo'] = prestamo_activo is not None
    
    if prestamo_activo:
        cliente_dict['prestamo_activo'] = {
            'prestamo_id': prestamo_activo.prestamo_id,
            'monto_total': float(prestamo_activo.monto_total),
            'estado': prestamo_activo.estado.value
        }
    
    return jsonify(cliente_dict), 200


@api_v1_bp.route('/clientes/verificar-prestamo/<int:cliente_id>', methods=['GET'])
def verificar_prestamo_activo_api(cliente_id):
    """Verifica si un cliente tiene préstamo activo"""
    prestamo = prestamo_activo_cliente(cliente_id, EstadoPrestamoEnum.VIGENTE)
    
    return jsonify({
        'tiene_prestamo_activo': prestamo is not None,
        'prestamo_id': prestamo.prestamo_id if prestamo else None
    }), 200


@api_v1_bp.route('/clientes/consultar-dni/<string:dni>', methods=['GET'])
def consultar_dni_reniec_api(dni):
    """
    Consulta datos de un DNI en RENIEC
    
    Query params:
    - correo_electronico: string (opcional)
    """
    correo_electronico = request.args.get('correo_electronico')
    
    info, error = consultar_dni_api(dni, correo_electronico)
    
    if error:
        return error_handler.respond(error, 404 if 'no encontrado' in error else 500)
    
    return jsonify(info), 200


@api_v1_bp.route('/clientes/validar-pep/<string:dni>', methods=['GET'])
def validar_pep_api(dni):
    """Valida si un DNI está en el dataset PEP"""
    es_pep = validar_pep_en_dataset(dni)
    
    return jsonify({
        'dni': dni,
        'es_pep': es_pep,
        'fuente': 'Dataset oficial PEP'
    }), 200
