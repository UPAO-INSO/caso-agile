"""
Servicio de Préstamos
Maneja la lógica de negocio relacionada con préstamos
"""
from datetime import date
from decimal import Decimal
import logging
from typing import Tuple, Optional, Dict, Any, List

from app.extensions import db
from app.models import (
    Cuota, 
    DeclaracionJurada, 
    TipoDeclaracionEnum,
    Prestamo,
    EstadoPrestamoEnum,
    Cliente
)
from app.crud import (
    crear_cuotas_bulk,
    crear_declaracion,
    crear_prestamo,
    obtener_cliente_por_dni,
    crear_cliente
)
from app.services.financial_service import FinancialService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class PrestamoService:
    """Servicio para manejar la lógica de negocios de préstamos"""
    
    @staticmethod
    def obtener_o_crear_cliente(dni: str, correo_electronico: str) -> Tuple[Optional[Cliente], Optional[str]]:
        """
        Obtiene un cliente existente por DNI, o lo crea si no existe.
        
        Args:
            dni: Número de documento de identidad
            correo_electronico: Email del cliente
            
        Returns:
            Tuple[Cliente, error]: Cliente obtenido/creado y mensaje de error si aplica
        """
        cliente = obtener_cliente_por_dni(dni)
        
        if cliente:
            return cliente, None
        
        # Crear nuevo cliente
        cliente_dict, error_cliente = crear_cliente(dni, correo_electronico, pep_declarado=False)
        
        if error_cliente:
            return None, f'Error al crear cliente: {error_cliente}'
        
        # Obtener el cliente recién creado
        cliente = obtener_cliente_por_dni(dni)
        
        if not cliente:
            return None, f'No se pudo crear o encontrar el cliente con DNI {dni}.'
        
        return cliente, None
    
    @staticmethod
    def validar_prestamo_activo(cliente_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Valida si un cliente ya tiene un préstamo activo.
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            Tuple[tiene_activo, info_prestamo]: Boolean indicando si tiene préstamo activo 
                                                 y dict con info del préstamo si existe
        """
        from app.crud import prestamo_activo_cliente
        
        prestamo_activo = prestamo_activo_cliente(cliente_id, EstadoPrestamoEnum.VIGENTE)
        
        if not prestamo_activo:
            return False, None
        
        info_prestamo = {
            'prestamo_id': prestamo_activo.prestamo_id,
            'monto': float(prestamo_activo.monto_total),
            'estado': 'VIGENTE'
        }
        
        return True, info_prestamo
    
    @staticmethod
    def determinar_tipo_declaracion(monto_total: Decimal, es_pep: bool) -> Tuple[bool, Optional[TipoDeclaracionEnum]]:
        """
        Determina si se requiere declaración jurada y de qué tipo.
        
        Args:
            monto_total: Monto del préstamo
            es_pep: Si el cliente es PEP
            
        Returns:
            Tuple[requiere_dj, tipo_dj]: Boolean y tipo de declaración si aplica
        """
        requiere_dj = False
        tipos_dj = set()
        
        if monto_total > FinancialService.UIT_VALOR:
            requiere_dj = True
            tipos_dj.add(TipoDeclaracionEnum.USO_PROPIO)
        
        if es_pep:
            requiere_dj = True
            tipos_dj.add(TipoDeclaracionEnum.PEP)
        
        if not requiere_dj:
            return False, None
        
        # Determinar tipo final
        if TipoDeclaracionEnum.USO_PROPIO in tipos_dj and TipoDeclaracionEnum.PEP in tipos_dj:
            tipo_final = TipoDeclaracionEnum.AMBOS
        elif TipoDeclaracionEnum.USO_PROPIO in tipos_dj:
            tipo_final = TipoDeclaracionEnum.USO_PROPIO
        else:
            tipo_final = TipoDeclaracionEnum.PEP
        
        return True, tipo_final
    
    @staticmethod
    def crear_declaracion_jurada(cliente_id: int, tipo_declaracion: TipoDeclaracionEnum) -> Tuple[Optional[DeclaracionJurada], Optional[str]]:
        """
        Crea una declaración jurada para un cliente.
        
        Args:
            cliente_id: ID del cliente
            tipo_declaracion: Tipo de declaración
            
        Returns:
            Tuple[DeclaracionJurada, error]: Declaración creada y mensaje de error si aplica
        """
        nueva_dj = DeclaracionJurada(
            cliente_id=cliente_id,
            tipo_declaracion=tipo_declaracion,
            fecha_firma=date.today(),
            firmado=True
        )
        
        modelo_declaracion, error_dj = crear_declaracion(nueva_dj)
        
        if error_dj:
            return None, f'Error al crear declaracion jurada: {error_dj}'
        
        return modelo_declaracion, None
    
    @staticmethod
    def crear_cuotas_desde_cronograma(prestamo_id: int, cronograma: List[Dict[str, Any]]) -> None:
        """
        Crea las cuotas en la base de datos desde un cronograma.
        
        Args:
            prestamo_id: ID del préstamo
            cronograma: Lista de diccionarios con información de cuotas
        """
        cuotas_a_crear = []
        
        for item in cronograma:
            cuota = Cuota(
                prestamo_id=prestamo_id,
                numero_cuota=item['numero_cuota'],
                fecha_vencimiento=item['fecha_vencimiento'],
                monto_cuota=item['monto_cuota'],
                monto_capital=item['monto_capital'],
                monto_interes=item['monto_interes'],
                saldo_capital=item['saldo_capital']
            )
            cuotas_a_crear.append(cuota)
        
        crear_cuotas_bulk(cuotas_a_crear)
    
    @staticmethod
    def registrar_prestamo_completo(
        dni: str,
        correo_electronico: str,
        monto_total: Decimal,
        interes_tea: Decimal,
        plazo: int,
        f_otorgamiento: date
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Registra un préstamo completo con todas sus dependencias.
        
        Este método maneja:
        1. Obtención/creación del cliente
        2. Validación de préstamos activos
        3. Creación de declaración jurada si aplica
        4. Creación del préstamo
        5. Generación y guardado del cronograma
        6. Envío de email de confirmación
        
        Args:
            dni: DNI del cliente
            correo_electronico: Email del cliente
            monto_total: Monto del préstamo
            interes_tea: Tasa de interés anual
            plazo: Plazo en meses
            f_otorgamiento: Fecha de otorgamiento
            
        Returns:
            Tuple[respuesta_dict, error, status_code]: Diccionario con datos del préstamo,
                                                       mensaje de error si aplica,
                                                       código HTTP de respuesta
        """
        try:
            # 1. Obtener o crear cliente
            cliente, error = PrestamoService.obtener_o_crear_cliente(dni, correo_electronico)
            if error:
                return None, error, 400
            
            # 2. Validar préstamo activo
            tiene_activo, info_prestamo = PrestamoService.validar_prestamo_activo(cliente.cliente_id)
            if tiene_activo:
                error_msg = f'El cliente {cliente.nombre_completo} ya tiene un préstamo activo.'
                return {
                    'error': 'PRESTAMO_ACTIVO',
                    'mensaje': error_msg,
                    **info_prestamo
                }, error_msg, 400
            
            # 3. Determinar si requiere declaración jurada
            requiere_dj, tipo_declaracion = PrestamoService.determinar_tipo_declaracion(
                monto_total, 
                cliente.pep
            )
            
            # 4. Crear declaración jurada si es necesaria
            declaracion_id = None
            modelo_declaracion = None
            
            if requiere_dj:
                modelo_declaracion, error = PrestamoService.crear_declaracion_jurada(
                    cliente.cliente_id,
                    tipo_declaracion
                )
                if error:
                    return None, error, 500
                
                declaracion_id = modelo_declaracion.declaracion_id
            
            # 5. Crear el préstamo
            nuevo_prestamo = Prestamo(
                cliente_id=cliente.cliente_id,
                monto_total=monto_total,
                interes_tea=interes_tea,
                plazo=plazo,
                f_otorgamiento=f_otorgamiento,
                requiere_dec_jurada=requiere_dj,
                declaracion_id=declaracion_id
            )
            
            modelo_prestamo = crear_prestamo(nuevo_prestamo)
            
            # 6. Generar cronograma
            cronograma = FinancialService.generar_cronograma_pagos(
                monto_total, 
                interes_tea, 
                plazo, 
                f_otorgamiento
            )
            
            # 7. Crear cuotas en BD
            PrestamoService.crear_cuotas_desde_cronograma(modelo_prestamo.prestamo_id, cronograma)
            
            # 8. Enviar correo electrónico
            EmailService.enviar_confirmacion_prestamo(cliente, modelo_prestamo, cronograma)
            
            # 9. Preparar respuesta
            respuesta = {
                'success': True,
                'message': 'Préstamo registrado exitosamente',
                'prestamo': {
                    'prestamo_id': modelo_prestamo.prestamo_id,
                    'cliente_id': modelo_prestamo.cliente_id,
                    'monto_total': float(modelo_prestamo.monto_total),
                    'interes_tea': float(modelo_prestamo.interes_tea),
                    'plazo': modelo_prestamo.plazo,
                    'fecha_otorgamiento': modelo_prestamo.f_otorgamiento.isoformat(),
                    'estado': modelo_prestamo.estado.value,
                    'requiere_declaracion': requiere_dj
                },
                'cliente': {
                    'cliente_id': cliente.cliente_id,
                    'dni': cliente.dni,
                    'nombre_completo': cliente.nombre_completo,
                    'pep': cliente.pep
                },
                'cronograma': [
                    {
                        'numero_cuota': c['numero_cuota'],
                        'fecha_vencimiento': c['fecha_vencimiento'].isoformat(),
                        'monto_cuota': float(c['monto_cuota']),
                        'monto_capital': float(c['monto_capital']),
                        'monto_interes': float(c['monto_interes']),
                        'saldo_capital': float(c['saldo_capital'])
                    }
                    for c in cronograma
                ]
            }
            
            if requiere_dj and modelo_declaracion:
                respuesta['declaracion_jurada'] = {
                    'declaracion_id': modelo_declaracion.declaracion_id,
                    'tipo': tipo_declaracion.value,
                    'fecha_firma': modelo_declaracion.fecha_firma.isoformat()
                }
            
            return respuesta, None, 201
            
        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error en registrar_prestamo_completo: {exc}", exc_info=True)
            return None, f'Error en la base de datos al registrar el préstamo: {str(exc)}', 500
    
    @staticmethod
    def actualizar_estado_prestamo(prestamo_id: int, nuevo_estado: EstadoPrestamoEnum) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Actualiza el estado de un préstamo siguiendo las reglas de negocio.
        
        Reglas:
        - Un préstamo CANCELADO no puede cambiar de estado (es final)
        - Un préstamo VIGENTE solo puede cambiar a CANCELADO
        
        Args:
            prestamo_id: ID del préstamo
            nuevo_estado: Nuevo estado del préstamo
            
        Returns:
            Tuple[respuesta_dict, error, status_code]
        """
        from app.prestamos.crud import obtener_prestamo_por_id
        
        prestamo = obtener_prestamo_por_id(prestamo_id)
        
        if not prestamo:
            return None, 'Préstamo no encontrado', 404
        
        estado_actual = prestamo.estado
        
        # REGLA: CANCELADO es final, no se puede cambiar
        if estado_actual == EstadoPrestamoEnum.CANCELADO:
            return None, 'Un préstamo CANCELADO no puede cambiar de estado', 400
        
        # REGLA: VIGENTE solo puede pasar a CANCELADO
        if estado_actual == EstadoPrestamoEnum.VIGENTE and nuevo_estado == EstadoPrestamoEnum.VIGENTE:
            return None, 'El préstamo ya está en estado VIGENTE', 400
        
        try:
            prestamo.estado = nuevo_estado
            db.session.commit()
            
            respuesta = {
                'success': True,
                'mensaje': f'Estado actualizado de {estado_actual.value} a {nuevo_estado.value}',
                'prestamo_id': prestamo_id,
                'nuevo_estado': nuevo_estado.value
            }
            
            return respuesta, None, 200
            
        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error al actualizar estado de préstamo {prestamo_id}: {exc}", exc_info=True)
            return None, f'Error al actualizar estado: {str(exc)}', 500
