"""
Servicio de Pagos
Maneja la lógica de negocio relacionada con pagos de cuotas
"""
import logging
from typing import Tuple, Optional, Dict, Any, List
from datetime import date
from decimal import Decimal, ROUND_DOWN

from app.common.extensions import db
from app.models import Pago, Cuota, Prestamo, EstadoPrestamoEnum, MetodoPagoEnum
from app.crud.pago_crud import (
    registrar_pago,
    obtener_pago_por_id,
    listar_pagos_por_cuota,
    listar_pagos_por_prestamo,
    obtener_pagos_pendientes_por_prestamo,
    actualizar_pago,
    devolver_pago
)

logger = logging.getLogger(__name__)


class PagoService:
    """Servicio para manejar la lógica de negocios de pagos"""
    
    @staticmethod
    def aplicar_redondeo(monto_contable: Decimal) -> Decimal:
        """
        MÓDULO 2: Aplica la Ley N° 29571 (Ley de Redondeo a favor del consumidor).
        
        IMPORTANTE: El redondeo SIEMPRE es hacia ABAJO para beneficiar al consumidor.
        Se redondea al múltiplo de S/ 0.10 inmediato inferior.
        
        La moneda de menor denominación en Perú es de 10 céntimos, por lo que:
        - Céntimos 0.01-0.09 → se ELIMINAN (redondeo hacia abajo a 0.00)
        - Céntimos 0.00 → sin cambio
        
        Ejemplos:
        - S/ 471.43 → S/ 471.40 (elimina 3 céntimos, ajuste +0.03)
        - S/ 471.44 → S/ 471.40 (elimina 4 céntimos, ajuste +0.04)
        - S/ 471.45 → S/ 471.40 (elimina 5 céntimos, ajuste +0.05)
        - S/ 471.47 → S/ 471.40 (elimina 7 céntimos, ajuste +0.07)
        - S/ 471.49 → S/ 471.40 (elimina 9 céntimos, ajuste +0.09)
        - S/ 471.50 → S/ 471.50 (sin céntimos residuales, ajuste +0.00)
        
        Args:
            monto_contable: Monto original de la cuota
            
        Returns:
            Decimal: Monto redondeado a pagar en efectivo (siempre <= monto_contable)
        """
        try:
            # Convertir a céntimos (enteros) para evitar problemas de punto flotante
            centimos = int(monto_contable * 100)
            
            # Obtener el residuo al dividir entre 10
            residuo = centimos % 10
            
            # LEY 29571: Redondeo SIEMPRE hacia abajo (a favor del consumidor)
            # Eliminar los céntimos residuales (1-9)
            centimos_redondeados = (centimos // 10) * 10
            
            # Convertir de vuelta a soles
            monto_redondeado = Decimal(centimos_redondeados) / Decimal('100')
            
            # El ajuste es siempre >= 0 (lo que el cliente NO paga)
            ajuste = monto_contable - monto_redondeado
            
            logger.debug(
                f"Redondeo Ley 29571: S/ {monto_contable} → S/ {monto_redondeado} "
                f"(residuo: {residuo} céntimos, ajuste a favor del cliente: +S/ {ajuste})"
            )
            
            return monto_redondeado
            
        except Exception as e:
            logger.error(f"Error aplicando redondeo Ley 29571: {e}")
            return monto_contable
    
    @staticmethod
    def calcular_montos_pago(
        monto_cuota: Decimal, 
        metodo_pago: MetodoPagoEnum
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        MÓDULO 2: Calcula los montos para el pago según el método.
        
        Args:
            monto_cuota: Monto contable de la cuota
            metodo_pago: Método de pago seleccionado
            
        Returns:
            Tuple[monto_contable, monto_pagado, ajuste_redondeo]:
                - monto_contable: Deuda contable (D_cont)
                - monto_pagado: Monto recibido en caja (P_efect)
                - ajuste_redondeo: Pérdida por redondeo (D_perd)
        """
        monto_contable = Decimal(str(monto_cuota))
        
        if metodo_pago == MetodoPagoEnum.EFECTIVO:
            # Aplicar Ley N° 29571 solo para efectivo
            monto_pagado = PagoService.aplicar_redondeo(monto_contable)
            ajuste_redondeo = monto_contable - monto_pagado
        else:
            # Para pagos digitales: monto exacto, sin ajuste
            monto_pagado = monto_contable
            ajuste_redondeo = Decimal('0.00')
        
        logger.info(
            f"Cálculo de pago - Método: {metodo_pago.value}, "
            f"Contable: S/ {monto_contable}, Pagado: S/ {monto_pagado}, "
            f"Ajuste: S/ {ajuste_redondeo}"
        )
        
        return monto_contable, monto_pagado, ajuste_redondeo
    
    @staticmethod
    def validar_prestamo_vigente(prestamo_id: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que un préstamo esté vigente.
        
        Args:
            prestamo_id: ID del préstamo
            
        Returns:
            Tuple[es_vigente, error]: Boolean y mensaje de error si aplica
        """
        prestamo = Prestamo.query.get(prestamo_id)
        
        if not prestamo:
            return False, f"Préstamo con ID {prestamo_id} no encontrado"
        
        if prestamo.estado != EstadoPrestamoEnum.VIGENTE:
            return False, f"El préstamo no está vigente. Estado actual: {prestamo.estado.value}"
        
        return True, None
    
    @staticmethod
    def validar_cuota_pertenece_prestamo(cuota_id: int, prestamo_id: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que una cuota pertenezca a un préstamo específico.
        
        Args:
            cuota_id: ID de la cuota
            prestamo_id: ID del préstamo
            
        Returns:
            Tuple[pertenece, error]: Boolean y mensaje de error si aplica
        """
        cuota = Cuota.query.get(cuota_id)
        
        if not cuota:
            return False, f"Cuota con ID {cuota_id} no encontrada"
        
        if cuota.prestamo_id != prestamo_id:
            return False, f"La cuota {cuota_id} no pertenece al préstamo {prestamo_id}"
        
        return True, None
    
    @staticmethod
    def validar_monto_pago(monto_pagado: Decimal, monto_cuota: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Valida que el monto del pago sea válido.
        
        Args:
            monto_pagado: Monto a pagar
            monto_cuota: Monto de la cuota
            
        Returns:
            Tuple[valido, error]: Boolean y mensaje de error si aplica
        """
        if monto_pagado <= 0:
            return False, "El monto del pago debe ser mayor a cero"
        
        if monto_pagado > monto_cuota:
            return False, f"El monto del pago ({monto_pagado}) no puede exceder el monto de la cuota ({monto_cuota})"
        
        return True, None
    
    @staticmethod
    def registrar_pago_cuota(
        prestamo_id: int,
        cuota_id: int,
        metodo_pago: MetodoPagoEnum = MetodoPagoEnum.EFECTIVO,
        fecha_pago: Optional[date] = None,
        comprobante_referencia: Optional[str] = None,
        observaciones: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        MÓDULO 2: Registra un pago de una cuota con lógica de redondeo y conciliación.
        
        Validaciones:
        1. El préstamo debe estar vigente
        2. La cuota debe pertenecer al préstamo
        3. La cuota no debe estar ya pagada
        
        Lógica de Redondeo:
        - EFECTIVO: Aplica Ley N° 29571 (redondeo a favor del consumidor)
        - TARJETA/TRANSFERENCIA: Monto exacto sin redondeo
        
        Conciliación Contable:
        - Caja recibe: monto_pagado (lo que realmente entró)
        - Ajuste por Redondeo: ajuste_redondeo (gasto operacional)
        - Cuenta por Cobrar: monto_contable (deuda saldada)
        - Invariante: monto_pagado + ajuste_redondeo = monto_contable
        
        Args:
            prestamo_id: ID del préstamo
            cuota_id: ID de la cuota
            metodo_pago: Método de pago (EFECTIVO, TARJETA, TRANSFERENCIA)
            fecha_pago: Fecha del pago (por defecto hoy)
            comprobante_referencia: Referencia del comprobante (opcional)
            observaciones: Observaciones del pago (opcional)
            
        Returns:
            Tuple[respuesta_dict, error, status_code]: Diccionario con datos del pago,
                                                       mensaje de error si aplica,
                                                       código HTTP de respuesta
        """
        try:
            # 1. Validar que el préstamo existe y está vigente
            es_vigente, error = PagoService.validar_prestamo_vigente(prestamo_id)
            if not es_vigente:
                return None, error, 400
            
            # 2. Validar que la cuota existe y pertenece al préstamo
            pertenece, error = PagoService.validar_cuota_pertenece_prestamo(cuota_id, prestamo_id)
            if not pertenece:
                return None, error, 400
            
            # Obtener la cuota
            cuota = Cuota.query.get(cuota_id)
            
            # 3. Validar que la cuota no está pagada
            if cuota.monto_pagado and cuota.monto_pagado > 0:
                return None, f"La cuota {cuota.numero_cuota} ya fue pagada", 400
            
            # 4. Calcular montos según método de pago
            monto_contable, monto_pagado, ajuste_redondeo = PagoService.calcular_montos_pago(
                cuota.monto_cuota,
                metodo_pago
            )
            
            # 5. Crear el pago con los montos calculados
            fecha_pago_efectiva = fecha_pago or date.today()
            
            nuevo_pago = Pago(
                cuota_id=cuota_id,
                metodo_pago=metodo_pago,
                monto_contable=monto_contable,
                monto_pagado=monto_pagado,
                ajuste_redondeo=ajuste_redondeo,
                fecha_pago=fecha_pago_efectiva,
                comprobante_referencia=comprobante_referencia,
                observaciones=observaciones
            )
            
            db.session.add(nuevo_pago)
            
            # 6. Actualizar la cuota con el monto pagado (contable, no el efectivo)
            cuota.monto_pagado = monto_contable
            cuota.fecha_pago = fecha_pago_efectiva
            
            db.session.commit()
            
            # 7. Enviar email con el voucher de pago
            try:
                from app.services.email_service import EmailService
                prestamo = Prestamo.query.get(prestamo_id)
                cliente = prestamo.cliente if prestamo else None
                
                if cliente and prestamo:
                    resultado = EmailService.enviar_voucher_pago(cliente, prestamo, cuota, nuevo_pago)
                    if resultado:
                        logger.info(f"Email de voucher enviado exitosamente para pago #{nuevo_pago.pago_id}")
                    else:
                        logger.warning(f"Email de voucher NO se envió para pago #{nuevo_pago.pago_id}")
                else:
                    logger.warning(f"No se pudo enviar email: cliente o préstamo no encontrado")
            except Exception as email_exc:
                # No fallar el pago si el email falla
                logger.error(f"Error al enviar email de voucher: {email_exc}", exc_info=True)
            
            # 8. Preparar respuesta con información de conciliación
            respuesta = {
                'success': True,
                'message': f'Pago registrado exitosamente para la cuota {cuota.numero_cuota}',
                'pago': nuevo_pago.to_dict(),
                'cuota': {
                    'cuota_id': cuota.cuota_id,
                    'numero_cuota': cuota.numero_cuota,
                    'es_cuota_ajuste': cuota.es_cuota_ajuste,
                    'fecha_vencimiento': cuota.fecha_vencimiento.isoformat(),
                    'fecha_pago': nuevo_pago.fecha_pago.isoformat()
                },
                'conciliacion': {
                    'monto_contable': float(monto_contable),
                    'monto_recibido_caja': float(monto_pagado),
                    'ajuste_redondeo': float(ajuste_redondeo),
                    'verificacion': float(monto_pagado + ajuste_redondeo),  # Debe igualar monto_contable
                    'metodo_pago': metodo_pago.value,
                    'ley_aplicada': 'Ley N° 29571' if metodo_pago == MetodoPagoEnum.EFECTIVO and ajuste_redondeo > 0 else None
                }
            }
            
            return respuesta, None, 201
            
        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error en registrar_pago_cuota: {exc}", exc_info=True)
            return None, f'Error al registrar el pago: {str(exc)}', 500
    
    @staticmethod
    def obtener_resumen_pagos_prestamo(prestamo_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Obtiene un resumen de los pagos de un préstamo.
        
        Args:
            prestamo_id: ID del préstamo
            
        Returns:
            Tuple[respuesta_dict, error, status_code]: Diccionario con resumen de pagos
        """
        try:
            # Validar que el préstamo existe
            prestamo = Prestamo.query.get(prestamo_id)
            if not prestamo:
                return None, f"Préstamo con ID {prestamo_id} no encontrado", 404
            
            # Obtener todas las cuotas
            cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
            
            if not cuotas:
                return None, "No hay cuotas para este préstamo", 404
            
            # Calcular estadísticas
            total_cuotas = len(cuotas)
            cuotas_pagadas = len([c for c in cuotas if c.monto_pagado and c.monto_pagado > 0])
            cuotas_pendientes = total_cuotas - cuotas_pagadas
            
            monto_total = sum(Decimal(c.monto_cuota) for c in cuotas)
            monto_pagado = sum(Decimal(c.monto_pagado) if c.monto_pagado else 0 for c in cuotas)
            monto_pendiente = monto_total - monto_pagado
            
            # Obtener pagos registrados
            pagos = listar_pagos_por_prestamo(prestamo_id)
            
            respuesta = {
                'success': True,
                'prestamo_id': prestamo_id,
                'resumen': {
                    'total_cuotas': total_cuotas,
                    'cuotas_pagadas': cuotas_pagadas,
                    'cuotas_pendientes': cuotas_pendientes,
                    'monto_total': float(monto_total),
                    'monto_pagado': float(monto_pagado),
                    'monto_pendiente': float(monto_pendiente),
                    'porcentaje_pagado': round((float(monto_pagado) / float(monto_total) * 100), 2) if monto_total > 0 else 0
                },
                'pagos': [p.to_dict() for p in pagos],
                'cuotas_pendientes': [
                    {
                        'cuota_id': c.cuota_id,
                        'numero_cuota': c.numero_cuota,
                        'fecha_vencimiento': c.fecha_vencimiento.isoformat(),
                        'monto_cuota': float(c.monto_cuota),
                        'estado': 'PAGADA' if c.monto_pagado and c.monto_pagado > 0 else 'PENDIENTE'
                    }
                    for c in sorted(cuotas, key=lambda x: x.numero_cuota)
                    if not c.monto_pagado or c.monto_pagado == 0
                ]
            }
            
            return respuesta, None, 200
            
        except Exception as exc:
            logger.error(f"Error en obtener_resumen_pagos_prestamo: {exc}", exc_info=True)
            return None, f'Error al obtener resumen de pagos: {str(exc)}', 500
