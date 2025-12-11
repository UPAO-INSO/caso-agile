# → Rutas para caja_routes.py   

import logging
from datetime import date, datetime
from flask import jsonify, request, render_template, session
from app.common.auth_decorators import login_required
from app.routes import caja_bp
from app.services.caja_service import CajaService

logger = logging.getLogger(__name__)

# → Vista principal de cuadre de caja
@caja_bp.route('/', methods=['GET'])
@caja_bp.route('/cuadre', methods=['GET'])
@login_required
def cuadre_caja():
    """Vista principal del cuadre de caja"""
    return render_template('pages/caja/cuadre.html', 
                         title='Cuadre de Caja',
                         fecha_hoy=date.today())

# → Obtiene el resumen de caja por fecha
@caja_bp.route('/resumen/diario', methods=['GET'])
@login_required
def obtener_resumen_diario():
    """
    Query params:
        fecha (opcional): Fecha en formato YYYY-MM-DD. Por defecto: hoy
        
    Response:
    {
        "fecha": "2025-12-08",
        "detalle_por_medio": [
            {
                "medio_pago": "EFECTIVO",
                "cantidad_pagos": 5,
                "total": 5000.00,
                "total_mora": 150.00,
                "total_capital": 4850.00,
                "ajuste_redondeo": 0.10
            }
        ],
        "resumen": {
            "cantidad_total_pagos": 10,
            "total_recaudado": 10000.00,
            "total_mora_cobrada": 300.00,
            "total_capital_cobrado": 9700.00,
            "total_ajuste_redondeo": 0.10,
            "nota_ajuste": "Positivo = ganancia del negocio, Negativo = condonación al cliente"
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
@login_required
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
                "medios": [{"ajuste_redondeo": 0.05, ...}],
                "total_dia": 5000.00,
                "ajuste_dia": 0.05,
                "cantidad_dia": 5
            }
        ],
        "resumen_periodo": {
            "cantidad_total_pagos": 50,
            "total_recaudado": 50000.00,
            "total_mora_cobrada": 1500.00,
            "total_capital_cobrado": 48500.00,
            "total_ajuste_redondeo": 0.50,
            "dias_con_movimiento": 8,
            "nota_ajuste": "Positivo = ganancia del negocio, Negativo = condonación al cliente"
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
@login_required
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
            "medio_pago": "EFECTIVO",
            "monto_contable": 1052.58,
            "monto_pagado": 1052.60,
            "ajuste_redondeo": 0.02,
            "monto_mora": 52.59,
            "monto_capital": 1000.00,
            "observaciones": "Pago completo con redondeo"
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
@login_required
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

# → DEBUG: Obtiene TODOS los pagos para verificar fechas
@caja_bp.route('/debug/todos-pagos', methods=['GET'])
@login_required
def debug_todos_pagos():
    """Endpoint de debug para ver todos los pagos registrados"""
    try:
        from app.models import Pago
        from app.common.extensions import db
        
        pagos = db.session.query(Pago).order_by(Pago.pago_id.desc()).limit(50).all()
        
        resultado = []
        for pago in pagos:
            resultado.append({
                'pago_id': pago.pago_id,
                'fecha_pago': pago.fecha_pago.isoformat() if pago.fecha_pago else None,
                'monto_pagado': float(pago.monto_pagado),
                'ajuste_redondeo': float(pago.ajuste_redondeo),
                'medio_pago': pago.medio_pago.value,
                'cuota_id': pago.cuota_id
            })
        
        return jsonify({
            'total_pagos': len(resultado),
            'pagos': resultado
        }), 200
        
    except Exception as exc:
        logger.error(f"Error en debug_todos_pagos: {exc}", exc_info=True)
        return jsonify({'error': str(exc)}), 500


@caja_bp.route('/egreso', methods=['POST'])
@login_required
def registrar_egreso_route():
    """Registra un egreso (por ejemplo: vuelto entregado al cliente).
    Espera JSON: { monto: number, concepto: string, pago_id?: int }
    """
    try:
        data = request.get_json() or {}
        monto = data.get('monto')
        concepto = data.get('concepto')
        pago_id = data.get('pago_id')

        if monto is None or concepto is None:
            return jsonify({'error': 'Debe proporcionar monto y concepto'}), 400

        try:
            from decimal import Decimal
            monto_dec = Decimal(str(monto))
        except Exception:
            return jsonify({'error': 'Monto inválido'}), 400

        usuario_id = session.get('usuario_id')

        egreso = CajaService.registrar_egreso(monto_dec, concepto, pago_id=pago_id, usuario_id=usuario_id)
        return jsonify({'success': True, 'egreso': egreso}), 201

    except Exception as exc:
        logger.error(f"Error en registrar_egreso_route: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno al registrar egreso'}), 500


@caja_bp.route('/cierre', methods=['GET'])
@login_required
def obtener_estado_cierre_route():
    """Devuelve si la caja está cerrada para la fecha dada."""
    try:
        fecha_str = request.args.get('fecha')
        if not fecha_str:
            fecha = date.today()
        else:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400

        estado = CajaService.obtener_estado_cierre(fecha)
        return jsonify({'cierre': estado}), 200
    except Exception as exc:
        logger.error(f"Error en obtener_estado_cierre_route: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


@caja_bp.route('/cierre', methods=['POST'])
@login_required
def cerrar_caja_route():
    """Cierra la caja para la fecha dada. JSON: { fecha: 'YYYY-MM-DD', monto_real: number }"""
    try:
        data = request.get_json() or {}
        fecha_str = data.get('fecha')
        monto_real = data.get('monto_real')

        if not fecha_str or monto_real is None:
            return jsonify({'error': 'Debe proporcionar fecha y monto_real'}), 400

        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400

        from decimal import Decimal
        try:
            monto_dec = Decimal(str(monto_real))
        except Exception:
            return jsonify({'error': 'Monto inválido'}), 400

        usuario_id = session.get('usuario_id')
        resultado = CajaService.cerrar_caja(fecha, monto_dec, usuario_id=usuario_id)
        return jsonify({'success': True, 'cierre': resultado}), 200

    except Exception as exc:
        logger.error(f"Error en cerrar_caja_route: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno al cerrar caja'}), 500


@caja_bp.route('/abrir', methods=['POST'])
@login_required
def abrir_caja_route():
    """Reabre la caja para la fecha indicada. JSON: { fecha: 'YYYY-MM-DD' }"""
    try:
        data = request.get_json() or {}
        fecha_str = data.get('fecha')
        if not fecha_str:
            fecha = date.today()
        else:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400

        CajaService.abrir_caja(fecha)
        return jsonify({'success': True, 'message': 'Caja abierta correctamente'}), 200

    except Exception as exc:
        logger.error(f"Error en abrir_caja_route: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno al abrir caja'}), 500


@caja_bp.route('/apertura', methods=['GET'])
@login_required
def obtener_apertura():
    """Obtiene la apertura de caja para una fecha dada. Query param: fecha=YYYY-MM-DD"""
    try:
        fecha_str = request.args.get('fecha')
        if not fecha_str:
            fecha = date.today()
        else:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400

        apertura = CajaService.obtener_apertura_por_fecha(fecha)
        return jsonify({'apertura': apertura}), 200

    except Exception as exc:
        logger.error(f"Error en obtener_apertura: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


@caja_bp.route('/apertura', methods=['POST'])
@login_required
def registrar_apertura_route():
    """Registra o actualiza la apertura de caja. JSON: { fecha: 'YYYY-MM-DD', monto: number }"""
    try:
        data = request.get_json() or {}
        fecha_str = data.get('fecha')
        monto = data.get('monto')

        if not fecha_str or monto is None:
            return jsonify({'error': 'Debe proporcionar fecha y monto'}), 400

        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400

        try:
            from decimal import Decimal
            monto_dec = Decimal(str(monto))
        except Exception:
            return jsonify({'error': 'Monto inválido'}), 400

        usuario_id = session.get('usuario_id')

        apertura = CajaService.registrar_apertura(fecha, monto_dec, usuario_id=usuario_id)
        return jsonify({'success': True, 'apertura': apertura}), 201

    except Exception as exc:
        logger.error(f"Error en registrar_apertura_route: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno al registrar apertura'}), 500
