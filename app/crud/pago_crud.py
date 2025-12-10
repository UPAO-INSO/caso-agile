import logging
from typing import Tuple, Optional, List, Dict, Any
from datetime import date
from decimal import Decimal

from app.common.extensions import db
from app.models import Pago, Cuota, MedioPagoEnum, MetodoPagoEnum

logger = logging.getLogger(__name__)


def registrar_pago(
    cuota_id: int,
    monto_pagado: Decimal,
    fecha_pago: Optional[date] = None,
    hora_pago=None,
    medio_pago: MedioPagoEnum = MedioPagoEnum.TRANSFERENCIA,
    monto_mora: Decimal = Decimal('0.00'),
    monto_contable: Optional[Decimal] = None,
    ajuste_redondeo: Decimal = Decimal('0.00'),
    monto_dado: Optional[Decimal] = None,
    vuelto: Decimal = Decimal('0.00'),
    comprobante_referencia: Optional[str] = None,
    observaciones: Optional[str] = None
) -> Tuple[Optional[Pago], Optional[str]]:
    """
    Registra un nuevo pago en la base de datos.
    
    Args:
        cuota_id: ID de la cuota
        monto_pagado: Monto pagado (lo que se aplica a la deuda)
        fecha_pago: Fecha del pago
        hora_pago: Hora del pago
        medio_pago: Medio de pago (enum)
        monto_mora: Monto de mora pagado
        monto_contable: Monto contable original (antes de redondeo)
        ajuste_redondeo: Ajuste por redondeo según Ley N° 29571
        monto_dado: Monto entregado por el cliente (billetes) - EFECTIVO
        vuelto: Vuelto entregado al cliente
        comprobante_referencia: Referencia del comprobante (generado internamente)
        observaciones: Observaciones (uso interno)
        
    Returns:
        Tuple[Pago creado, mensaje de error si aplica]
    """
    try:
        cuota = Cuota.query.get(cuota_id)
        if not cuota:
            return None, f"Cuota {cuota_id} no encontrada"

        fecha_pago = fecha_pago or date.today()

        # Asegurar que medio_pago es un enum
        if isinstance(medio_pago, str):
            medio_pago = MedioPagoEnum[medio_pago]

        # Determinar metodo_pago basado en medio_pago
        if medio_pago == MedioPagoEnum.EFECTIVO:
            metodo_pago = MetodoPagoEnum.EFECTIVO
        elif medio_pago in [MedioPagoEnum.TARJETA_DEBITO, MedioPagoEnum.TARJETA_CREDITO]:
            metodo_pago = MetodoPagoEnum.TARJETA
        else:  # TRANSFERENCIA, BILLETERA_ELECTRONICA, PAGO_AUTOMATICO
            metodo_pago = MetodoPagoEnum.TRANSFERENCIA

        pago = Pago(
            cuota_id=cuota_id,
            monto_pagado=monto_pagado,
            monto_contable=monto_contable,
            ajuste_redondeo=ajuste_redondeo,
            fecha_pago=fecha_pago,
            hora_pago=hora_pago,
            monto_dado=monto_dado,
            vuelto=vuelto,
            comprobante_referencia=comprobante_referencia,
            observaciones=observaciones,
            metodo_pago=metodo_pago,
            medio_pago=medio_pago,
            monto_mora=monto_mora
        )

        db.session.add(pago)
        db.session.commit()

        logger.info(f"Pago registrado: ID={pago.pago_id}, Cuota={cuota_id}, Monto={monto_pagado}, Mora={monto_mora}")

        return pago, None

    except Exception as exc:
        db.session.rollback()
        logger.error(f"Error al registrar pago: {exc}")
        return None, str(exc)


def obtener_pago_por_id(pago_id: int) -> Optional[Pago]:
    """Obtiene un pago por su ID"""
    try:
        return Pago.query.get(pago_id)
    except Exception as exc:
        logger.error(f"Error al obtener pago {pago_id}: {exc}")
        return None


def listar_pagos_por_cuota(cuota_id: int) -> List[Pago]:
    """Lista todos los pagos de una cuota"""
    try:
        return Pago.query.filter_by(cuota_id=cuota_id).all()
    except Exception as exc:
        logger.error(f"Error al listar pagos de cuota {cuota_id}: {exc}")
        return []


def listar_pagos_por_prestamo(prestamo_id: int) -> List[Pago]:
    """Lista todos los pagos de un préstamo"""
    try:
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
        cuota_ids = [c.cuota_id for c in cuotas]
        return Pago.query.filter(Pago.cuota_id.in_(cuota_ids)).all()
    except Exception as exc:
        logger.error(f"Error al listar pagos de préstamo {prestamo_id}: {exc}")
        return []


def obtener_pagos_pendientes_por_prestamo(prestamo_id: int) -> List[Pago]:
    """Obtiene pagos pendientes de un préstamo"""
    try:
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
        cuota_ids = [c.cuota_id for c in cuotas]
        return Pago.query.filter(
            Pago.cuota_id.in_(cuota_ids),
            Pago.estado == 'PENDIENTE'
        ).all()
    except Exception as exc:
        logger.error(f"Error al obtener pagos pendientes: {exc}")
        return []


def actualizar_pago(
    pago_id: int,
    **campos
) -> Tuple[Optional[Pago], Optional[str]]:
    # ...existing code...
    try:
        pago = Pago.query.get(pago_id)
        if not pago:
            return None, f"Pago {pago_id} no encontrado"

        for campo, valor in campos.items():
            if hasattr(pago, campo):
                setattr(pago, campo, valor)

        db.session.commit()
        logger.info(f"Pago {pago_id} actualizado")
        return pago, None

    except Exception as exc:
        db.session.rollback()
        logger.error(f"Error al actualizar pago {pago_id}: {exc}")
        return None, str(exc)

def devolver_pago(pago_id: int) -> Tuple[bool, Optional[str]]:
    """Devuelve/anula un pago registrado"""
    try:
        pago = Pago.query.get(pago_id)
        if not pago:
            return False, f"Pago {pago_id} no encontrado"

        cuota = Cuota.query.get(pago.cuota_id)
        if not cuota:
            return False, f"Cuota {pago.cuota_id} no encontrada"

        # Restaurar saldo pendiente
        cuota.saldo_pendiente += pago.monto_pagado
        
        # Reducir monto pagado
        cuota.monto_pagado = (cuota.monto_pagado or 0) - pago.monto_pagado
        
        # Restaurar mora
        cuota.mora_acumulada = (cuota.mora_acumulada or 0) + pago.monto_mora

        db.session.delete(pago)
        db.session.commit()

        logger.info(f"Pago {pago_id} devuelto/anulado")
        return True, None

    except Exception as exc:
        db.session.rollback()
        logger.error(f"Error al devolver pago {pago_id}: {exc}")
        return False, str(exc)