from flask import render_template, request, jsonify
from decimal import Decimal
import logging
from pydantic import ValidationError

from app.extensions import db
from app.crud import (
    listar_prestamos_por_cliente_id,
    obtener_prestamo_por_id,
    obtener_cliente_por_id,
    obtener_clientes_por_estado_prestamo
)
from app.common.error_handler import ErrorHandler
from app.models import EstadoPrestamoEnum
from app.schemas import PrestamoCreateDTO
from app.routes import prestamos_bp
from app.services.prestamo_service import PrestamoService

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)

@prestamos_bp.route('/register', methods=['POST'])
def registrar_prestamo():
    """Endpoint para registrar un nuevo préstamo"""
    payload = request.get_json(silent=True)
    if payload is None:
        return error_handler.respond('El cuerpo de la solicitud debe ser JSON válido.', 400)

    try:
        dto = PrestamoCreateDTO.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Errores de validación al registrar préstamo", extra={'errors': exc.errors()})
        # Convertir errores de Pydantic a formato serializable
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

    # Delegar toda la lógica de negocio al servicio
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
            # Error de préstamo activo
            return jsonify(respuesta), status_code
        return error_handler.respond(error, status_code)
    
    return jsonify(respuesta), status_code

# ENDPOINTS API ADICIONALES

@prestamos_bp.route('/api/prestamo/<int:prestamo_id>', methods=['GET'])
def obtener_prestamo_api(prestamo_id): # → Endpoint para obtener la información completa de un préstamo
    from app.cuotas.crud import listar_cuotas_por_prestamo, obtener_resumen_cuotas
    
    prestamo = obtener_prestamo_por_id(prestamo_id)
    
    if not prestamo:
        return jsonify({'error': 'Préstamo no encontrado'}), 404
    
    # Obtener cuotas
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
            'nombre_completo': f"{prestamo.cliente.nombre_completo}",
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


@prestamos_bp.route('/api/cliente/<int:cliente_id>/prestamos', methods=['GET'])
def listar_prestamos_cliente_api(cliente_id): # → Endpoint para listar todos los préstamos de un cliente
    from app.clients.crud import obtener_cliente_por_id
    
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

# -------------- ENDPOINTS DE VISTAS (HTML) ------------------------

@prestamos_bp.route('/', methods=['GET'])
def list_clientes_con_prestamos():

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
    cliente = obtener_cliente_por_id(cliente_id)
    
    if cliente is None:
        return error_handler.respond('Cliente no encontrado.', 404)
        
    prestamos_del_cliente = listar_prestamos_por_cliente_id(cliente_id)

    listado_prestamos = [{
        'id': p.prestamo_id,
        'monto': f"S/ {p.monto_total.quantize(Decimal('0.01'))}",
        'estado': p.estado.value,
        'plazo': p.plazo,
        'f_otorgamiento': p.f_otorgamiento.strftime('%d-%m-%Y')
    } for p in prestamos_del_cliente]
    
    return render_template('list.html', 
                           cliente=cliente,
                           prestamos=listado_prestamos, 
                           title=f"Préstamos de {cliente.nombre_completo}")

@prestamos_bp.route('/prestamo/<int:prestamo_id>', methods=['GET'])
def detail_prestamo(prestamo_id): # → Detalle de un préstamo
    from app.cuotas.crud import listar_cuotas_por_prestamo
    
    prestamo = obtener_prestamo_por_id(prestamo_id)
    
    if prestamo is None:
        return error_handler.respond('Préstamo no encontrado.', 404)

    # Obtener cuotas desde crud.py (correcto)
    cronograma_list = listar_cuotas_por_prestamo(prestamo_id)

    cronograma_data = [{
        'nro': c.numero_cuota,
        'vencimiento': c.fecha_vencimiento.strftime('%d-%m-%Y'),
        'monto_cuota': f"S/ {c.monto_cuota.quantize(Decimal('0.01'))}",
        'capital': f"S/ {c.monto_capital.quantize(Decimal('0.01'))}",
        'interes': f"S/ {c.monto_interes.quantize(Decimal('0.01'))}",
        'saldo': f"S/ {c.saldo_capital.quantize(Decimal('0.01'))}",
        'pagado': 'Sí' if c.monto_pagado else 'No'
    } for c in cronograma_list]

    datos_prestamo = {
        'id': prestamo.prestamo_id,
        'cliente_id': prestamo.cliente_id, 
        'cliente': prestamo.cliente.nombre_completo,
        'dni': prestamo.cliente.dni,
        'monto_total': f"S/ {prestamo.monto_total.quantize(Decimal('0.01'))}",
        'interes_tea': f"{prestamo.interes_tea.quantize(Decimal('0.01'))} %",
        'plazo': prestamo.plazo,
        'f_otorgamiento': prestamo.f_otorgamiento.strftime('%d-%m-%Y'),
        'estado': prestamo.estado.value,
        'requiere_dj': 'Sí' if prestamo.requiere_dec_jurada else 'No',
        'tipo_dj': prestamo.declaracion_jurada.tipo_declaracion.value if prestamo.declaracion_jurada else 'N/A'
    }

    return render_template('detail.html', prestamo=datos_prestamo, cronograma=cronograma_data, title=f"Detalle Préstamo {prestamo_id}")

@prestamos_bp.route('/actualizar-estado/<int:prestamo_id>', methods=['POST'])
def actualizar_estado_prestamo(prestamo_id):
    """Actualizar estado de préstamo: VIGENTE -> CANCELADO (irreversible)"""
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

@prestamos_bp.route('/cliente/<int:cliente_id>/json', methods=['GET'])
def obtener_prestamos_cliente_json(cliente_id):
    """Endpoint JSON para obtener todos los préstamos de un cliente con sus cronogramas"""
    from app.cuotas.crud import listar_cuotas_por_prestamo
    
    cliente = obtener_cliente_por_id(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    prestamos_del_cliente = listar_prestamos_por_cliente_id(cliente_id)
    
    prestamos_data = []
    for prestamo in prestamos_del_cliente:
        # Obtener cronograma de cuotas
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