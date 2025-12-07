"""
Common Utilities
Funciones de utilidad compartidas.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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

def generar_cronograma_pdf(nombre_cliente, monto, cuotas, tasa_interes):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, 750, "Cronograma de Pagos")

    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Cliente: {nombre_cliente}")
    p.drawString(100, 700, f"Monto del préstamo: S/ {monto:.2f}")
    p.drawString(100, 680, f"Tasa de interés mensual: {tasa_interes}%")
    p.drawString(100, 660, f"Número de cuotas: {cuotas}")

    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, 630, "N°")
    p.drawString(150, 630, "Fecha de Pago")
    p.drawString(300, 630, "Monto (S/)")
    p.setFont("Helvetica", 12)

    # Simular cuotas mensuales
    monto_cuota = round((monto * (1 + (tasa_interes / 100))) / cuotas, 2)
    fecha_pago = datetime.now()

    for i in range(cuotas):
        p.drawString(100, 610 - (i * 20), str(i + 1))
        p.drawString(150, 610 - (i * 20), (fecha_pago + timedelta(days=30*i)).strftime("%d/%m/%Y"))
        p.drawString(300, 610 - (i * 20), f"{monto_cuota:.2f}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer