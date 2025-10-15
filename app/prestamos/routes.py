from flask import render_template, request, jsonify, abort
from datetime import date
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)

# Importaciones de dependencias locales
from app import db 
from . import bp 

# Importaciones de los Modelos (Ajustadas a tu estructura)
from .model.prestamos import Prestamo, EstadoPrestamoEnum
from app.cuotas.model.cuotas import Cuota
from app.declaraciones.model.declaraciones import DeclaracionJurada, TipoDeclaracionEnum 
from app.clients.model.clients import Cliente 

# Importaciones de Utilidades (app/utils.py)
from app.utils import generar_cronograma_pagos, UIT_VALOR

# --------------------------------------------------------------------------------
# RUTA: REGISTRAR NUEVO PRÉSTAMO (CREATE - POST)
# --------------------------------------------------------------------------------

@bp.route('/register', methods=['POST'])
def registrar_prestamo():
    """
    POST: Procesa el JSON para registrar un nuevo préstamo.
    Realiza validaciones de Cliente, Préstamo Activo, Declaración Jurada, 
    y genera el cronograma de pagos.
    """
    # --- 1. Obtención y Validación Inicial de Datos ---
    try:
        data = request.json
        
        dni = data.get('dni')
        monto_total_str = data.get('monto')
        interes_tea_str = data.get('interes_tea')
        plazo = int(data.get('plazo', 0))
        f_otorgamiento_str = data.get('f_otorgamiento') 

        if not all([dni, monto_total_str, interes_tea_str, plazo > 0, f_otorgamiento_str]):
            return jsonify({'success': False, 'message': 'Faltan datos requeridos o son inválidos.'}), 400

        monto_total = Decimal(monto_total_str)
        interes_tea = Decimal(interes_tea_str)
        f_otorgamiento = date.fromisoformat(f_otorgamiento_str)
        
    except (ValueError, InvalidOperation) as e:
        logger.error(f"Error en datos de entrada para registro de préstamo: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Datos numéricos o de fecha inválidos.'}), 400
    except Exception as e:
         return jsonify({'success': False, 'message': f'Error al procesar datos: {e}'}), 400

    # --- 2. Búsqueda y Validación del Cliente ---
    cliente = db.session.execute(db.select(Cliente).filter_by(dni=dni)).scalar_one_or_none()
    
    if not cliente:
        return jsonify({'success': False, 'message': f'Cliente con DNI {dni} no encontrado en la base de datos.'}), 404
        
    # VALIDACIÓN REGLA DE NEGOCIO: Un cliente solo puede tener un crédito activo.
    prestamo_activo = db.session.execute(
        db.select(Prestamo)
        .filter_by(cliente_id=cliente.cliente_id, estado=EstadoPrestamoEnum.VIGENTE)
    ).scalar_one_or_none()
    
    if prestamo_activo:
        return jsonify({'success': False, 'message': f'El cliente {cliente.nombre_completo} ya tiene un préstamo ACTIVO (ID: {prestamo_activo.prestamo_id}).'}), 400

    # --- 3. Validación y Creación de Declaración Jurada (DJ) ---
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
        db.session.add(nueva_dj)

    # --- 4. Creación del Préstamo (Transacción) ---
    try:
        # Obtener la PK de la DJ antes de usarla como FK en Prestamo
        if nueva_dj:
            db.session.flush() 
            declaracion_id = nueva_dj.declaracion_id

        nuevo_prestamo = Prestamo(
            cliente_id=cliente.cliente_id,
            monto_total=monto_total,
            interes_tea=interes_tea,
            plazo=plazo,
            f_otorgamiento=f_otorgamiento,
            requiere_dec_jurada=requiere_dj,
            declaracion_id=declaracion_id
        )
        db.session.add(nuevo_prestamo)
        db.session.flush() # Obtener el ID del préstamo para las cuotas

        # --- 5. Generación y Creación del Cronograma de Pagos ---
        cronograma = generar_cronograma_pagos(monto_total, interes_tea, plazo, f_otorgamiento)
        
        cuotas_a_crear = []
        for item in cronograma:
            cuota = Cuota(
                prestamo_id=nuevo_prestamo.prestamo_id,
                numero_cuota=item['numero_cuota'],
                fecha_vencimiento=item['fecha_vencimiento'],
                monto_cuota=item['monto_cuota'],
                monto_capital=item['monto_capital'],
                monto_interes=item['monto_interes'],
                saldo_capital=item['saldo_capital']
            )
            cuotas_a_crear.append(cuota)
        
        db.session.add_all(cuotas_a_crear)

        # --- 6. Commit de la Transacción ---
        db.session.commit()
        return jsonify({'success': True, 'message': 'Préstamo y cronograma registrados.', 'prestamo_id': nuevo_prestamo.prestamo_id}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error fatal en la transacción de registro de préstamo: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error en la base de datos al registrar el préstamo o el cronograma.'}), 500

# --------------------------------------------------------------------------------
# RUTA 1: LISTADO DE CLIENTES CON PRÉSTAMOS (READ - GET)
# *Se usa la plantilla 'list_clientes.html'*
# --------------------------------------------------------------------------------

@bp.route('/', methods=['GET']) # Usamos la ruta base para el listado principal
def list_clientes_con_prestamos():
    """
    GET: Lista todos los clientes que tienen al menos un préstamo.
    """
    clientes_con_prestamos = db.session.execute(
        db.select(Cliente)
        .join(Prestamo) 
        .distinct() 
        .order_by(Cliente.nombre_completo.asc())
    ).scalars().all()

    listado_clientes = [{
        'id': c.cliente_id,
        'nombre_completo': c.nombre_completo,
        'dni': c.dni,
        'pep': 'Sí' if c.pep else 'No',
    } for c in clientes_con_prestamos]
    
    # IMPORTANTE: Cambiamos la plantilla renderizada a 'list_clientes.html'
    return render_template('list_clients.html', clientes=listado_clientes, title="Consulta de Clientes con Historial")


# --------------------------------------------------------------------------------
# RUTA 2: LISTADO DE PRÉSTAMOS DE UN CLIENTE ESPECÍFICO (READ - GET)
# *Se usa la plantilla 'list.html'*
# --------------------------------------------------------------------------------

@bp.route('/cliente/<int:cliente_id>/prestamos', methods=['GET'])
def list_prestamos_por_cliente(cliente_id):
    """
    GET: Lista todos los préstamos de un cliente específico.
    """
    cliente = db.session.execute(db.select(Cliente).filter_by(cliente_id=cliente_id)).scalar_one_or_none()
    
    if cliente is None:
        return abort(404)
        
    prestamos_del_cliente = db.session.execute(
        db.select(Prestamo)
        .where(Prestamo.cliente_id == cliente_id)
        .order_by(Prestamo.f_registro.desc())
    ).scalars().all()

    listado_prestamos = [{
        'id': p.prestamo_id,
        'monto': f"S/ {p.monto_total.quantize(Decimal('0.01'))}",
        'estado': p.estado.value,
        'plazo': p.plazo,
        'f_otorgamiento': p.f_otorgamiento.strftime('%d-%m-%Y')
    } for p in prestamos_del_cliente]
    
    # IMPORTANTE: Usamos la plantilla 'list.html' pero enviando la variable 'prestamos'
    return render_template('list.html', 
                           cliente=cliente, # También enviamos el cliente para el título/navegación
                           prestamos=listado_prestamos, 
                           title=f"Préstamos de {cliente.nombre_completo}")

# --------------------------------------------------------------------------------
# RUTA 3: DETALLE Y CRONOGRAMA DE UN PRÉSTAMO (READ - GET)
# *Se usa la plantilla 'detail.html'*
# --------------------------------------------------------------------------------

@bp.route('/prestamo/<int:prestamo_id>', methods=['GET'])
def detail_prestamo(prestamo_id):
    """
    GET: Muestra el detalle de un préstamo y su cronograma.
    """
    prestamo = db.session.execute(
        db.select(Prestamo)
        .filter_by(prestamo_id=prestamo_id)
        .options(db.joinedload(Prestamo.cliente), db.joinedload(Prestamo.declaracion_jurada))
    ).scalar_one_or_none()
    
    if prestamo is None:
        return abort(404) 

    cronograma_list = db.session.execute(
        db.select(Cuota)
        .where(Cuota.prestamo_id == prestamo_id)
        .order_by(Cuota.numero_cuota.asc())
    ).scalars().all()

    # Preparar datos para el frontend (Jinja)
    cronograma_data = [{
        'nro': c.numero_cuota,
        'vencimiento': c.fecha_vencimiento.strftime('%d-%m-%Y'),
        'monto_cuota': f"S/ {c.monto_cuota.quantize(Decimal('0.01'))}",
        'capital': f"S/ {c.monto_capital.quantize(Decimal('0.01'))}",
        'interes': f"S/ {c.monto_interes.quantize(Decimal('0.01'))}",
        'saldo': f"S/ {c.saldo_capital.quantize(Decimal('0.01'))}",
        'pagado': 'Sí' if c.monto_pagado else 'No'
    } for c in cronograma_list]

    # Datos del préstamo
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
