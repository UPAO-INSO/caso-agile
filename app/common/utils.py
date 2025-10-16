"""
Common Utilities
Funciones de utilidad compartidas.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Importar servicio financiero para reutilizar lógica
from app.services.financial_service import FinancialService

# Valor de la UIT (Unidad Impositiva Tributaria) - Perú 2025
UIT_VALOR = Decimal('5350.00')

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def tea_to_tem(tea):
    """Convierte TEA a TEM usando FinancialService"""
    return FinancialService.tea_to_tem(tea)


def calcular_cuota_fija(monto, tea, plazo_meses):
    try:
        if plazo_meses <= 0 or monto <= 0 or tea < 0:
            logger.error(f"Error de validación en calcular_cuota_fija: monto={monto}, tea={tea}, plazo={plazo_meses}. Valores deben ser positivos.")
            return Decimal('0.00')

        # Calcular TEM
        tem = tea_to_tem(tea)

        if tem == Decimal('0'):
            return (monto / plazo_meses).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        factor_num = tem * (Decimal('1') + tem) ** plazo_meses
        factor_den = (Decimal('1') + tem) ** plazo_meses - Decimal('1')

        if factor_den == Decimal('0'):
            logger.error(f"Error matemático en calcular_cuota_fija: factor_den es cero. TEM={tem}, Plazo={plazo_meses}")
            return Decimal('0.00') 


        cuota = monto * (factor_num / factor_den)
        return cuota.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    except InvalidOperation as e:
        logger.error(f"Error de operación Decimal en calcular_cuota_fija: {e}. Entrada: monto={monto}, tea={tea}, plazo={plazo_meses}", exc_info=True)
        return Decimal('0.00')
        
    except Exception as e:
        logger.error(f"Error inesperado en calcular_cuota_fija: {e}. Entrada: monto={monto}, tea={tea}, plazo={plazo_meses}", exc_info=True)
        return Decimal('0.00')


def generar_cronograma_pagos(monto_total, interes_tea, plazo, f_otorgamiento):
    """
    Genera cronograma de pagos.
    
    REFACTORED: Ahora delega al FinancialService para mayor consistencia.
    Este wrapper se mantiene por compatibilidad legacy.
    
    Args:
        monto_total: Monto del préstamo
        interes_tea: TEA en porcentaje
        plazo: Número de cuotas
        f_otorgamiento: Fecha de otorgamiento
        
    Returns:
        list: Cronograma de pagos con formato ajustado para BD
    """
    # Delegar a FinancialService
    cronograma_servicio = FinancialService.generar_cronograma_pagos(
        monto_total, interes_tea, plazo, f_otorgamiento
    )
    
    # Adaptar formato para compatibilidad con código existente
    cronograma_legacy = []
    for item in cronograma_servicio:
        # Convertir formato del servicio a formato legacy esperado por la BD
        from datetime import datetime
        fecha_vencimiento = datetime.strptime(item['fecha_vencimiento'], '%Y-%m-%d').date()
        
        cronograma_legacy.append({
            'numero_cuota': item['numero'],
            'fecha_vencimiento': fecha_vencimiento,
            'monto_cuota': Decimal(str(item['monto_cuota'])),
            'monto_capital': Decimal(str(item['capital'])),
            'monto_interes': Decimal(str(item['interes'])),
            'saldo_capital': Decimal(str(item['saldo']))
        })
    
    return cronograma_legacy