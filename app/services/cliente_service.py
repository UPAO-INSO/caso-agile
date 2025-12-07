"""
Servicio de Clientes
Maneja la lógica de negocio relacionada con clientes
"""
import os
import logging
from typing import Tuple, Optional, Dict, Any
import requests

from app.extensions import db
from app.models import Cliente
from app.services.pep_service import PEPService

logger = logging.getLogger(__name__)


class ClienteService:
    """Servicio para manejar la lógica de negocios de clientes"""
    
    # Configuración API RENIEC
    API_URL = os.environ.get('DNI_API_URL')
    API_KEY = os.environ.get('DNI_API_KEY')
    
    @staticmethod
    def validar_configuracion_api() -> Tuple[bool, Optional[str]]:
        """
        Valida que las credenciales de API estén configuradas.
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if not ClienteService.API_URL or not ClienteService.API_KEY:
            error = "Error de configuración: Las credenciales de la API no están configuradas. " \
                   "Por favor, configure DNI_API_URL y DNI_API_KEY en las variables de entorno."
            return False, error
        return True, None
    
    @staticmethod
    def consultar_dni_reniec(dni: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Consulta la API de RENIEC (APIPERU) para obtener datos de un DNI.
        
        Args:
            dni: Número de documento de identidad
            
        Returns:
            Tuple[datos, error]: Diccionario con datos del ciudadano o mensaje de error
            
        Formato de respuesta:
        {
            'nombres': 'JUAN',
            'apellido_paterno': 'PEREZ',
            'apellido_materno': 'GARCIA',
            'nombre_completo': 'JUAN PEREZ GARCIA',
            'numero': '12345678'
        }
        """
        # Validar configuración
        es_valido, error = ClienteService.validar_configuracion_api()
        if not es_valido:
            return None, error
        
        try:
            url_completa = f"{ClienteService.API_URL}/{dni}"
            headers = {
                "Authorization": f"Bearer {ClienteService.API_KEY}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            respuesta = requests.get(url_completa, headers=headers, timeout=10)
            
            # Verificar tipo de contenido
            content_type = respuesta.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                return None, "DNI no encontrado en RENIEC"
            
            respuesta.raise_for_status()
            api_data = respuesta.json()
            
            # Verificar éxito de la consulta
            if not api_data.get("success", False):
                mensaje = api_data.get("message", "DNI no encontrado en RENIEC")
                return None, mensaje
            
            # Normalizar datos
            data = api_data.get('data', {})
            datos_normalizados = {
                'nombres': data.get('nombres', ''),
                'apellido_paterno': data.get('apellido_paterno', ''),
                'apellido_materno': data.get('apellido_materno', ''),
                'nombre_completo': data.get('nombre_completo', ''),
                'numero': data.get('numero', dni)
            }
            
            return datos_normalizados, None
            
        except requests.exceptions.Timeout:
            return None, "Tiempo de espera agotado al consultar RENIEC"
        except requests.exceptions.RequestException as exc:
            logger.error(f"Error de conexión con RENIEC: {exc}", exc_info=True)
            return None, f"Error de conexión con RENIEC: {str(exc)}"
        except Exception as exc:
            logger.error(f"Error al consultar DNI: {exc}", exc_info=True)
            return None, f"Error al consultar DNI: {str(exc)}"
    
    @staticmethod
    def validar_pep_cliente(dni: str, pep_declarado: bool) -> Tuple[bool, bool, Optional[str]]:
        """
        Valida si un cliente es PEP consultando el dataset oficial.
        
        Args:
            dni: Número de documento
            pep_declarado: Si el cliente declaró ser PEP
            
        Returns:
            Tuple[pep_final, pep_validado, advertencia]: 
                - pep_final: Resultado final (True si es PEP por cualquier razón)
                - pep_validado: Si está en el dataset oficial
                - advertencia: Mensaje de advertencia si hay discrepancia
        """
        pep_validado = PEPService.validar_pep(dni)
        pep_final = pep_validado or pep_declarado
        advertencia = None
        
        # Detectar discrepancias
        if pep_declarado != pep_validado:
            if pep_validado:
                advertencia = "CUIDADO: El cliente declaró NO ser PEP pero está en el dataset oficial"
            else:
                advertencia = "El cliente declaró ser PEP pero no está en el dataset oficial " \
                            "(puede ser PEP por otros motivos)"
        
        return pep_final, pep_validado, advertencia
    
    @staticmethod
    def crear_cliente_completo(
        dni: str,
        correo_electronico: str,
        pep_declarado: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Crea un nuevo cliente consultando RENIEC y validando PEP.
        
        Args:
            dni: Número de documento de identidad
            correo_electronico: Email del cliente
            pep_declarado: Si el cliente declaró ser PEP
            
        Returns:
            Tuple[cliente_dict, error]: Diccionario con datos del cliente o mensaje de error
        """
        # Validar si ya existe
        cliente_existente = Cliente.query.filter_by(dni=dni).first()
        if cliente_existente:
            return None, "El cliente ya existe"
        
        # Consultar RENIEC
        info_cliente, error = ClienteService.consultar_dni_reniec(dni)
        if error:
            return None, error
        
        # Validar PEP
        pep_final, pep_validado, advertencia = ClienteService.validar_pep_cliente(
            dni, 
            pep_declarado
        )
        
        # Crear cliente en BD
        try:
            nuevo_cliente = Cliente(
                dni=dni,
                nombre_completo=info_cliente.get('nombre_completo', ''),
                apellido_paterno=info_cliente.get('apellido_paterno', ''),
                apellido_materno=info_cliente.get('apellido_materno', ''),
                correo_electronico=correo_electronico,
                pep=pep_final
            )
            
            db.session.add(nuevo_cliente)
            db.session.commit()
            
            # Preparar respuesta completa
            cliente_dict = nuevo_cliente.to_dict()
            cliente_dict['pep_declarado'] = pep_declarado
            cliente_dict['pep_validado_dataset'] = pep_validado
            cliente_dict['pep_final'] = pep_final
            
            if advertencia:
                cliente_dict['advertencia'] = advertencia
            
            logger.info(f"Cliente creado exitosamente: DNI {dni}, PEP: {pep_final}")
            return cliente_dict, None
            
        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error al guardar cliente: {exc}", exc_info=True)
            return None, f"Error al guardar el cliente: {str(exc)}"
    
    @staticmethod
    def crear_cliente_minimo(dni: str, correo_electronico: Optional[str] = None) -> Tuple[Optional[Cliente], Optional[str]]:
        """
        Crea un cliente con datos mínimos cuando RENIEC no responde.
        
        Args:
            dni: Número de documento
            correo_electronico: Email opcional
            
        Returns:
            Tuple[Cliente, error]: Cliente creado o mensaje de error
        """
        try:
            # Validar PEP al menos
            pep_validado = PEPService.validar_pep(dni)
            
            nuevo_cliente = Cliente(
                dni=dni,
                nombre_completo=f"Cliente {dni}",
                apellido_paterno="PENDIENTE",
                apellido_materno="ACTUALIZACIÓN",
                correo_electronico=correo_electronico or f"{dni}@pendiente.com",
                pep=pep_validado
            )
            
            db.session.add(nuevo_cliente)
            db.session.commit()
            
            logger.warning(f"Cliente creado con datos mínimos: DNI {dni}")
            return nuevo_cliente, None
            
        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error al crear cliente mínimo: {exc}", exc_info=True)
            return None, f"Error al crear cliente: {str(exc)}"
    
    @staticmethod
    def obtener_o_crear_cliente(dni: str, correo_electronico: Optional[str] = None) -> Tuple[Optional[Cliente], Optional[str]]:
        """
        Obtiene un cliente existente o lo crea si no existe.
        
        Intenta:
        1. Buscar cliente existente
        2. Crear consultando RENIEC
        3. Si falla RENIEC, crear con datos mínimos
        
        Args:
            dni: Número de documento
            correo_electronico: Email opcional
            
        Returns:
            Tuple[Cliente, error]: Cliente obtenido/creado o mensaje de error
        """
        # Intentar obtener existente
        cliente = Cliente.query.filter_by(dni=dni).first()
        if cliente:
            return cliente, None
        
        # Intentar crear con RENIEC
        cliente_dict, error = ClienteService.crear_cliente_completo(
            dni, 
            correo_electronico or f"{dni}@temporal.com",
            pep_declarado=False
        )
        
        if error:
            # Si RENIEC falla, crear con datos mínimos
            if "no encontrado" in error.lower() or "tiempo de espera" in error.lower():
                return ClienteService.crear_cliente_minimo(dni, correo_electronico)
            return None, error
        
        # Obtener cliente recién creado
        cliente = Cliente.query.filter_by(dni=dni).first()
        return cliente, None
    
    @staticmethod
    def actualizar_cliente(
        cliente_id: int,
        pep: Optional[bool] = None,
        correo_electronico: Optional[str] = None
    ) -> Tuple[Optional[Cliente], Optional[str]]:
        """
        Actualiza los datos de un cliente.
        
        Args:
            cliente_id: ID del cliente
            pep: Nuevo estado PEP (opcional)
            correo_electronico: Nuevo email (opcional)
            
        Returns:
            Tuple[Cliente, error]: Cliente actualizado o mensaje de error
        """
        cliente = Cliente.query.get(cliente_id)
        if not cliente:
            return None, "Cliente no encontrado"
        
        try:
            if pep is not None:
                cliente.pep = pep
            if correo_electronico is not None:
                cliente.correo_electronico = correo_electronico
            
            db.session.commit()
            logger.info(f"Cliente {cliente_id} actualizado exitosamente")
            return cliente, None
            
        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error al actualizar cliente {cliente_id}: {exc}", exc_info=True)
            return None, f"Error al actualizar: {str(exc)}"
