"""
CRUD Operations para Pagos
Maneja todas las operaciones de base de datos relacionadas con pagos
"""
from app.common.extensions import db
from app.models import Pago, EstadoPagoEnum
from datetime import date


def registrar_pago(cuota_id, monto_pagado, fecha_pago=None, comprobante_referencia=None, observaciones=None):
    """
    Registra un pago de una cuota.
    
    Args:
        cuota_id: ID de la cuota a pagar
        monto_pagado: Monto del pago
        fecha_pago: Fecha del pago (por defecto hoy)
        comprobante_referencia: Referencia del comprobante (opcional)
        observaciones: Observaciones del pago (opcional)
    
    Returns:
        Tuple[Pago, error]: Objeto Pago creado y mensaje de error si aplica
    """
    try:
        # Validar que la cuota exista
        from app.models import Cuota
        cuota = Cuota.query.get(cuota_id)
        if not cuota:
            return None, f"Cuota con ID {cuota_id} no encontrada"
        
        # Crear el pago
        nuevo_pago = Pago(
            cuota_id=cuota_id,
            monto_pagado=monto_pagado,
            fecha_pago=fecha_pago or date.today(),
            estado=EstadoPagoEnum.REALIZADO,
            comprobante_referencia=comprobante_referencia,
            observaciones=observaciones
        )
        
        db.session.add(nuevo_pago)
        
        # Actualizar la cuota con la información del pago
        cuota.monto_pagado = monto_pagado
        cuota.fecha_pago = fecha_pago or date.today()
        
        db.session.commit()
        return nuevo_pago, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error al registrar pago: {str(e)}"


def obtener_pago_por_id(pago_id):
    """Obtiene un pago por su ID"""
    return Pago.query.get(pago_id)


def listar_pagos_por_cuota(cuota_id):
    """
    Obtiene todos los pagos de una cuota ordenados por fecha.
    
    Args:
        cuota_id: ID de la cuota
        
    Returns:
        Lista de pagos
    """
    return db.session.execute(
        db.select(Pago)
        .where(Pago.cuota_id == cuota_id)
        .order_by(Pago.fecha_pago.asc())
    ).scalars().all()


def listar_pagos_por_prestamo(prestamo_id):
    """
    Obtiene todos los pagos de un préstamo a través de sus cuotas.
    
    Args:
        prestamo_id: ID del préstamo
        
    Returns:
        Lista de pagos ordenados por fecha
    """
    from app.models import Cuota
    
    return db.session.execute(
        db.select(Pago)
        .join(Cuota)
        .where(Cuota.prestamo_id == prestamo_id)
        .order_by(Pago.fecha_pago.asc())
    ).scalars().all()


def obtener_pagos_pendientes_por_prestamo(prestamo_id):
    """
    Obtiene todas las cuotas pendientes de pago de un préstamo.
    
    Args:
        prestamo_id: ID del préstamo
        
    Returns:
        Lista de cuotas sin pagar
    """
    from app.models import Cuota
    
    return db.session.execute(
        db.select(Cuota)
        .where(
            Cuota.prestamo_id == prestamo_id,
            (Cuota.monto_pagado == None) | (Cuota.monto_pagado == 0)
        )
        .order_by(Cuota.numero_cuota.asc())
    ).scalars().all()


def actualizar_pago(pago_id, monto_pagado=None, fecha_pago=None, comprobante_referencia=None, observaciones=None):
    """
    Actualiza los detalles de un pago.
    
    Args:
        pago_id: ID del pago
        monto_pagado: Nuevo monto (opcional)
        fecha_pago: Nueva fecha (opcional)
        comprobante_referencia: Nueva referencia (opcional)
        observaciones: Nuevas observaciones (opcional)
        
    Returns:
        Tuple[Pago, error]: Pago actualizado y mensaje de error si aplica
    """
    try:
        pago = Pago.query.get(pago_id)
        if not pago:
            return None, f"Pago con ID {pago_id} no encontrado"
        
        if monto_pagado is not None:
            pago.monto_pagado = monto_pagado
        if fecha_pago is not None:
            pago.fecha_pago = fecha_pago
        if comprobante_referencia is not None:
            pago.comprobante_referencia = comprobante_referencia
        if observaciones is not None:
            pago.observaciones = observaciones
        
        db.session.commit()
        return pago, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error al actualizar pago: {str(e)}"


def devolver_pago(pago_id):
    """
    Marca un pago como devuelto.
    
    Args:
        pago_id: ID del pago
        
    Returns:
        Tuple[Pago, error]: Pago devuelto y mensaje de error si aplica
    """
    try:
        pago = Pago.query.get(pago_id)
        if not pago:
            return None, f"Pago con ID {pago_id} no encontrado"
        
        pago.estado = EstadoPagoEnum.DEVUELTO
        
        # Actualizar la cuota
        cuota = pago.cuota
        cuota.monto_pagado = None
        cuota.fecha_pago = None
        
        db.session.commit()
        return pago, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error al devolver pago: {str(e)}"


def eliminar_pago(pago_id):
    """
    Elimina un pago y restaura el estado de la cuota.
    
    Args:
        pago_id: ID del pago
        
    Returns:
        Tuple[success, error]: Boolean indicando éxito y mensaje de error si aplica
    """
    try:
        pago = Pago.query.get(pago_id)
        if not pago:
            return False, f"Pago con ID {pago_id} no encontrado"
        
        # Restaurar la cuota
        cuota = pago.cuota
        cuota.monto_pagado = None
        cuota.fecha_pago = None
        
        db.session.delete(pago)
        db.session.commit()
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error al eliminar pago: {str(e)}"
