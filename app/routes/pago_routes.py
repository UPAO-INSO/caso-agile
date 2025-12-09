"""
Rutas API para Pagos
Endpoints para registrar y gestionar pagos de cuotas
"""
from flask import request, jsonify
from datetime import date
from decimal import Decimal
import logging

from app.routes import pagos_bp
from app.services.pago_service import PagoService

logger = logging.getLogger(__name__)


@pagos_bp.route('/registrar', methods=['POST'])
def registrar_pago():
    """
    Registra un pago para una cuota de un préstamo.
    
    Body esperado:
    {
        "prestamo_id": int,
        "cuota_id": int,
        "monto_pagado": float,
        "medio_pago": string ("EFECTIVO", "TARJETA_DEBITO", etc.),
        "fecha_pago": "YYYY-MM-DD" (opcional)
    }
    """
    try:
        datos = request.get_json()
        
        if not datos:
            return jsonify({
                'success': False,
                'error': 'Datos incompletos'
            }), 400
        
        # Validar campos requeridos
        prestamo_id = datos.get('prestamo_id')
        cuota_id = datos.get('cuota_id')
        monto_pagado_raw = datos.get('monto_pagado')
        medio_pago = datos.get('medio_pago')
        
        if not all([prestamo_id, cuota_id, monto_pagado_raw, medio_pago]):
            return jsonify({
                'error': 'Faltan campos requeridos: prestamo_id, cuota_id, monto_pagado, medio_pago'
            }), 400
        
        # Convertir tipos
        try:
            prestamo_id = int(prestamo_id)
            cuota_id = int(cuota_id)
            monto_pagado = Decimal(str(monto_pagado_raw))
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Tipos de datos inválidos para prestamo_id, cuota_id o monto_pagado'
            }), 400
        
        # Validar medio de pago
        medios_validos = ['EFECTIVO', 'TARJETA_DEBITO', 'TARJETA_CREDITO', 
                         'TRANSFERENCIA', 'BILLETERA_ELECTRONICA', 'PAGO_AUTOMATICO']
        if medio_pago not in medios_validos:
            return jsonify({
                'error': f'Medio de pago inválido. Valores permitidos: {", ".join(medios_validos)}'
            }), 400
        
        # Procesar fecha (opcional)
        fecha_pago = None
        if 'fecha_pago' in datos and datos['fecha_pago']:
            try:
                fecha_pago = date.fromisoformat(datos['fecha_pago'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        
        # Registrar el pago (sin comprobante ni observaciones del frontend)
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id,
            cuota_id,
            monto_pagado,
            medio_pago,
            fecha_pago
        )
        
        if error:
            return jsonify({'error': error}), status_code
        
        return jsonify(respuesta), status_code
        
    except Exception as exc:
        logger.error(f"Error en registrar_pago: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


@pagos_bp.route('/resumen/<int:prestamo_id>', methods=['GET'])
def obtener_resumen_pagos(prestamo_id):
    """Obtiene un resumen de los pagos de un préstamo."""
    try:
        respuesta, error, status_code = PagoService.obtener_resumen_pagos_prestamo(prestamo_id)
        
        if error:
            return jsonify({'error': error}), status_code
        
        return jsonify(respuesta), status_code
        
    except Exception as exc:
        logger.error(f"Error en obtener_resumen_pagos: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500