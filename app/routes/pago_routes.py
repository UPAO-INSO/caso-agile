"""
Rutas API para Pagos
Endpoints para registrar y gestionar pagos de cuotas
MÓDULO 2: Soporte para métodos de pago y redondeo legal
"""
from flask import request, jsonify
from datetime import date
from decimal import Decimal
import logging

from app.routes import pagos_bp
from app.services.pago_service import PagoService
from app.models import MetodoPagoEnum

logger = logging.getLogger(__name__)


@pagos_bp.route('/registrar', methods=['POST'])
def registrar_pago():
    """
    MÓDULO 2: Registra un pago para una cuota con soporte de método de pago.
    
    Body esperado:
    {
        "prestamo_id": int,
        "cuota_id": int,
        "metodo_pago": string (EFECTIVO, TARJETA, TRANSFERENCIA) - opcional, default EFECTIVO,
        "fecha_pago": "YYYY-MM-DD" (opcional),
        "comprobante_referencia": string (opcional),
        "observaciones": string (opcional)
    }
    
    Lógica de Pago:
    - EFECTIVO: Aplica Ley N° 29571 (redondeo a favor del consumidor al múltiplo de S/ 0.05)
    - TARJETA/TRANSFERENCIA: Monto exacto sin redondeo
    
    Returns:
        JSON con datos del pago registrado, incluyendo información de conciliación contable
    """
    try:
        datos = request.get_json()
        
        if not datos:
            return jsonify({'error': 'No se proporcionó JSON'}), 400
        
        # Validar campos requeridos
        prestamo_id = datos.get('prestamo_id')
        cuota_id = datos.get('cuota_id')
        
        if not all([prestamo_id, cuota_id]):
            return jsonify({
                'error': 'Faltan campos requeridos: prestamo_id, cuota_id'
            }), 400
        
        # Convertir tipos
        try:
            prestamo_id = int(prestamo_id)
            cuota_id = int(cuota_id)
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Tipos de datos inválidos para prestamo_id o cuota_id'
            }), 400
        
        # Procesar método de pago (opcional, default EFECTIVO)
        metodo_pago_str = datos.get('metodo_pago', 'EFECTIVO').upper()
        try:
            metodo_pago = MetodoPagoEnum[metodo_pago_str]
        except KeyError:
            return jsonify({
                'error': f'Método de pago inválido. Valores permitidos: EFECTIVO, TARJETA, TRANSFERENCIA'
            }), 400
        
        # Procesar fecha (opcional)
        fecha_pago = None
        if 'fecha_pago' in datos and datos['fecha_pago']:
            try:
                fecha_pago = date.fromisoformat(datos['fecha_pago'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        
        # Procesar comprobante y observaciones (opcionales)
        comprobante_referencia = datos.get('comprobante_referencia')
        observaciones = datos.get('observaciones')
        
        # Registrar el pago con el nuevo sistema
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id,
            cuota_id,
            metodo_pago,
            fecha_pago,
            comprobante_referencia,
            observaciones
        )
        
        if error:
            return jsonify({'error': error}), status_code
        
        return jsonify(respuesta), status_code
        
    except Exception as exc:
        logger.error(f"Error en registrar_pago: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


@pagos_bp.route('/resumen/<int:prestamo_id>', methods=['GET'])
def obtener_resumen_pagos(prestamo_id):
    """
    Obtiene un resumen de los pagos de un préstamo.
    
    Returns:
        JSON con resumen de pagos, cuotas pagadas y pendientes
    """
    try:
        respuesta, error, status_code = PagoService.obtener_resumen_pagos_prestamo(prestamo_id)
        
        if error:
            return jsonify({'error': error}), status_code
        
        return jsonify(respuesta), status_code
        
    except Exception as exc:
        logger.error(f"Error en obtener_resumen_pagos: {exc}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
