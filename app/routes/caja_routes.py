# → Rutas para caja_routes.py   

import logging
from datetime import date, datetime
from flask import Blueprint, jsonify, request
from app.services.caja_service import CajaService

logger = logging.getLogger(__name__)

caja_bp = Blueprint('caja', __name__, url_prefix='/caja')

# → Obtiene el resumen de caja por fecha
@caja_bp.route('/resumen/diario', methods=['GET'])
def obtener_resumen_diario():
    """
    Query params:
        fecha (opcional): Fecha en formato YYYY-MM-DD. Por defecto: hoy
        
    Response:
    {
        "fecha": "2025-12-08",
        "detalle_por_medio": [
            {
                "medio_pago": "efectivo",
                "cantidad_pagos": 5,
                "total": 5000.00,
                "total_mora": 150.00,
                "total_capital": 4850.00
            }
        ],
        "resumen": {
            "cantidad_total_pagos": 10,
            "total_recaudado": 10000.00,
            "total_mora_cobrada": 300.00,
            "total_capital_cobrado": 9700.00
        }
    }
    """
    try:
        fecha_str = request.args.get('fecha')
        
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        else:
            fecha = date.today()
        
        resumen = CajaService.obtener_resumen_diario(fecha)
        return jsonify(resumen), 200
        
    except Exception as exc:
        logger.error(f"Error en obtener_resumen_diario: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


@caja_bp.route('/resumen/periodo', methods=['GET'])
def obtener_resumen_periodo():
    """
    Query params:
        fecha_inicio (requerido): Fecha inicial YYYY-MM-DD
        fecha_fin (requerido): Fecha final YYYY-MM-DD
        
    Response:
    {
        "periodo": {
            "fecha_inicio": "2025-12-01",
            "fecha_fin": "2025-12-08"
        },
        "detalle_por_dia": [
            {
                "fecha": "2025-12-01",
                "medios": [...],
                "total_dia": 5000.00,
                "cantidad_dia": 5
            }
        ],
        "resumen_periodo": {
            "cantidad_total_pagos": 50,
            "total_recaudado": 50000.00,
            "total_mora_cobrada": 1500.00,
            "total_capital_cobrado": 48500.00,
            "dias_con_movimiento": 8
        }
    }
    """
    try:
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')
        
        if not fecha_inicio_str or not fecha_fin_str:
            return jsonify({'error': 'Debe proporcionar fecha_inicio y fecha_fin'}), 400
        
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        
        if fecha_inicio > fecha_fin:
            return jsonify({'error': 'La fecha_inicio no puede ser mayor que fecha_fin'}), 400
        
        resumen = CajaService.obtener_resumen_periodo(fecha_inicio, fecha_fin)
        return jsonify(resumen), 200
        
    except Exception as exc:
        logger.error(f"Error en obtener_resumen_periodo: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

# → Obtiene el detalle de pagos por fecha
@caja_bp.route('/detalle/diario', methods=['GET'])
def obtener_detalle_diario():
    """
    Query params:
        fecha (opcional): Fecha en formato YYYY-MM-DD. Por defecto: hoy
        
    Response:
    [
        {
            "pago_id": 1,
            "hora": "14:30:00",
            "comprobante": "COMP-001-2025",
            "cliente": {
                "nombre": "Juan Pérez",
                "dni": "12345678"
            },
            "prestamo_id": 1,
            "cuota_numero": 3,
            "medio_pago": "efectivo",
            "monto_pagado": 1052.59,
            "monto_mora": 52.59,
            "monto_capital": 1000.00,
            "observaciones": "Pago parcial"
        }
    ]
    """
    try:
        fecha_str = request.args.get('fecha')
        
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        else:
            fecha = date.today()
        
        detalle = CajaService.obtener_detalle_pagos_dia(fecha)
        return jsonify(detalle), 200
        
    except Exception as exc:
        logger.error(f"Error en obtener_detalle_diario: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

# → Obtiene estadísticas generales de caja - últimos 30 días
@caja_bp.route('/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """
    Response:
    {
        "periodo_analisis": "30 días",
        "total_recaudado_30d": 150000.00,
        "dias_con_movimiento": 25,
        "promedio_diario": 6000.00,
        "medio_pago_mas_usado": "efectivo",
        "veces_usado": 150
    }
    """
    try:
        estadisticas = CajaService.obtener_estadisticas_caja()
        return jsonify(estadisticas), 200
        
    except Exception as exc:
        logger.error(f"Error en obtener_estadisticas: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
