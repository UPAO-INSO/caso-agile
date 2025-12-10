"""
Servicio de integración con Flow API para pagos digitales
Soporta: Transferencias, Tarjetas D/C, Billeteras Digitales (Yape/Plin)
"""
import hmac
import hashlib
import requests
from typing import Dict, Optional, Tuple
from decimal import Decimal
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class FlowService:
    """Servicio para gestionar pagos con Flow API"""
    
    # Credenciales hardcodeadas desde .env
    API_KEY = "55BE7F9B-6F16-40BD-972E-57AE8L4C6C0E"
    SECRET_KEY = "a6cc47b739746a35bde300ba829337f7f5391767"
    SANDBOX_URL = "https://sandbox.flow.cl/api"
    PROD_URL = "https://www.flow.cl/api"
    
    # Mapeo de medios de pago a paymentMethod de Flow
    PAYMENT_METHOD_MAP = {
        'TRANSFERENCIA': 9,  # Todos los medios (incluye transferencias)
        'TARJETA_DEBITO': 9,  # Webpay permite débito/crédito
        'TARJETA_CREDITO': 9,  # Webpay permite débito/crédito
        'YAPE': 9,  # Flow soporta billeteras digitales
        'PLIN': 9,  # Flow soporta billeteras digitales
    }
    
    @classmethod
    def _get_api_url(cls) -> str:
        """Retorna URL base del API según entorno"""
        # Usar sandbox en desarrollo
        env = current_app.config.get('FLASK_ENV', 'production')
        return cls.SANDBOX_URL if env == 'development' else cls.PROD_URL
    
    @classmethod
    def _sign_params(cls, params: Dict) -> str:
        """
        Firma los parámetros con HMAC-SHA256 según documentación Flow
        
        Proceso:
        1. Ordenar parámetros alfabéticamente
        2. Concatenar: nombre_param + valor
        3. Firmar con HMAC-SHA256
        """
        # Ordenar por clave alfabéticamente
        sorted_keys = sorted(params.keys())
        
        # Concatenar: clave1valor1clave2valor2...
        string_to_sign = ""
        for key in sorted_keys:
            string_to_sign += str(key) + str(params[key])
        
        # Firmar con HMAC-SHA256
        signature = hmac.new(
            cls.SECRET_KEY.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"String to sign: {string_to_sign}")
        logger.debug(f"Signature: {signature}")
        
        return signature
    
    @classmethod
    def crear_orden_pago(
        cls,
        commerce_order: str,
        subject: str,
        amount: Decimal,
        email: str,
        medio_pago: str,
        prestamo_id: int,
        cuota_numero: int,
        url_confirmation: str,
        url_return: str
    ) -> Tuple[Optional[Dict], Optional[str], int]:
        """
        Crea una orden de pago en Flow
        
        Args:
            commerce_order: ID único de orden del comercio
            subject: Descripción del pago
            amount: Monto a pagar
            email: Email del pagador
            medio_pago: Tipo de pago (TRANSFERENCIA, TARJETA_DEBITO, etc)
            prestamo_id: ID del préstamo
            cuota_numero: Número de cuota
            url_confirmation: URL callback para notificación
            url_return: URL de retorno después del pago
            
        Returns:
            (response_dict, error_msg, status_code)
        """
        try:
            # Validar medio de pago
            if medio_pago not in cls.PAYMENT_METHOD_MAP:
                return None, f"Medio de pago {medio_pago} no soportado por Flow", 400
            
            # Construir parámetros (sin firma todavía)
            params = {
                'apiKey': cls.API_KEY,
                'commerceOrder': commerce_order,
                'subject': subject,
                'currency': 'PEN',  # Soles peruanos (PEN) para Perú
                'amount': int(amount),  # Flow requiere entero (centavos)
                'email': email,
                'paymentMethod': cls.PAYMENT_METHOD_MAP[medio_pago],
                'urlConfirmation': url_confirmation,
                'urlReturn': url_return,
                'optional': f'{{"prestamo_id":{prestamo_id},"cuota_numero":{cuota_numero},"medio_pago":"{medio_pago}"}}'
            }
            
            # Firmar parámetros
            params['s'] = cls._sign_params(params)
            
            # Construir URL del endpoint
            url = f"{cls._get_api_url()}/payment/create"
            
            logger.info(f"Creando orden Flow: {commerce_order} - Monto: {amount} - Medio: {medio_pago}")
            
            # Hacer request POST
            response = requests.post(url, data=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Orden Flow creada exitosamente: {data.get('flowOrder')}")
                
                # Flow retorna: url, token, flowOrder
                # Construir URL de pago: url?token=XXX
                payment_url = f"{data['url']}?token={data['token']}"
                
                return {
                    'success': True,
                    'flow_order': data.get('flowOrder'),
                    'token': data.get('token'),
                    'payment_url': payment_url,
                    'commerce_order': commerce_order
                }, None, 200
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('message', 'Error desconocido de Flow')
                logger.error(f"Error Flow API: {response.status_code} - {error_msg}")
                return None, error_msg, response.status_code
                
        except requests.exceptions.Timeout:
            logger.error("Timeout al conectar con Flow API")
            return None, "Timeout de conexión con Flow", 504
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión con Flow: {e}")
            return None, f"Error de conexión: {str(e)}", 503
        except Exception as e:
            logger.error(f"Error inesperado en crear_orden_pago: {e}", exc_info=True)
            return None, f"Error interno: {str(e)}", 500
    
    @classmethod
    def obtener_estado_pago(cls, token: str) -> Tuple[Optional[Dict], Optional[str], int]:
        """
        Obtiene el estado de un pago mediante su token
        
        Args:
            token: Token de la transacción enviado por Flow
            
        Returns:
            (payment_status_dict, error_msg, status_code)
        """
        try:
            # Construir parámetros
            params = {
                'apiKey': cls.API_KEY,
                'token': token
            }
            
            # Firmar parámetros
            params['s'] = cls._sign_params(params)
            
            # Construir URL del endpoint
            url = f"{cls._get_api_url()}/payment/getStatus"
            
            logger.info(f"Consultando estado de pago Flow: token={token}")
            
            # Hacer request GET
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Estado de pago obtenido: Order={data.get('flowOrder')} Status={data.get('status')}")
                
                return {
                    'flow_order': data.get('flowOrder'),
                    'commerce_order': data.get('commerceOrder'),
                    'status': data.get('status'),  # 1=pagado, 2=rechazado, 3=pendiente
                    'amount': Decimal(data.get('amount', 0)),
                    'currency': data.get('currency'),
                    'payer': data.get('payer'),
                    'payment_date': data.get('paymentData', {}).get('date'),
                    'media': data.get('paymentData', {}).get('media'),
                    'fee': Decimal(data.get('paymentData', {}).get('fee', 0)),
                    'balance': Decimal(data.get('paymentData', {}).get('balance', 0)),
                    'optional': data.get('optional', {})
                }, None, 200
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('message', 'Error al consultar estado')
                logger.error(f"Error Flow API getStatus: {response.status_code} - {error_msg}")
                return None, error_msg, response.status_code
                
        except Exception as e:
            logger.error(f"Error al obtener estado de pago: {e}", exc_info=True)
            return None, f"Error interno: {str(e)}", 500
    
    @classmethod
    def validar_webhook_signature(cls, params: Dict, signature: str) -> bool:
        """
        Valida la firma del webhook de Flow
        
        Args:
            params: Parámetros recibidos (sin 's')
            signature: Firma recibida en parámetro 's'
            
        Returns:
            True si la firma es válida
        """
        try:
            expected_signature = cls._sign_params(params)
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if not is_valid:
                logger.warning(f"Firma inválida en webhook. Esperada: {expected_signature}, Recibida: {signature}")
            
            return is_valid
        except Exception as e:
            logger.error(f"Error validando firma de webhook: {e}")
            return False
