from app import db
from app.prestamos.model.prestamos import Prestamo, EstadoPrestamoEnum
from app.declaraciones.model.declaraciones import DeclaracionJurada, TipoDeclaracionEnum
from app.cuotas.model.cuotas import Cuota
from datetime import date
from decimal import Decimal
from app.clients.crud import prestamo_activo_cliente
from app.declaraciones.crud import crear_declaracion
from app.cuotas.crud import crear_cuotas_bulk
from app.common.utils import generar_cronograma_pagos, UIT_VALOR

''' ESTA ES LA LÓGICA DEL CLIENTE
TENER EN CUENTA:
   templates : Vistas dinámicas 
   crud.py   : LÓGICA DE NEGOCIO ←------ ESTAMOS AQUÍ 
   routes.py : Rutas URL - endpoints
   schemas.py: Define la estructura y validación                               

   - DARLE UNA REVISADA - URGENTE - SE PUEDE SIMPLIFICAR '''

# ------------------------------ FUNCIONES DE FORMATEO (PARA RESPUESTAS JSON) ------------------------------

def formatear_cliente_json(cliente):
    return {
        'cliente_id': cliente.cliente_id,
        'dni': cliente.dni,
        'nombre_completo': f"{cliente.nombre_completo} {cliente.apellido_paterno} {cliente.apellido_materno}",
        'pep': cliente.pep
    }

def formatear_prestamo_json(prestamo):
    return {
        'prestamo_id': prestamo.prestamo_id,
        'cliente_id': prestamo.cliente_id,
        'monto_total': float(prestamo.monto_total),
        'interes_tea': float(prestamo.interes_tea),
        'plazo': prestamo.plazo,
        'fecha_otorgamiento': prestamo.f_otorgamiento.isoformat(),
        'estado': prestamo.estado.value,
        'requiere_declaracion': prestamo.requiere_dec_jurada
    }

def formatear_cuota_json(cuota):
    return {
        'cuota_id': cuota.cuota_id,
        'numero_cuota': cuota.numero_cuota,
        'fecha_vencimiento': cuota.fecha_vencimiento.isoformat(),
        'monto_cuota': float(cuota.monto_cuota),
        'monto_capital': float(cuota.monto_capital),
        'monto_interes': float(cuota.monto_interes),
        'saldo_capital': float(cuota.saldo_capital),
        'pagado': bool(cuota.monto_pagado and cuota.monto_pagado > 0),
        'monto_pagado': float(cuota.monto_pagado) if cuota.monto_pagado else 0,
        'fecha_pago': cuota.fecha_pago.isoformat() if cuota.fecha_pago else None
    }

# ------------------------------ OPERACIONES CRUD ------------------------------

def crear_prestamo(prestamo):
    try:
        db.session.add(prestamo)        # Rastrea el objeto prestamo
        db.session.commit()             # Aplica los cambios permanentemente
        db.session.refresh(prestamo)    # Recarga el objeto desde la BD para evitar campos NO generados
        return prestamo
    except Exception as e: # Para errores
        db.session.rollback()
        raise Exception(f"Error al guardar el préstamo: {str(e)}")

def obtener_prestamo_por_id(prestamo_id):
    return db.session.get(Prestamo, prestamo_id)

def listar_prestamos_por_cliente_id(cliente_id):
    return db.session.execute(  # Ejecuta el siguiente script
        db.select(Prestamo)                       # Selecciona el objeto préstamo
        .where(Prestamo.cliente_id == cliente_id) # Lo relaciona el id local con el de Préstamo para mostrar la lista de ese cliente
        .order_by(Prestamo.f_registro.desc())     # Ordena la lista de forma descentemente por fecha de registro
    ).scalars().all()

def listar_prestamos():
    return Prestamo.query.all() # Lista todos los préstamos gracias al query

# ------------------------------ REGISTRO DE PRÉSTAMO ------------------------------

def registrar_prestamo_completo(cliente, monto_total, interes_tea, plazo, f_otorgamiento):
    """    Lógica de negocio para registrar un préstamo completo con declaración jurada y cuotas.
    Args:
        cliente: Objeto Cliente (ya validado)
        monto_total: Decimal - Monto del préstamo
        interes_tea: Decimal - Tasa de interés anual
        plazo: int - Plazo en meses
        f_otorgamiento: date - Fecha de otorgamiento
    Returns:
        tuple: (resultado_dict, error_message)    """
    
    # 1. Verificar si el cliente ya está guardado
    if cliente.cliente_id is None:
        try:
            db.session.add(cliente)
            db.session.flush()
        except Exception as e:
            db.session.rollback()
            return None, f'Error al guardar cliente: {str(e)}'
    
    # 2. Verificar préstamo activo
    prestamo_activo = prestamo_activo_cliente(cliente.cliente_id, EstadoPrestamoEnum.VIGENTE)
    if prestamo_activo:
        return {
            'error': 'PRESTAMO_ACTIVO',
            'mensaje': f'El cliente {cliente.nombre_completo} ya tiene un préstamo activo.',
            'prestamo_id': prestamo_activo.prestamo_id,
            'monto': float(prestamo_activo.monto_total),
            'estado': 'VIGENTE'
        }, 'PRESTAMO_ACTIVO'
    
    # 3. Determinar si requiere Declaración Jurada
    requiere_dj = monto_total > UIT_VALOR or cliente.pep
    tipo_declaracion_enum = None
    
    if requiere_dj:
        if monto_total > UIT_VALOR and cliente.pep:
            tipo_declaracion_enum = TipoDeclaracionEnum.AMBOS
        elif monto_total > UIT_VALOR:
            tipo_declaracion_enum = TipoDeclaracionEnum.USO_PROPIO
        else:
            tipo_declaracion_enum = TipoDeclaracionEnum.PEP
    
    try:
        declaracion_id = None
        modelo_declaracion = None
        
        # 4. Crear declaración jurada si es necesaria
        if requiere_dj:
            nueva_dj = DeclaracionJurada(
                cliente_id=cliente.cliente_id,
                tipo_declaracion=tipo_declaracion_enum,
                fecha_firma=date.today(),
                firmado=True
            )
            modelo_declaracion, error_dj = crear_declaracion(nueva_dj)
            
            if error_dj:
                return None, f'Error al crear declaracion jurada: {error_dj}'
            
            declaracion_id = modelo_declaracion.declaracion_id
        
        # 5. Crear el préstamo
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
        
        # 6. Generar cronograma de pagos
        cronograma = generar_cronograma_pagos(monto_total, interes_tea, plazo, f_otorgamiento)
        
        # 7. Crear cuotas en la base de datos
        cuotas_a_crear = [
            Cuota(
                prestamo_id=modelo_prestamo.prestamo_id,
                numero_cuota=item['numero_cuota'],
                fecha_vencimiento=item['fecha_vencimiento'],
                monto_cuota=item['monto_cuota'],
                monto_capital=item['monto_capital'],
                monto_interes=item['monto_interes'],
                saldo_capital=item['saldo_capital']
            )
            for item in cronograma
        ]
        
        crear_cuotas_bulk(cuotas_a_crear)
        
        # 8. Preparar respuesta
        respuesta = {
            'success': True,
            'message': 'Préstamo registrado exitosamente',
            'prestamo': formatear_prestamo_json(modelo_prestamo),
            'cliente': formatear_cliente_json(cliente),
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
        
        if requiere_dj and modelo_declaracion:
            respuesta['declaracion_jurada'] = {
                'declaracion_id': modelo_declaracion.declaracion_id,
                'tipo': tipo_declaracion_enum.value,
                'fecha_firma': modelo_declaracion.fecha_firma.isoformat()
            }
        
        return respuesta, None
        
    except Exception as exc:
        db.session.rollback()
        return None, f'Error en la transacción: {str(exc)}'

# ------------------------------ OBTENER PRÉSTAMO COMPLETO ------------------------------

def obtener_prestamo_completo(prestamo_id):
    """
    Obtiene un préstamo con toda su información relacionada (cliente, cuotas, declaración).
    
    Returns:
        tuple: (datos_dict, error_message)
    """
    from app.cuotas.crud import listar_cuotas_por_prestamo, obtener_resumen_cuotas
    
    prestamo = obtener_prestamo_por_id(prestamo_id)
    
    if not prestamo:
        return None, 'Préstamo no encontrado'
    
    # Obtener cuotas y resumen
    cuotas = listar_cuotas_por_prestamo(prestamo_id)
    resumen = obtener_resumen_cuotas(prestamo_id)
    
    respuesta = {
        'prestamo': formatear_prestamo_json(prestamo),
        'cliente': formatear_cliente_json(prestamo.cliente),
        'cronograma': [formatear_cuota_json(c) for c in cuotas],
        'resumen': resumen
    }
    
    if prestamo.declaracion_jurada:
        respuesta['declaracion_jurada'] = {
            'declaracion_id': prestamo.declaracion_jurada.declaracion_id,
            'tipo': prestamo.declaracion_jurada.tipo_declaracion.value,
            'fecha_firma': prestamo.declaracion_jurada.fecha_firma.isoformat(),
            'firmado': prestamo.declaracion_jurada.firmado
        }
    
    return respuesta, None

# ------------------------------ LISTAR PRÉSTAMOS DE CLIENTE ------------------------------

def obtener_prestamos_cliente_completo(cliente_id):
    """
    Obtiene todos los préstamos de un cliente con información formateada.
    
    Returns:
        tuple: (datos_dict, error_message)
    """
    from app.clients.crud import obtener_cliente_por_id
    
    cliente = obtener_cliente_por_id(cliente_id)
    if not cliente:
        return None, 'Cliente no encontrado'
    
    prestamos = listar_prestamos_por_cliente_id(cliente_id)
    
    respuesta = {
        'cliente': formatear_cliente_json(cliente),
        'prestamos': [formatear_prestamo_json(p) for p in prestamos],
        'total_prestamos': len(prestamos)
    }
    
    return respuesta, None

# ------------------------------ OBTENER PRÉSTAMOS CON CRONOGRAMAS ------------------------------

def obtener_prestamos_cliente_con_cronogramas(cliente_id):
    """
    Obtiene todos los préstamos de un cliente con sus cronogramas completos.
    
    Returns:
        tuple: (lista_prestamos, error_message)
    """
    from app.clients.crud import obtener_cliente_por_id
    from app.cuotas.crud import listar_cuotas_por_prestamo
    
    cliente = obtener_cliente_por_id(cliente_id)
    if not cliente:
        return None, 'Cliente no encontrado'
    
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
    
    return prestamos_data, None

# ------------------------------ FORMATEO PARA VISTAS HTML ------------------------------

def formatear_prestamos_para_lista(prestamos):
    """Formatea una lista de préstamos para mostrar en HTML"""
    return [{
        'id': p.prestamo_id,
        'monto': f"S/ {p.monto_total.quantize(Decimal('0.01'))}",
        'estado': p.estado.value,
        'plazo': p.plazo,
        'f_otorgamiento': p.f_otorgamiento.strftime('%d-%m-%Y')
    } for p in prestamos]

def formatear_prestamo_para_detalle(prestamo):
    """Formatea un préstamo para mostrar en la vista de detalle"""
    return {
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

def formatear_cronograma_para_detalle(cuotas):
    """Formatea el cronograma de cuotas para mostrar en HTML"""
    return [{
        'nro': c.numero_cuota,
        'vencimiento': c.fecha_vencimiento.strftime('%d-%m-%Y'),
        'monto_cuota': f"S/ {c.monto_cuota.quantize(Decimal('0.01'))}",
        'capital': f"S/ {c.monto_capital.quantize(Decimal('0.01'))}",
        'interes': f"S/ {c.monto_interes.quantize(Decimal('0.01'))}",
        'saldo': f"S/ {c.saldo_capital.quantize(Decimal('0.01'))}",
        'pagado': 'Sí' if c.monto_pagado else 'No'
    } for c in cuotas]

# ------------------------------ ACTUALIZACIÓN DE ESTADO ------------------------------

def actualizar_estado_prestamo(prestamo_id, nuevo_estado):
    """
    Actualiza el estado de un préstamo.
    
    Returns:
        tuple: (prestamo, error_message)
    """
    try:
        prestamo = db.session.get(Prestamo, prestamo_id)
        if not prestamo:
            return None, "Préstamo no encontrado"
        
        prestamo.estado = nuevo_estado
        db.session.commit()
        return prestamo, None
    except Exception as e:
        db.session.rollback()
        return None, f"Error al actualizar estado: {str(e)}"

def validar_cambio_estado(prestamo, estado_enum):
    """
    Valida si un cambio de estado es permitido según las reglas de negocio.
    
    Returns:
        tuple: (es_valido: bool, mensaje_error: str)
    """
    estado_actual = prestamo.estado
    
    # REGLA: CANCELADO es final, no se puede cambiar
    if estado_actual == EstadoPrestamoEnum.CANCELADO:
        return False, 'Un prestamo CANCELADO no puede cambiar de estado'
    
    # REGLA: VIGENTE solo puede pasar a CANCELADO
    if estado_actual == EstadoPrestamoEnum.VIGENTE and estado_enum == EstadoPrestamoEnum.VIGENTE:
        return False, 'El prestamo ya esta en estado VIGENTE'
    
    return True, None

def cambiar_estado_prestamo(prestamo_id, estado_enum):
    """
    Cambia el estado de un préstamo validando las reglas de negocio.
    
    Returns:
        tuple: (resultado_dict, error_message, status_code)
    """
    prestamo = obtener_prestamo_por_id(prestamo_id)
    if not prestamo:
        return None, 'Prestamo no encontrado', 404
    
    # Validar cambio
    es_valido, mensaje_error = validar_cambio_estado(prestamo, estado_enum)
    if not es_valido:
        return None, mensaje_error, 400
    
    estado_anterior = prestamo.estado
    
    try:
        prestamo.estado = estado_enum
        db.session.commit()
        
        resultado = {
            'success': True,
            'mensaje': f'Estado actualizado de {estado_anterior.value} a {estado_enum.value}',
            'prestamo_id': prestamo_id,
            'nuevo_estado': estado_enum.value
        }
        return resultado, None, 200
    except Exception as e:
        db.session.rollback()
        return None, f'Error al actualizar estado: {str(e)}', 500

def cancelar_prestamo(prestamo_id):
    """Cancela un préstamo (cambia estado a CANCELADO)"""
    prestamo, error = actualizar_estado_prestamo(prestamo_id, EstadoPrestamoEnum.CANCELADO)
    if error:
        return False, error
    return True, None