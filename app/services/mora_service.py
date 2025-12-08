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
        try:
            if not cuota.fecha_vencimiento:
                return Decimal("0.00"), 0

            # ---- FIX: Forzar carga de pagos ----
            try:
                _ = cuota.pagos
            except:
                cuota.pagos = []
            # ------------------------------------

            fecha_venc = cuota.fecha_vencimiento
            monto_capital = Decimal(cuota.monto_capital)

            # 1) Si paga antes o en fecha → NO mora
            if fecha_pago_actual <= fecha_venc:
                return Decimal("0.00"), 0

            # 2) Pago parcial dentro del mes del vencimiento → anula mora
            for p in (cuota.pagos or []):
                if (
                    p.fecha_pago
                    and p.monto_pagado is not None
                    and p.monto_pagado > 0
                    and p.fecha_pago.year == fecha_venc.year
                    and p.fecha_pago.month == fecha_venc.month
                ):
                    return Decimal("0.00"), 0

            # 3) Calcular días de atraso
            dias_atraso = (fecha_pago_actual - fecha_venc).days

            # 4) Determinar meses vencidos
            meses_vencidos = dias_atraso // 30
            if meses_vencidos < 1:
                meses_vencidos = 1

            # 5) Mora
            monto_mora = (monto_capital * Decimal("0.01") * meses_vencidos).quantize(Decimal("0.00"))

            return monto_mora, dias_atraso

        except Exception as exc:
            logger.error(f"Error en calcular_mora_cuota: {exc}", exc_info=True)
            return Decimal("0.00"), 0

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