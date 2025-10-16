"""
API v1 - Endpoints de Préstamos
Endpoints REST que retornan JSON
"""
from flask import jsonify, request
from decimal import Decimal
import logging
from pydantic import ValidationError

from . import api_v1_bp
from app.extensions import db
from app.prestamos.crud import (
    listar_prestamos_por_cliente_id,
    obtener_prestamo_por_id
)
from app.prestamos.schemas import PrestamoCreateDTO
from app.prestamos.model.prestamos import EstadoPrestamoEnum
from app.clients.crud import obtener_cliente_por_id
from app.common.error_handler import ErrorHandler
from app.services.prestamo_service import PrestamoService

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)


@api_v1_bp.route('/prestamos', methods=['POST'])
def registrar_prestamo_api():
    """
    Registra un nuevo préstamo
    
    Request body:
    {
        "dni": "12345678",
        "correo_electronico": "email@example.com",
        "monto": 10000.00,
        "interes_tea": 24.0,
        "plazo": 12,
        "f_otorgamiento": "2025-10-16"
    }
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return error_handler.respond('El cuerpo de la solicitud debe ser JSON válido.', 400)

    try:
        dto = PrestamoCreateDTO.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Errores de validación al registrar préstamo", extra={'errors': exc.errors()})
        errors_serializables = []
        for error in exc.errors():
            error_dict = {
                'loc': list(error.get('loc', [])),
                'msg': str(error.get('msg', '')),
                'type': str(error.get('type', ''))
            }
            if 'input' in error:
                error_dict['input'] = str(error['input'])
            errors_serializables.append(error_dict)
        return error_handler.respond('Datos inválidos.', 400, errors=errors_serializables)

    # Delegar al servicio
    respuesta, error, status_code = PrestamoService.registrar_prestamo_completo(
        dni=dto.dni,
        correo_electronico=dto.correo_electronico,
        monto_total=dto.monto,
        interes_tea=dto.interes_tea,
        plazo=dto.plazo,
        f_otorgamiento=dto.f_otorgamiento
    )
    
    if error:
        if status_code == 400 and respuesta and 'error' in respuesta:
            return jsonify(respuesta), status_code
        return error_handler.respond(error, status_code)
    
    return jsonify(respuesta), status_code


@api_v1_bp.route('/prestamos/<int:prestamo_id>', methods=['GET'])
def obtener_prestamo_api(prestamo_id):
    """Obtiene la información completa de un préstamo"""
    from app.cuotas.crud import listar_cuotas_por_prestamo, obtener_resumen_cuotas
    
    prestamo = obtener_prestamo_por_id(prestamo_id)
    
    if not prestamo:
        return jsonify({'error': 'Préstamo no encontrado'}), 404
    
    # Obtener cuotas y resumen
    cuotas = listar_cuotas_por_prestamo(prestamo_id)
    resumen = obtener_resumen_cuotas(prestamo_id)
    
    respuesta = {
        'prestamo': {
            'prestamo_id': prestamo.prestamo_id,
            'cliente_id': prestamo.cliente_id,
            'monto_total': float(prestamo.monto_total),
            'interes_tea': float(prestamo.interes_tea),
            'plazo': prestamo.plazo,
            'fecha_otorgamiento': prestamo.f_otorgamiento.isoformat(),
            'estado': prestamo.estado.value,
            'requiere_declaracion': prestamo.requiere_dec_jurada
        },
        'cliente': {
            'cliente_id': prestamo.cliente.cliente_id,
            'dni': prestamo.cliente.dni,
            'nombre_completo': f"{prestamo.cliente.nombre_completo} {prestamo.cliente.apellido_paterno} {prestamo.cliente.apellido_materno}",
            'pep': prestamo.cliente.pep
        },
        'cronograma': [
            {
                'cuota_id': c.cuota_id,
                'numero_cuota': c.numero_cuota,
                'fecha_vencimiento': c.fecha_vencimiento.isoformat(),
                'monto_cuota': float(c.monto_cuota),
                'monto_capital': float(c.monto_capital),
                'monto_interes': float(c.monto_interes),
                'saldo_capital': float(c.saldo_capital),
                'pagado': bool(c.monto_pagado and c.monto_pagado > 0),
                'monto_pagado': float(c.monto_pagado) if c.monto_pagado else 0,
                'fecha_pago': c.fecha_pago.isoformat() if c.fecha_pago else None
            }
            for c in cuotas
        ],
        'resumen': resumen
    }
    
    if prestamo.declaracion_jurada:
        respuesta['declaracion_jurada'] = {
            'declaracion_id': prestamo.declaracion_jurada.declaracion_id,
            'tipo': prestamo.declaracion_jurada.tipo_declaracion.value,
            'fecha_firma': prestamo.declaracion_jurada.fecha_firma.isoformat(),
            'firmado': prestamo.declaracion_jurada.firmado
        }
    
    return jsonify(respuesta), 200


@api_v1_bp.route('/clientes/<int:cliente_id>/prestamos', methods=['GET'])
def listar_prestamos_cliente_api(cliente_id):
    """Lista todos los préstamos de un cliente"""
    cliente = obtener_cliente_por_id(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    prestamos = listar_prestamos_por_cliente_id(cliente_id)
    
    respuesta = {
        'cliente': {
            'cliente_id': cliente.cliente_id,
            'dni': cliente.dni,
            'nombre_completo': f"{cliente.nombre_completo}",
            'pep': cliente.pep
        },
        'prestamos': [
            {
                'prestamo_id': p.prestamo_id,
                'monto_total': float(p.monto_total),
                'interes_tea': float(p.interes_tea),
                'plazo': p.plazo,
                'fecha_otorgamiento': p.f_otorgamiento.isoformat(),
                'estado': p.estado.value,
                'requiere_declaracion': p.requiere_dec_jurada
            }
            for p in prestamos
        ],
        'total_prestamos': len(prestamos)
    }
    
    return jsonify(respuesta), 200


@api_v1_bp.route('/clientes/<int:cliente_id>/prestamos/detalle', methods=['GET'])
def obtener_prestamos_cliente_con_cronogramas_api(cliente_id):
    """Obtiene todos los préstamos de un cliente con sus cronogramas"""
    from app.cuotas.crud import listar_cuotas_por_prestamo
    
    cliente = obtener_cliente_por_id(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    prestamos_del_cliente = listar_prestamos_por_cliente_id(cliente_id)
    
    prestamos_data = []
    for prestamo in prestamos_del_cliente:
        cuotas = listar_cuotas_por_prestamo(prestamo.prestamo_id)
        
        cronograma_data = [{
            'numero_cuota': c.numero_cuota,
            'fecha_vencimiento': c.fecha_vencimiento.strftime('%d/%m/%Y'),
            'monto_cuota': float(c.monto_cuota),
            'monto_capital': float(c.monto_capital),
            'monto_interes': float(c.monto_interes),
            'saldo_capital': float(c.saldo_capital),
            'pagado': bool(c.monto_pagado)
        } for c in cuotas]
        
        prestamo_dict = {
            'prestamo_id': prestamo.prestamo_id,
            'monto_total': float(prestamo.monto_total),
            'interes_tea': float(prestamo.interes_tea),
            'plazo': prestamo.plazo,
            'f_otorgamiento': prestamo.f_otorgamiento.strftime('%d/%m/%Y'),
            'estado': prestamo.estado.value,
            'requiere_dec_jurada': prestamo.requiere_dec_jurada,
            'cronograma': cronograma_data
        }
        
        prestamos_data.append(prestamo_dict)
    
    return jsonify(prestamos_data), 200


@api_v1_bp.route('/prestamos/<int:prestamo_id>/estado', methods=['PUT'])
def actualizar_estado_prestamo_api(prestamo_id):
    """
    Actualiza el estado de un préstamo
    
    Request body:
    {
        "estado": "CANCELADO"
    }
    """
    data = request.get_json()
    nuevo_estado = data.get('estado')
    
    if not nuevo_estado:
        return jsonify({'error': 'El campo estado es requerido'}), 400
    
    try:
        estado_enum = EstadoPrestamoEnum[nuevo_estado.upper()]
    except KeyError:
        return jsonify({'error': 'Estado inválido. Debe ser VIGENTE o CANCELADO'}), 400
    
    # Delegar al servicio
    respuesta, error, status_code = PrestamoService.actualizar_estado_prestamo(prestamo_id, estado_enum)
    
    if error:
        return jsonify({'error': error}), status_code
    
    return jsonify(respuesta), status_code
