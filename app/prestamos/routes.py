from flask import render_template, request, jsonify, abort
from datetime import date
from decimal import Decimal
import logging
from pydantic import ValidationError
from flask_mail import Message
from app import db, mail
from app.cuotas.model.cuotas import Cuota
from app.cuotas.crud import crear_cuotas_bulk
from app.declaraciones.crud import crear_declaracion
from app.prestamos.crud import crear_prestamo, listar_prestamos_por_cliente_id, obtener_prestamo_por_id
from app.common.error_handler import ErrorHandler
from .model.prestamos import Prestamo, EstadoPrestamoEnum
from app.declaraciones.model.declaraciones import DeclaracionJurada, TipoDeclaracionEnum 
from app.clients.crud import obtener_cliente_por_id, obtener_clientes_por_estado_prestamo, prestamo_activo_cliente, crear_o_obtener_cliente
from .schemas import PrestamoCreateDTO
from . import prestamos_bp
from app.common.utils import generar_cronograma_pagos, UIT_VALOR
from app.utils import generar_cronograma_pdf

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)

def enviar_correo_prestamo(cliente, prestamo, cronograma):
    """
    Envía un correo electrónico al cliente con los detalles del préstamo
    """
    try:
        if not cliente.correo_electronico:
            logger.warning(f"Cliente {cliente.dni} no tiene correo electrónico registrado")
            return False
        
        msg = Message(
            subject="Confirmación de Préstamo - Gota a Gota",
            recipients=[cliente.correo_electronico]
        )
        
        # Cuerpo de texto plano
        msg.body = f"""
Hola {cliente.nombre_completo},

Tu préstamo ha sido aprobado exitosamente.

Detalles del Préstamo:
- ID: {prestamo.prestamo_id}
- Monto: S/ {float(prestamo.monto_total):.2f}
- Tasa de Interés (TEA): {float(prestamo.interes_tea):.2f}%
- Plazo: {prestamo.plazo} meses
- Fecha de Otorgamiento: {prestamo.f_otorgamiento.strftime('%d/%m/%Y')}
- Número de Cuotas: {len(cronograma)}

Gracias por confiar en nosotros.

Atentamente,
Gota a Gota
"""
        
        # Cuerpo HTML
        msg.html = render_template(
            "emails/email_cliente.html",
            nombre=cliente.nombre_completo,
            prestamo_id=prestamo.prestamo_id,
            monto=float(prestamo.monto_total),
            interes_tea=float(prestamo.interes_tea),
            plazo=prestamo.plazo,
            fecha=prestamo.f_otorgamiento.strftime('%d/%m/%Y'),
            num_cuotas=len(cronograma)
        )
        
        # Adjuntar PDF del cronograma (si es posible)
        try:
            pdf_buffer = generar_cronograma_pdf(
                cliente.nombre_completo,
                float(prestamo.monto_total),
                len(cronograma),
                float(prestamo.interes_tea)
            )
            # Asegurarse de leer desde el inicio
            pdf_buffer.seek(0)
            pdf_bytes = pdf_buffer.read()
            msg.attach("cronograma.pdf", "application/pdf", pdf_bytes)
            logger.debug(f"Adjuntado cronograma PDF para el prestamo {prestamo.prestamo_id}")
        except Exception as attach_exc:
            logger.error(f"No se pudo generar/adjuntar el PDF del cronograma: {attach_exc}")

        mail.send(msg)
        logger.info(f"Correo enviado exitosamente a {cliente.correo_electronico}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar correo a {cliente.correo_electronico}: {str(e)}")
        return False

@prestamos_bp.route('/register', methods=['POST'])
def registrar_prestamo():
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

    dni = dto.dni
    correo_electronico = dto.correo_electronico
    monto_total = dto.monto
    interes_tea = dto.interes_tea
    plazo = dto.plazo
    f_otorgamiento = dto.f_otorgamiento

    # Intentar obtener cliente existente primero
    from app.clients.crud import obtener_cliente_por_dni
    cliente = obtener_cliente_por_dni(dni)
    
    # Si no existe, crearlo con los datos del formulario
    if not cliente:
        from app.clients.crud import crear_cliente
        cliente_dict, error_cliente = crear_cliente(dni, correo_electronico, pep_declarado=False)
        if error_cliente:
            return error_handler.respond(f'Error al crear cliente: {error_cliente}', 400)
        # Obtener el cliente recién creado
        cliente = obtener_cliente_por_dni(dni)
    
    error_cliente = None
    
    if error_cliente:
        return error_handler.respond(f'Error al procesar cliente: {error_cliente}', 400)
    
    if not cliente:
        return error_handler.respond(f'No se pudo crear o encontrar el cliente con DNI {dni}.', 404)
    
    # Verificar si tiene préstamo VIGENTE
    prestamo_activo = prestamo_activo_cliente(cliente.cliente_id, EstadoPrestamoEnum.VIGENTE)
    
    if prestamo_activo:
        return jsonify({
            'error': 'PRESTAMO_ACTIVO',
            'mensaje': f'El cliente {cliente.nombre_completo} ya tiene un préstamo activo.',
            'prestamo_id': prestamo_activo.prestamo_id,
            'monto': float(prestamo_activo.monto_total),
            'estado': 'VIGENTE'
        }), 400

    requiere_dj = False
    tipos_dj = set() 

    if monto_total > UIT_VALOR:
        requiere_dj = True
        tipos_dj.add(TipoDeclaracionEnum.USO_PROPIO)

    if cliente.pep:
        requiere_dj = True
        tipos_dj.add(TipoDeclaracionEnum.PEP)

    declaracion_id = None
    tipo_declaracion_enum = None
    
    if requiere_dj:
        if TipoDeclaracionEnum.USO_PROPIO in tipos_dj and TipoDeclaracionEnum.PEP in tipos_dj:
            tipo_declaracion_enum = TipoDeclaracionEnum.AMBOS
        elif TipoDeclaracionEnum.USO_PROPIO in tipos_dj:
            tipo_declaracion_enum = TipoDeclaracionEnum.USO_PROPIO
        else:
            tipo_declaracion_enum = TipoDeclaracionEnum.PEP

    try:
        # 1. Crear declaracion jurada si es necesaria
        modelo_declaracion = None
        if requiere_dj:
            nueva_dj = DeclaracionJurada(
                cliente_id=cliente.cliente_id,
                tipo_declaracion=tipo_declaracion_enum,
                fecha_firma=date.today(), 
                firmado=True 
            )
            modelo_declaracion, error_dj = crear_declaracion(nueva_dj)
            
            if error_dj:
                return error_handler.respond(f'Error al crear declaracion jurada: {error_dj}', 500)
            
            declaracion_id = modelo_declaracion.declaracion_id
        
        # 2. Crear el prestamo
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
        
        # 4. Crear cuotas en la base de datos
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
        
        # Guardar todas las cuotas
        crear_cuotas_bulk(cuotas_a_crear)

        # 5. Enviar correo electrónico al cliente
        enviar_correo_prestamo(cliente, modelo_prestamo, cronograma)

        # 6. Preparar respuesta con toda la información
        respuesta = {
            'success': True,
            'message': 'Préstamo registrado exitosamente',
            'prestamo': {
                'prestamo_id': modelo_prestamo.prestamo_id,
                'cliente_id': modelo_prestamo.cliente_id,
                'monto_total': float(modelo_prestamo.monto_total),
                'interes_tea': float(modelo_prestamo.interes_tea),
                'plazo': modelo_prestamo.plazo,
                'fecha_otorgamiento': modelo_prestamo.f_otorgamiento.isoformat(),
                'estado': modelo_prestamo.estado.value,
                'requiere_declaracion': requiere_dj
            },
            'cliente': {
                'cliente_id': cliente.cliente_id,
                'dni': cliente.dni,
                'nombre_completo': cliente.nombre_completo,
                'pep': cliente.pep
            },
            'cronograma': [
                {
                    'numero_cuota': c['numero_cuota'],
                    'fecha_vencimiento': c['fecha_vencimiento'].isoformat(),
                    'monto_cuota': float(c['monto_cuota']),
                    'monto_capital': float(c['monto_capital']),
                    'monto_interes': float(c['monto_interes']),
                    'saldo_capital': float(c['saldo_capital'])
                }
                for c in cronograma
            ]
        }
        
        if requiere_dj:
            respuesta['declaracion_jurada'] = {
                'declaracion_id': modelo_declaracion.declaracion_id,
                'tipo': tipo_declaracion_enum.value,
                'fecha_firma': modelo_declaracion.fecha_firma.isoformat()
            }

        return jsonify(respuesta), 201

    except Exception as exc:
        db.session.rollback()
        return error_handler.log_and_respond(
            exc,
            "Error fatal en la transacción de registro de préstamo",
            'Error en la base de datos al registrar el préstamo o el cronograma.',
            status_code=500,
            log_extra={'dni': dni},
        )

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
    """Actualizar estado de prestamo: VIGENTE -> CANCELADO (irreversible)"""
    data = request.get_json()
    nuevo_estado = data.get('estado')
    
    if not nuevo_estado:
        return jsonify({'error': 'El campo estado es requerido'}), 400
    
    try:
        estado_enum = EstadoPrestamoEnum[nuevo_estado.upper()]
    except KeyError:
        return jsonify({'error': 'Estado invalido. Debe ser VIGENTE o CANCELADO'}), 400
    
    prestamo = obtener_prestamo_por_id(prestamo_id)
    if not prestamo:
        return jsonify({'error': 'Prestamo no encontrado'}), 404
    
    estado_actual = prestamo.estado
    
    # REGLA: CANCELADO es final, no se puede cambiar
    if estado_actual == EstadoPrestamoEnum.CANCELADO:
        return jsonify({'error': 'Un prestamo CANCELADO no puede cambiar de estado'}), 400
    
    # REGLA: VIGENTE solo puede pasar a CANCELADO
    if estado_actual == EstadoPrestamoEnum.VIGENTE and estado_enum == EstadoPrestamoEnum.VIGENTE:
        return jsonify({'error': 'El prestamo ya esta en estado VIGENTE'}), 400
    
    try:
        prestamo.estado = estado_enum
        db.session.commit()
        return jsonify({
            'success': True,
            'mensaje': f'Estado actualizado de {estado_actual.value} a {estado_enum.value}',
            'prestamo_id': prestamo_id,
            'nuevo_estado': estado_enum.value
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar estado: {str(e)}'}), 500

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