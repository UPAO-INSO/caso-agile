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
        "numero_cuota": int,
        "monto_pagado": float (monto que desea pagar),
        "metodo_pago": string (EFECTIVO, TARJETA, TRANSFERENCIA) - opcional, default EFECTIVO,
        "medio_pago": string ("EFECTIVO", "TARJETA_DEBITO", etc.),
        "fecha_pago": "YYYY-MM-DD" (opcional),
        "hora_pago": "HH:MM" (opcional),
        "monto_dado": float (billetes entregados - solo EFECTIVO),
        "vuelto": float (opcional, se calcula automáticamente)
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
        numero_cuota = datos.get('numero_cuota')
        monto_pagado = datos.get('monto_pagado')
        medio_pago = datos.get('medio_pago')
        
        if not all([prestamo_id, numero_cuota, monto_pagado, medio_pago]):
            return jsonify({
                'error': 'Faltan campos requeridos: prestamo_id, numero_cuota, monto_pagado, medio_pago'
            }), 400
        
        # Convertir tipos
        try:
            prestamo_id = int(prestamo_id)
            numero_cuota = int(numero_cuota)
            monto_pagado = Decimal(str(monto_pagado))
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Tipos de datos inválidos para prestamo_id, numero_cuota o monto_pagado'
            }), 400
        
        # Buscar la cuota por número
        from app.models import Cuota
        cuota = Cuota.query.filter_by(prestamo_id=prestamo_id, numero_cuota=numero_cuota).first()
        if not cuota:
            return jsonify({
                'error': f'Cuota {numero_cuota} no encontrada para el préstamo {prestamo_id}'
            }), 404
        
        cuota_id = cuota.cuota_id
        
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
        
        # Procesar hora (opcional)
        from datetime import time as dt_time
        hora_pago = None
        if 'hora_pago' in datos and datos['hora_pago']:
            try:
                hora_str = datos['hora_pago']
                hora_parts = hora_str.split(':')
                hora_pago = dt_time(int(hora_parts[0]), int(hora_parts[1]))
            except (ValueError, TypeError, IndexError):
                return jsonify({'error': 'Formato de hora inválido. Use HH:MM'}), 400
        
        # Procesar monto_dado y calcular vuelto (solo para EFECTIVO)
        monto_dado = None
        vuelto = Decimal('0.00')
        if medio_pago == 'EFECTIVO':
            if 'monto_dado' in datos and datos['monto_dado']:
                try:
                    monto_dado = Decimal(str(datos['monto_dado']))
                    if monto_dado < monto_pagado:
                        return jsonify({'error': 'El monto dado debe ser mayor o igual al monto a pagar'}), 400
                    vuelto = monto_dado - monto_pagado
                except (ValueError, TypeError):
                    return jsonify({'error': 'Tipo de dato inválido para monto_dado'}), 400
        
        # Procesar comprobante y observaciones (opcionales)
        comprobante_referencia = datos.get('comprobante_referencia')
        observaciones = datos.get('observaciones')
        
        # Registrar el pago con el nuevo sistema
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id,
            cuota_id,
            monto_pagado,
            medio_pago,
            fecha_pago,
            comprobante_referencia,
            observaciones,
            hora_pago,
            monto_dado,
            vuelto
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
