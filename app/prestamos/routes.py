from flask import render_template, request, jsonify, abort
from datetime import date
from decimal import Decimal
import logging

from pydantic import ValidationError

from app.cuotas.model.cuotas import Cuota
from app.declaraciones.crud import crear_declaracion
from app.prestamos.crud import crear_prestamo, listar_prestamos_por_cliente_id, obtener_prestamo_por_id
from app.common.error_handler import ErrorHandler

from .model.prestamos import Prestamo, EstadoPrestamoEnum
from app.declaraciones.model.declaraciones import DeclaracionJurada, TipoDeclaracionEnum 
from app.clients.crud import obtener_cliente_por_dni, obtener_cliente_por_id, obtener_clientes_por_estado_prestamo, prestamo_activo_cliente

from .schemas import PrestamoCreateDTO
from . import prestamos_bp
from app.common.utils import generar_cronograma_pagos, UIT_VALOR


logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)

@prestamos_bp.route('/register', methods=['POST'])
def registrar_prestamo():
    payload = request.get_json(silent=True)
    if payload is None:
        return error_handler.respond('El cuerpo de la solicitud debe ser JSON válido.', 400)

    try:
        dto = PrestamoCreateDTO.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Errores de validación al registrar préstamo", extra={'errors': exc.errors()})
        return error_handler.respond('Datos inválidos.', 400, errors=exc.errors())

    dni = dto.dni
    monto_total = dto.monto
    interes_tea = dto.interes_tea
    plazo = dto.plazo
    f_otorgamiento = dto.f_otorgamiento

    cliente = obtener_cliente_por_dni(dni)
    
    if not cliente:
        return error_handler.respond(f'Cliente con DNI {dni} no encontrado en la base de datos.', 404)
        
    prestamo_activo = prestamo_activo_cliente(cliente.cliente_id, EstadoPrestamoEnum.VIGENTE)
    
    if prestamo_activo:
        return error_handler.respond(
            f'El cliente {cliente.nombre_completo} ya tiene un préstamo ACTIVO (ID: {prestamo_activo.prestamo_id}).',
            400,
        )

    requiere_dj = False
    tipos_dj = set() 

    if monto_total > UIT_VALOR:
        requiere_dj = True
        tipos_dj.add(TipoDeclaracionEnum.USO_PROPIO)

    if cliente.pep:
        requiere_dj = True
        tipos_dj.add(TipoDeclaracionEnum.PEP)

    nueva_dj = None
    declaracion_id = None
    
    if requiere_dj:
        if TipoDeclaracionEnum.USO_PROPIO in tipos_dj and TipoDeclaracionEnum.PEP in tipos_dj:
            tipo_declaracion_enum = TipoDeclaracionEnum.AMBOS
        elif TipoDeclaracionEnum.USO_PROPIO in tipos_dj:
            tipo_declaracion_enum = TipoDeclaracionEnum.USO_PROPIO
        else:
            tipo_declaracion_enum = TipoDeclaracionEnum.PEP

        nueva_dj = DeclaracionJurada(
            cliente_id=cliente.cliente_id,
            tipo_declaracion=tipo_declaracion_enum,
            fecha_firma=date.today(), 
            firmado=True 
        )
        
        modelo_declaracion = crear_declaracion(nueva_dj)

    try:
        if nueva_dj:
            declaracion_id = modelo_declaracion.declaracion_id

        nuevo_prestamo = Prestamo(
            cliente_id=cliente.cliente_id,
            monto_total=monto_total,
            interes_tea=interes_tea,
            plazo=plazo,
            f_otorgamiento=f_otorgamiento,
            requiere_dec_jurada=requiere_dj,
            declaracion_id=declaracion_id
        )
        
        modelo_prestamo = crear_prestamo(nuevo_prestamo)

        cronograma = generar_cronograma_pagos(monto_total, interes_tea, plazo, f_otorgamiento)
        
        cuotas_a_crear = []
        for item in cronograma:
            cuota = Cuota(
                prestamo_id=modelo_prestamo.prestamo_id,
                numero_cuota=item['numero_cuota'],
                fecha_vencimiento=item['fecha_vencimiento'],
                monto_cuota=item['monto_cuota'],
                monto_capital=item['monto_capital'],
                monto_interes=item['monto_interes'],
                saldo_capital=item['saldo_capital']
            )
            cuotas_a_crear.append(cuota)
        
        # prestamos_bp.session.add_all(cuotas_a_crear)

        return jsonify({'success': True, 'message': 'Préstamo y cronograma registrados.', 'prestamo_id': nuevo_prestamo.prestamo_id}), 201

    except Exception as exc:
        return error_handler.log_and_respond(
            exc,
            "Error fatal en la transacción de registro de préstamo",
            'Error en la base de datos al registrar el préstamo o el cronograma.',
            status_code=500,
            log_extra={'dni': dni},
        )

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
def detail_prestamo(prestamo_id):
    prestamo = obtener_prestamo_por_id(prestamo_id)
    
    if prestamo is None:
        return error_handler.respond('Prestamo no encontrado.', 404)

    cronograma_list = []
    
    
    # TODO: Corregir -> Las conexiones a DB deben estar en los archivos crud.py
    # prestamos_bp.session.execute(
    #     prestamos_bp.select(Cuota)
    #     .where(Cuota.prestamo_id == prestamo_id)
    #     .order_by(Cuota.numero_cuota.asc())
    # ).scalars().all()

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
