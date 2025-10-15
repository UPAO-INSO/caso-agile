import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Valor de la UIT (Unidad Impositiva Tributaria) - Perú 2025
# S/ 5,350.00
UIT_VALOR = Decimal('5350.00')

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def tea_to_tem(tea):
    tea_decimal = Decimal(tea) / Decimal('100.00')
    tem = ((Decimal('1') + tea_decimal) ** (Decimal('1') / Decimal('12'))) - Decimal('1')
    return tem


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
    cuota_fija = calcular_cuota_fija(monto_total, interes_tea, plazo)  # puede venir redondeada
    tem = tea_to_tem(interes_tea)

    saldo = monto_total   # saldo pendiente al inicio de cada periodo
    cronograma = []

    for i in range(1, plazo + 1):
        fecha_vencimiento = f_otorgamiento + relativedelta(months=i)

        monto_interes_un = saldo * tem

        monto_capital_un = cuota_fija - monto_interes_un

        if i == plazo:
            monto_capital_un = saldo
            cuota_un = monto_capital_un + monto_interes_un
            saldo_final_un = Decimal('0.00')
        else:
            cuota_un = cuota_fija
            saldo_final_un = saldo - monto_capital_un

        monto_interes = monto_interes_un.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        monto_capital = monto_capital_un.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        cuota_a_usar = cuota_un.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        saldo_capital_final = saldo_final_un.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        cronograma.append({
            'numero_cuota': i,
            'fecha_vencimiento': fecha_vencimiento,
            'monto_cuota': cuota_a_usar,
            'monto_capital': monto_capital,
            'monto_interes': monto_interes,
            'saldo_capital': saldo_capital_final,
        })

        saldo = saldo_final_un

    return cronograma