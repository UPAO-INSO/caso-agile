"""
Servicio de Cálculo de Mora
Implementa la lógica de negocio para calcular mora según RF4
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Tuple, Optional

from app.models import Cuota

logger = logging.getLogger(__name__)


class MoraService:
    """Servicio para calcular mora de cuotas"""
    
    TASA_MORA_MENSUAL = Decimal('0.01')  # 1% mensual
    DIAS_POR_MES = 30  # 1 mes = 30 días exactos
    
    @staticmethod
    def calcular_mora_cuota(cuota: Cuota, fecha_pago_actual: date) -> Tuple[Decimal, int]:
        """
        Calcula la mora de una cuota según RF4.
        
        Reglas:
        - Mora es 1% mensual sobre el monto de CAPITAL de la cuota
        - No es acumulativa
        - Si hay pago parcial en el mes de vencimiento, se anula la mora
        - Mora se aplica apenas pase la fecha de vencimiento
        
        Args:
            cuota: Objeto Cuota
            fecha_pago_actual: Fecha del pago que se está realizando
            
        Returns:
            Tuple[monto_mora, dias_mora]: Monto de mora y días de atraso
        """
        try:
            # Si no hay fecha de vencimiento, no hay mora |Esto está pa checar, ta raro
            if not cuota.fecha_vencimiento:
                return Decimal('0.00'), 0
            
            # Si se paga antes o en la fecha de vencimiento, no hay mora
            if fecha_pago_actual <= cuota.fecha_vencimiento:
                return Decimal('0.00'), 0
            
            # Si ya se pagó algo en el mes de vencimiento, no hay mora
            if cuota.fecha_pago and MoraService._es_mismo_mes(cuota.fecha_pago, cuota.fecha_vencimiento):
                return Decimal('0.00'), 0
            
            # Calcular días de atraso
            dias_atraso = (fecha_pago_actual - cuota.fecha_vencimiento).days
          
            # Calcular mora: 1% sobre el monto de la cuota (no acumulativa)
            monto_mora = cuota.monto_capital * MoraService.TASA_MORA_MENSUAL
            
            logger.info(f"Mora calculada para cuota {cuota.cuota_id}: {monto_mora} ({dias_atraso} días de atraso)")

            return monto_mora, dias_atraso
            
        except Exception as exc:
            logger.error(f"Error en calcular_mora_cuota: {exc}", exc_info=True)
            return Decimal('0.00'), 0
    
    @staticmethod
    def _es_mismo_mes(fecha1: date, fecha2: date) -> bool:
        """Verifica si dos fechas están en el mismo mes y año"""
        return fecha1.year == fecha2.year and fecha1.month == fecha2.month
    
    @staticmethod
    def calcular_saldo_pendiente(cuota: Cuota, monto_pagado: Decimal, monto_mora: Decimal) -> Decimal:
        """
        Calcula el saldo pendiente después de un pago.
        
        Args:
            cuota: Objeto Cuota
            monto_pagado: Monto que se está pagando
            monto_mora: Monto de mora calculado
            
        Returns:
            Saldo pendiente
        """
        try:
            # Total a pagar = monto de cuota + mora
            total_a_pagar = cuota.monto_cuota + monto_mora
            
            # Saldo pendiente = total - pagado
            saldo = total_a_pagar - monto_pagado
            
            # El saldo no puede ser negativo
            return max(Decimal('0.00'), saldo)
            
        except Exception as exc:
            logger.error(f"Error en calcular_saldo_pendiente: {exc}", exc_info=True)
            return cuota.monto_cuota