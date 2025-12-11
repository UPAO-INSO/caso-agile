"""
Financial Routes - Endpoints para servicios financieros
Endpoints para simulaciones y cálculos financieros
"""
from flask import jsonify, request
from datetime import datetime
from decimal import Decimal
import logging

from app.routes import api_v1_bp
from app.services.financial_service import FinancialService
from app.common.error_handler import ErrorHandler

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)


@api_v1_bp.route('/financial/simular-cronograma', methods=['POST'])
def simular_cronograma():
    """
    Simula un cronograma de pagos sin crear el préstamo.
    
    Request body:
    {
        "monto": 12000.00,
        "plazo": 12,
        "tea": 10.0
    }
    
    Response:
    {
        "cronograma": [
            {
                "numero_cuota": 1,
                "fecha_vencimiento": "2026-01-09",
                "monto_cuota": "1102.28",
                "monto_capital": "918.57",
                "monto_interes": "183.71",
                "saldo_capital": "11081.43",
                "dias": 30
            },
            ...
        ],
        "resumen": {
            "monto_prestado": "12000.00",
            "total_intereses": "1227.36",
            "total_a_pagar": "13227.36",
            "cuota_regular": "1102.28",
            "tea": "10.00",
            "tem": "0.7974"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_handler.respond('Datos inválidos', 400)
        
        # Validar campos requeridos
        monto = data.get('monto')
        plazo = data.get('plazo')
        tea = data.get('tea', 10.0)  # Default 10% TEA
        
        if not monto or not plazo:
            return error_handler.respond('Monto y plazo son requeridos', 400)
        
        # Convertir a tipos apropiados
        try:
            monto_decimal = Decimal(str(monto))
            plazo_int = int(plazo)
            tea_decimal = Decimal(str(tea))
        except (ValueError, TypeError) as e:
            return error_handler.respond(f'Formato de datos inválido: {str(e)}', 400)
        
        # Validaciones de negocio
        if monto_decimal <= 0:
            return error_handler.respond('El monto debe ser mayor a 0', 400)
        
        if plazo_int <= 0 or plazo_int > 60:
            return error_handler.respond('El plazo debe estar entre 1 y 60 meses', 400)
        
        if tea_decimal < 0 or tea_decimal > 100:
            return error_handler.respond('La TEA debe estar entre 0% y 100%', 400)
        
        # Generar cronograma usando el servicio financiero
        fecha_otorgamiento = datetime.now().date()
        cronograma = FinancialService.generar_cronograma_pagos(
            monto_total=monto_decimal,
            interes_tea=tea_decimal,
            plazo=plazo_int,
            f_otorgamiento=fecha_otorgamiento
        )
        
        if not cronograma:
            return error_handler.respond('Error al generar el cronograma', 500)
        
        # Calcular resumen
        total_capital = sum(Decimal(str(c['monto_capital'])) for c in cronograma)
        total_interes = sum(Decimal(str(c['monto_interes'])) for c in cronograma)
        total_cuotas = sum(Decimal(str(c['monto_cuota'])) for c in cronograma)
        
        # Calcular TEM para el resumen
        tem = FinancialService.tea_to_tem(tea_decimal)
        
        # Preparar respuesta
        cronograma_json = []
        for cuota in cronograma:
            cronograma_json.append({
                'numero_cuota': cuota['numero_cuota'],
                'fecha_vencimiento': cuota['fecha_vencimiento'].strftime('%d/%m/%Y'),  # Formato: 09/01/2026
                'monto_cuota': str(cuota['monto_cuota']),
                'monto_capital': str(cuota['monto_capital']),
                'monto_interes': str(cuota['monto_interes']),
                'saldo_capital': str(cuota['saldo_capital']),
                'dias': cuota.get('dias', 30),
                'es_cuota_ajuste': cuota.get('es_cuota_ajuste', False)
            })
        
        resumen = {
            'monto_prestado': str(monto_decimal),
            'total_intereses': str(total_interes),
            'total_a_pagar': str(total_cuotas),
            'cuota_regular': str(cronograma[0]['monto_cuota']) if cronograma else '0.00',
            'tea': str(tea_decimal),
            'tem': f"{(tem * 100):.4f}"
        }
        
        return jsonify({
            'cronograma': cronograma_json,
            'resumen': resumen,
            'mensaje': f'Cronograma simulado exitosamente: {plazo_int} cuotas de 30 días'
        }), 200
        
    except Exception as e:
        logger.error(f"Error al simular cronograma: {str(e)}", exc_info=True)
        return error_handler.respond(f'Error interno al simular cronograma: {str(e)}', 500)


@api_v1_bp.route('/financial/calcular-cuota', methods=['POST'])
def calcular_cuota():
    """
    Calcula la cuota mensual fija de un préstamo.
    
    Request body:
    {
        "monto": 10000.00,
        "plazo": 12,
        "tea": 10.0
    }
    
    Response:
    {
        "cuota_mensual": "878.57",
        "tem": "0.7974",
        "total_intereses": "542.84",
        "total_a_pagar": "10542.84"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_handler.respond('Datos inválidos', 400)
        
        monto = Decimal(str(data.get('monto', 0)))
        plazo = int(data.get('plazo', 0))
        tea = Decimal(str(data.get('tea', 10.0)))
        
        if monto <= 0 or plazo <= 0:
            return error_handler.respond('Monto y plazo deben ser mayores a 0', 400)
        
        # Calcular cuota
        cuota = FinancialService.calcular_cuota_fija(monto, tea, plazo)
        tem = FinancialService.tea_to_tem(tea)
        
        total_a_pagar = cuota * plazo
        total_intereses = total_a_pagar - monto
        
        return jsonify({
            'cuota_mensual': str(cuota),
            'tem': f"{(tem * 100):.4f}",
            'total_intereses': str(total_intereses),
            'total_a_pagar': str(total_a_pagar)
        }), 200
        
    except Exception as e:
        logger.error(f"Error al calcular cuota: {str(e)}")
        return error_handler.respond(str(e), 500)
