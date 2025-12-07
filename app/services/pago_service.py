"""
Servicio de Pagos
Maneja la lógica de negocio relacionada con pagos de cuotas
"""
import logging
from typing import Tuple, Optional, Dict, Any, List
from datetime import date
from decimal import Decimal

from app.common.extensions import db
from app.models import Pago, Cuota, Prestamo, EstadoPrestamoEnum
from app.crud.pago_crud import (
    registrar_pago,
    obtener_pago_por_id,
    listar_pagos_por_cuota,
    listar_pagos_por_prestamo,
    obtener_pagos_pendientes_por_prestamo,
    actualizar_pago,
    devolver_pago
)

logger = logging.getLogger(__name__)


class PagoService:
    """Servicio para manejar la lógica de negocios de pagos"""
    
    @staticmethod
    def validar_prestamo_vigente(prestamo_id: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que un préstamo esté vigente.
        
        Args:
            prestamo_id: ID del préstamo
            
        Returns:
            Tuple[es_vigente, error]: Boolean y mensaje de error si aplica
        """
        prestamo = Prestamo.query.get(prestamo_id)
        
        if not prestamo:
            return False, f"Préstamo con ID {prestamo_id} no encontrado"
        
        if prestamo.estado != EstadoPrestamoEnum.VIGENTE:
            return False, f"El préstamo no está vigente. Estado actual: {prestamo.estado.value}"
        
        return True, None
    
    @staticmethod
    def validar_cuota_pertenece_prestamo(cuota_id: int, prestamo_id: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que una cuota pertenezca a un préstamo específico.
        
        Args:
            cuota_id: ID de la cuota
            prestamo_id: ID del préstamo
            
        Returns:
            Tuple[pertenece, error]: Boolean y mensaje de error si aplica
        """
        cuota = Cuota.query.get(cuota_id)
        
        if not cuota:
            return False, f"Cuota con ID {cuota_id} no encontrada"
        
        if cuota.prestamo_id != prestamo_id:
            return False, f"La cuota {cuota_id} no pertenece al préstamo {prestamo_id}"
        
        return True, None
    
    @staticmethod
    def validar_monto_pago(monto_pagado: Decimal, monto_cuota: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Valida que el monto del pago sea válido.
        
        Args:
            monto_pagado: Monto a pagar
            monto_cuota: Monto de la cuota
            
        Returns:
            Tuple[valido, error]: Boolean y mensaje de error si aplica
        """
        if monto_pagado <= 0:
            return False, "El monto del pago debe ser mayor a cero"
        
        if monto_pagado > monto_cuota:
            return False, f"El monto del pago ({monto_pagado}) no puede exceder el monto de la cuota ({monto_cuota})"
        
        return True, None
    
    @staticmethod
    def registrar_pago_cuota(
        prestamo_id: int,
        cuota_id: int,
        monto_pagado: Decimal,
        fecha_pago: Optional[date] = None,
        comprobante_referencia: Optional[str] = None,
        observaciones: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Registra un pago de una cuota de un préstamo.
        
        Validaciones:
        1. El préstamo debe estar vigente
        2. La cuota debe pertenecer al préstamo
        3. El monto debe ser válido
        4. La cuota no debe estar ya pagada
        
        Args:
            prestamo_id: ID del préstamo
            cuota_id: ID de la cuota
            monto_pagado: Monto del pago
            fecha_pago: Fecha del pago (por defecto hoy)
            comprobante_referencia: Referencia del comprobante (opcional)
            observaciones: Observaciones del pago (opcional)
            
        Returns:
            Tuple[respuesta_dict, error, status_code]: Diccionario con datos del pago,
                                                       mensaje de error si aplica,
                                                       código HTTP de respuesta
        """
        try:
            # 1. Validar que el préstamo existe y está vigente
            es_vigente, error = PagoService.validar_prestamo_vigente(prestamo_id)
            if not es_vigente:
                return None, error, 400
            
            # 2. Validar que la cuota existe y pertenece al préstamo
            pertenece, error = PagoService.validar_cuota_pertenece_prestamo(cuota_id, prestamo_id)
            if not pertenece:
                return None, error, 400
            
            # Obtener la cuota
            cuota = Cuota.query.get(cuota_id)
            
            # 3. Validar que la cuota no está pagada
            if cuota.monto_pagado and cuota.monto_pagado > 0:
                return None, f"La cuota {cuota.numero_cuota} ya fue pagada", 400
            
            # 4. Validar el monto del pago
            valido, error = PagoService.validar_monto_pago(monto_pagado, cuota.monto_cuota)
            if not valido:
                return None, error, 400
            
            # 5. Registrar el pago
            nuevo_pago, error_pago = registrar_pago(
                cuota_id,
                monto_pagado,
                fecha_pago,
                comprobante_referencia,
                observaciones
            )
            
            if error_pago:
                return None, error_pago, 500
            
            # 6. Preparar respuesta
            respuesta = {
                'success': True,
                'message': f'Pago registrado exitosamente para la cuota {cuota.numero_cuota}',
                'pago': nuevo_pago.to_dict(),
                'cuota': {
                    'cuota_id': cuota.cuota_id,
                    'numero_cuota': cuota.numero_cuota,
                    'monto_cuota': float(cuota.monto_cuota),
                    'monto_pagado': float(nuevo_pago.monto_pagado),
                    'fecha_vencimiento': cuota.fecha_vencimiento.isoformat(),
                    'fecha_pago': nuevo_pago.fecha_pago.isoformat()
                }
            }
            
            return respuesta, None, 201
            
        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error en registrar_pago_cuota: {exc}", exc_info=True)
            return None, f'Error al registrar el pago: {str(exc)}', 500
    
    @staticmethod
    def obtener_resumen_pagos_prestamo(prestamo_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Obtiene un resumen de los pagos de un préstamo.
        
        Args:
            prestamo_id: ID del préstamo
            
        Returns:
            Tuple[respuesta_dict, error, status_code]: Diccionario con resumen de pagos
        """
        try:
            # Validar que el préstamo existe
            prestamo = Prestamo.query.get(prestamo_id)
            if not prestamo:
                return None, f"Préstamo con ID {prestamo_id} no encontrado", 404
            
            # Obtener todas las cuotas
            cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
            
            if not cuotas:
                return None, "No hay cuotas para este préstamo", 404
            
            # Calcular estadísticas
            total_cuotas = len(cuotas)
            cuotas_pagadas = len([c for c in cuotas if c.monto_pagado and c.monto_pagado > 0])
            cuotas_pendientes = total_cuotas - cuotas_pagadas
            
            monto_total = sum(Decimal(c.monto_cuota) for c in cuotas)
            monto_pagado = sum(Decimal(c.monto_pagado) if c.monto_pagado else 0 for c in cuotas)
            monto_pendiente = monto_total - monto_pagado
            
            # Obtener pagos registrados
            pagos = listar_pagos_por_prestamo(prestamo_id)
            
            respuesta = {
                'success': True,
                'prestamo_id': prestamo_id,
                'resumen': {
                    'total_cuotas': total_cuotas,
                    'cuotas_pagadas': cuotas_pagadas,
                    'cuotas_pendientes': cuotas_pendientes,
                    'monto_total': float(monto_total),
                    'monto_pagado': float(monto_pagado),
                    'monto_pendiente': float(monto_pendiente),
                    'porcentaje_pagado': round((float(monto_pagado) / float(monto_total) * 100), 2) if monto_total > 0 else 0
                },
                'pagos': [p.to_dict() for p in pagos],
                'cuotas_pendientes': [
                    {
                        'cuota_id': c.cuota_id,
                        'numero_cuota': c.numero_cuota,
                        'fecha_vencimiento': c.fecha_vencimiento.isoformat(),
                        'monto_cuota': float(c.monto_cuota),
                        'estado': 'PAGADA' if c.monto_pagado and c.monto_pagado > 0 else 'PENDIENTE'
                    }
                    for c in sorted(cuotas, key=lambda x: x.numero_cuota)
                    if not c.monto_pagado or c.monto_pagado == 0
                ]
            }
            
            return respuesta, None, 200
            
        except Exception as exc:
            logger.error(f"Error en obtener_resumen_pagos_prestamo: {exc}", exc_info=True)
            return None, f'Error al obtener resumen de pagos: {str(exc)}', 500
