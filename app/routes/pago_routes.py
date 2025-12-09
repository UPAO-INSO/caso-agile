"""
Rutas API para Pagos
Endpoints para registrar y gestionar pagos de cuotas
MÓDULO 2: Soporte para métodos de pago y redondeo legal
"""
from flask import request, jsonify, send_file
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
        "medio_pago": string ("EFECTIVO", "TARJETA_DEBITO", etc.),
        "fecha_pago": "YYYY-MM-DD" (opcional)
    }
    
    Returns:
        JSON con datos del pago registrado o error
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
        medio_pago = datos.get('medio_pago')
        
        if not all([prestamo_id, cuota_id, medio_pago]):
            return jsonify({
                'error': 'Faltan campos requeridos: prestamo_id, cuota_id, medio_pago'
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
        
        # Validar medio de pago
        medios_validos = ['EFECTIVO', 'TARJETA_DEBITO', 'TARJETA_CREDITO', 
                         'TRANSFERENCIA', 'BILLETERA_ELECTRONICA', 'PAGO_AUTOMATICO']
        if medio_pago not in medios_validos:
            return jsonify({
                'error': f'Medio de pago inválido. Valores permitidos: {", ".join(medios_validos)}'
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
        
        # Procesar comprobante y observaciones (opcionales)
        comprobante_referencia = datos.get('comprobante_referencia')
        observaciones = datos.get('observaciones')
        
        # Registrar el pago con el nuevo sistema
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id,
            cuota_id,
            metodo_pago,
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
