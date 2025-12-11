"""
Rutas para webhooks y callbacks de Flow API
"""
from flask import Blueprint, request, jsonify, redirect, url_for
from app.services.flow_service import FlowService
from app.services.pago_service import PagoService
from app.common.extensions import db
from app.models.pago import Pago
from datetime import datetime
import logging
import json

flow_bp = Blueprint('flow', __name__, url_prefix='/flow')
logger = logging.getLogger(__name__)

@flow_bp.route('/webhook/confirmation', methods=['POST'])
def flow_confirmation():
    """
    Webhook de Flow para notificar estado de pago
    Flow envía: token (POST form-urlencoded)
    """
    try:
        # Obtener token del POST
        token = request.form.get('token')
        
        if not token:
            logger.error("Webhook Flow sin token")
            return jsonify({'error': 'Token requerido'}), 400
        
        logger.info(f"Webhook Flow recibido: token={token}")
        
        # Consultar estado del pago en Flow
        payment_data, error, status_code = FlowService.obtener_estado_pago(token)
        
        if error:
            logger.error(f"Error al consultar Flow: {error}")
            return jsonify({'error': error}), status_code
        
        # Extraer información del optional (prestamo_id, cuota_numero, medio_pago)
        optional = payment_data.get('optional', {})
        if isinstance(optional, str):
            optional = json.loads(optional)
        
        prestamo_id = optional.get('prestamo_id')
        cuota_numero = optional.get('cuota_numero')
        medio_pago_original = optional.get('medio_pago')
        
        if not prestamo_id or not cuota_numero:
            logger.error(f"Datos incompletos en optional: {optional}")
            return jsonify({'error': 'Datos incompletos en orden'}), 400
        
        # Verificar estado del pago
        flow_status = payment_data.get('status')
        
        if flow_status == 1:  # Pagado
            logger.info(f"Pago Flow exitoso: Order={payment_data.get('flow_order')} Prestamo={prestamo_id} Cuota={cuota_numero}")
            
            # Buscar si ya existe un pago registrado con este commerce_order
            commerce_order = payment_data.get('commerce_order')
            pago_existente = Pago.query.filter_by(
                comprobante_referencia=commerce_order
            ).first()
            
            if pago_existente:
                logger.warning(f"Pago ya procesado: {commerce_order}")
                return jsonify({'message': 'Pago ya procesado'}), 200
            
            # Registrar el pago automáticamente
            monto_pagado = payment_data.get('amount')
            fecha_pago = datetime.now().date()
            
            # Obtener hora del pago de Flow
            hora_pago = None
            if payment_data.get('payment_date'):
                try:
                    payment_datetime = datetime.fromisoformat(payment_data['payment_date'].replace('Z', '+00:00'))
                    hora_pago = payment_datetime.time()
                except:
                    hora_pago = datetime.now().time()
            else:
                hora_pago = datetime.now().time()
            
            # Registrar pago con PagoService
            respuesta, error_pago, status_pago = PagoService.registrar_pago_cuota(
                prestamo_id=prestamo_id,
                cuota_numero=cuota_numero,
                monto_pagado=monto_pagado,
                medio_pago=medio_pago_original or 'TRANSFERENCIA',
                fecha_pago=fecha_pago,
                comprobante_referencia=commerce_order,
                observaciones=f'Pago Flow #{payment_data.get("flow_order")} - {payment_data.get("media")}',
                hora_pago=hora_pago,
                monto_dado=None,  # No aplica para pagos digitales
                vuelto=0  # No aplica para pagos digitales
            )
            
            if error_pago:
                logger.error(f"Error al registrar pago Flow: {error_pago}")
                return jsonify({'error': error_pago}), status_pago
            
            logger.info(f"Pago Flow registrado exitosamente: Pago ID={respuesta.get('pago_id')}")
            
            return jsonify({
                'success': True,
                'message': 'Pago procesado exitosamente',
                'pago_id': respuesta.get('pago_id')
            }), 200
            
        elif flow_status == 2:  # Rechazado
            logger.warning(f"Pago Flow rechazado: Order={payment_data.get('flow_order')}")
            return jsonify({
                'success': False,
                'message': 'Pago rechazado'
            }), 200
            
        else:  # Pendiente u otro estado
            logger.info(f"Pago Flow en estado {flow_status}: Order={payment_data.get('flow_order')}")
            return jsonify({
                'success': False,
                'message': 'Pago pendiente'
            }), 200
            
    except Exception as e:
        logger.error(f"Error en webhook Flow: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


@flow_bp.route('/return', methods=['GET', 'POST'])
def flow_return():
    """
    URL de retorno después del pago
    Flow redirige aquí: ?token=XXX (GET o POST)
    """
    try:
        # Flow puede enviar el token por GET o POST
        token = request.args.get('token') or request.form.get('token')
        
        if not token:
            return redirect(url_for('main.home') + '?error=token_missing')
        
        logger.info(f"Usuario retornado de Flow: token={token}")
        
        # Consultar estado del pago
        payment_data, error, status_code = FlowService.obtener_estado_pago(token)
        
        if error:
            logger.error(f"Error al consultar estado: {error}")
            return redirect(url_for('main.home') + f'?error={error}')
        
        # Extraer prestamo_id del optional
        optional = payment_data.get('optional', {})
        if isinstance(optional, str):
            optional = json.loads(optional)
        
        prestamo_id = optional.get('prestamo_id')
        flow_status = payment_data.get('status')
        
        if flow_status == 1:  # Pagado
            # Redirigir a página de préstamo con mensaje de éxito
            if prestamo_id:
                return redirect(url_for('prestamos_view.ver_prestamo_view', prestamo_id=prestamo_id) + '?pago_exitoso=1&metodo=flow')
            else:
                return redirect(url_for('main.home') + '?pago_exitoso=1')
        elif flow_status == 2:  # Rechazado
            if prestamo_id:
                return redirect(url_for('prestamos_view.ver_prestamo_view', prestamo_id=prestamo_id) + '?pago_rechazado=1')
            else:
                return redirect(url_for('main.home') + '?pago_rechazado=1')
        else:  # Pendiente
            if prestamo_id:
                return redirect(url_for('prestamos_view.ver_prestamo_view', prestamo_id=prestamo_id) + '?pago_pendiente=1')
            else:
                return redirect(url_for('main.home') + '?pago_pendiente=1')
            
    except Exception as e:
        logger.error(f"Error en return de Flow: {e}", exc_info=True)
        return redirect(url_for('main.home') + '?error=server_error')
