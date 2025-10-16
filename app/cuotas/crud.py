from app.extensions import db
from app.cuotas.model.cuotas import Cuota
from datetime import date

def crear_cuotas_bulk(cuotas_lista): # → Crear múltiples cuotas en una sola transacción
    try:
        db.session.add_all(cuotas_lista)
        db.session.commit()
        return cuotas_lista
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error al crear cuotas: {str(e)}")

def listar_cuotas_por_prestamo(prestamo_id): # → Listar todas las cuotas de un préstamo ordenadas por número
    return db.session.execute(
        db.select(Cuota)
        .where(Cuota.prestamo_id == prestamo_id)
        .order_by(Cuota.numero_cuota.asc())
    ).scalars().all()

def obtener_cuota_por_id(cuota_id): # → Obtener una cuota específica por su ID
    return Cuota.query.get(cuota_id)

def registrar_pago_cuota(cuota_id, monto_pagado, fecha_pago=None): # → Registrar el pago de una cuota
    try:
        cuota = Cuota.query.get(cuota_id)
        if not cuota:
            return None, "Cuota no encontrada"
        
        if cuota.monto_pagado and cuota.monto_pagado > 0:
            return None, "Esta cuota ya fue pagada"
        cuota.monto_pagado = monto_pagado
        cuota.fecha_pago = fecha_pago or date.today()
        
        db.session.commit()
        return cuota, None
    except Exception as e:
        db.session.rollback()
        return None, f"Error al registrar pago: {str(e)}"

def obtener_cuotas_pendientes(prestamo_id): # → Obtener las cuotas pendientes de pago de un préstamo
    return db.session.execute(
        db.select(Cuota)
        .where(
            Cuota.prestamo_id == prestamo_id,
            (Cuota.monto_pagado == None) | (Cuota.monto_pagado == 0)
        )
        .order_by(Cuota.numero_cuota.asc())
    ).scalars().all()

def obtener_cuotas_vencidas(prestamo_id): # → Obtener las cuotas vencidas y no pagadas de un préstamo
    hoy = date.today()
    return db.session.execute(
        db.select(Cuota)
        .where(
            Cuota.prestamo_id == prestamo_id,
            Cuota.fecha_vencimiento < hoy,
            (Cuota.monto_pagado == None) | (Cuota.monto_pagado == 0)
        )
        .order_by(Cuota.numero_cuota.asc())
    ).scalars().all()

def obtener_resumen_cuotas(prestamo_id): # → Obtener un resumen del estado de las cuotas de un préstamo
    cuotas = listar_cuotas_por_prestamo(prestamo_id)
    
    total_cuotas = len(cuotas)
    cuotas_pagadas = sum(1 for c in cuotas if c.monto_pagado and c.monto_pagado > 0)
    cuotas_pendientes = total_cuotas - cuotas_pagadas
    
    monto_total_pagado = sum(c.monto_pagado for c in cuotas if c.monto_pagado)
    monto_total_pendiente = sum(c.monto_cuota for c in cuotas if not c.monto_pagado or c.monto_pagado == 0)
    
    cuotas_vencidas = [c for c in cuotas if c.fecha_vencimiento < date.today() and (not c.monto_pagado or c.monto_pagado == 0)]
    
    return {
        'total_cuotas': total_cuotas,
        'cuotas_pagadas': cuotas_pagadas,
        'cuotas_pendientes': cuotas_pendientes,
        'monto_total_pagado': float(monto_total_pagado),
        'monto_total_pendiente': float(monto_total_pendiente),
        'cuotas_vencidas': len(cuotas_vencidas)
    }