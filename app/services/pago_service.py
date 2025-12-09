import logging
from typing import Tuple, Optional, Dict, Any, List
from datetime import date
from decimal import Decimal, ROUND_DOWN

from app.common.extensions import db
<<<<<<< HEAD
from app.models import Pago, Cuota, Prestamo, EstadoPrestamoEnum, MedioPagoEnum
=======
from app.models import Pago, Cuota, Prestamo, EstadoPrestamoEnum, MetodoPagoEnum
>>>>>>> origin/add-redondeoemail
from app.crud.pago_crud import (
    registrar_pago,
    obtener_pago_por_id,
    listar_pagos_por_cuota,
    listar_pagos_por_prestamo,
    obtener_pagos_pendientes_por_prestamo,
    actualizar_pago
)
from app.services.mora_service import MoraService

logger = logging.getLogger(__name__)


class PagoService:
    """Servicio para manejar la lógica de negocios de pagos con mora"""

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
        """Valida que un préstamo esté vigente"""
        prestamo = Prestamo.query.get(prestamo_id)

        if not prestamo:
            return False, f"Préstamo con ID {prestamo_id} no encontrado"

        if prestamo.estado != EstadoPrestamoEnum.VIGENTE:
            return False, f"El préstamo no está vigente. Estado actual: {prestamo.estado.value}"

        return True, None

    @staticmethod
    def obtener_cuotas_pendientes_ordenadas(prestamo_id: int) -> List[Cuota]:
        """
        Obtiene las cuotas pendientes ordenadas por número.
        
        Args:
            prestamo_id: ID del préstamo
            
        Returns:
            Lista de cuotas pendientes ordenadas
        """
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
        
        # Filtrar solo las cuotas con saldo pendiente
        cuotas_pendientes = [c for c in cuotas if c.saldo_pendiente > 0]
        
        # Ordenar por número de cuota (para pagar en orden)
        return sorted(cuotas_pendientes, key=lambda c: c.numero_cuota)

    @staticmethod
    def registrar_pago_cuota(
        prestamo_id: int,
        cuota_id: int,
<<<<<<< HEAD
        monto_pagado: Decimal,
        medio_pago: str, 
=======
        metodo_pago: MetodoPagoEnum = MetodoPagoEnum.EFECTIVO,
>>>>>>> origin/add-redondeoemail
        fecha_pago: Optional[date] = None,
        comprobante_referencia: Optional[str] = None,
        observaciones: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
<<<<<<< HEAD
        Registra un pago de una cuota con priorización automática.
        
        PRIORIZACIÓN DE PAGO:
        1. Mora de cuotas anteriores vencidas
        2. Saldo pendiente de cuotas anteriores
        3. Mora de la cuota actual (si vencida)
        4. Saldo pendiente de la cuota actual
        
        Args:
            prestamo_id: ID del préstamo
            cuota_id: ID de la cuota (para registro)
            monto_pagado: Monto a pagar
            fecha_pago: Fecha del pago
            comprobante_referencia: Referencia del comprobante
            observaciones: Observaciones adicionales
=======
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
>>>>>>> origin/add-redondeoemail
            
        Returns:
            Tuple[respuesta_dict, error, status_code]
        """
        try:
            # Validaciones básicas
            es_vigente, error = PagoService.validar_prestamo_vigente(prestamo_id)
            if not es_vigente:
                return None, error, 400

            if monto_pagado <= 0:
                return None, "El monto del pago debe ser mayor a cero", 400

            # Validar medio de pago
            try:
                medio_pago_enum = MedioPagoEnum[medio_pago]
            except KeyError:
                return None, f"Medio de pago inválido: {medio_pago}", 400


            fecha_pago = fecha_pago or date.today()

            # Actualizar moras de todas las cuotas
            MoraService.actualizar_mora_prestamo(prestamo_id)

            # Obtener cuotas pendientes ordenadas
            cuotas_pendientes = PagoService.obtener_cuotas_pendientes_ordenadas(prestamo_id)
            
<<<<<<< HEAD
            if not cuotas_pendientes:
                return None, "No hay cuotas pendientes para este préstamo", 400

            # Aplicar el pago con priorización
            monto_restante = monto_pagado
            pagos_registrados = []
            detalles_pago = []
            monto_mora_total = Decimal('0.00')

            for cuota in cuotas_pendientes:
                if monto_restante <= 0:
                    break

                # Prioridad 1 y 2: Mora y saldo de cuotas anteriores
                monto_restante, mora_pagada = PagoService._aplicar_pago_a_cuota(
                    cuota,
                    monto_restante,
                    fecha_pago,
                    detalles_pago
                )
                monto_mora_total += mora_pagada

            # Registrar el pago principal
            nuevo_pago, error_pago = registrar_pago(
                cuota_id=cuota_id,
                monto_pagado=monto_pagado,
                fecha_pago=fecha_pago,
                comprobante_referencia=comprobante_referencia,
                observaciones=observaciones,
                medio_pago=MedioPagoEnum.TRANSFERENCIA,  # Por defecto
                monto_mora=monto_mora_total
            )

            if error_pago:
                return None, error_pago, 500

            # Preparar respuesta
            respuesta = {
                'success': True,
                'message': f'Pago de S/. {monto_pagado} registrado exitosamente',
                'pago_id': nuevo_pago.pago_id,
                'monto_pagado': float(monto_pagado),
                'monto_mora_pagado': float(monto_mora_total),
                'fecha_pago': fecha_pago.isoformat(),
                'medio_pago': medio_pago_enum,
                'detalles_aplicacion': detalles_pago,
                'comprobante_referencia': comprobante_referencia
=======
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
>>>>>>> origin/add-redondeoemail
            }

            logger.info(
                f"Pago registrado: Préstamo={prestamo_id}, "
                f"Monto={monto_pagado}, Mora={monto_mora_total}, Detalles={len(detalles_pago)} movimientos"
            )

            return respuesta, None, 201

        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error en registrar_pago_cuota: {exc}", exc_info=True)
            return None, f'Error al registrar el pago: {str(exc)}', 500

    @staticmethod
    def _aplicar_pago_a_cuota(
        cuota: Cuota,
        monto_disponible: Decimal,
        fecha_pago: date,
        detalles: List[Dict[str, Any]]
    ) -> Tuple[Decimal, Decimal]:
        """
        Aplica un pago a una cuota siguiendo la priorización.
        
        Returns:
            Tuple[monto_restante, monto_mora_pagado]
        """
        monto_restante = monto_disponible
        monto_mora_pagado = Decimal('0.00')

        # Paso 1: Cubrir mora
        if cuota.mora_acumulada > 0 and monto_restante > 0:
            pago_mora = min(monto_restante, cuota.mora_acumulada)
            
            # mora_acumulada: se reduce (es la mora pendiente de pago)
            cuota.mora_acumulada -= pago_mora
            
            # mora_generada: NO se modifica (es el registro histórico)
            # cuota.mora_generada permanece igual
            
            monto_restante -= pago_mora
            monto_mora_pagado = pago_mora
            
            detalles.append({
                'cuota_numero': cuota.numero_cuota,
                'concepto': 'Mora',
                'monto': float(pago_mora),
                'mora_restante': float(cuota.mora_acumulada),
                'mora_historica': float(cuota.mora_generada)
            })

        # Paso 2: Cubrir saldo pendiente
        if cuota.saldo_pendiente > 0 and monto_restante > 0:
            pago_saldo = min(monto_restante, cuota.saldo_pendiente)
            cuota.saldo_pendiente -= pago_saldo
            cuota.monto_pagado = (cuota.monto_pagado or 0) + pago_saldo
            monto_restante -= pago_saldo
            
            detalles.append({
                'cuota_numero': cuota.numero_cuota,
                'concepto': 'Saldo Pendiente',
                'monto': float(pago_saldo),
                'saldo_restante': float(cuota.saldo_pendiente)
            })

        # Marcar como pagada si no hay saldo
        if cuota.saldo_pendiente <= 0 and cuota.mora_acumulada <= 0:
            cuota.fecha_pago = fecha_pago
            detalles.append({
                'cuota_numero': cuota.numero_cuota,
                'concepto': 'Estado',
                'monto': 0,
                'estado': 'PAGADA'
            })

        db.session.commit()
        return monto_restante, monto_mora_pagado

    @staticmethod
    def obtener_resumen_pagos_prestamo(prestamo_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Obtiene un resumen completo de pagos incluyendo mora.
        """
        try:
            prestamo = Prestamo.query.get(prestamo_id)
            if not prestamo:
                return None, f"Préstamo con ID {prestamo_id} no encontrado", 404

            # Actualizar moras
            MoraService.actualizar_mora_prestamo(prestamo_id)

            cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
            if not cuotas:
                return None, "No hay cuotas para este préstamo", 404

            total_cuotas = len(cuotas)
            cuotas_pagadas = len([c for c in cuotas if c.saldo_pendiente <= 0])
            cuotas_pendientes = total_cuotas - cuotas_pagadas

            monto_total = sum(Decimal(c.monto_cuota) for c in cuotas)
            monto_pagado = sum(Decimal(c.monto_pagado) if c.monto_pagado else 0 for c in cuotas)
            monto_pendiente = sum(c.saldo_pendiente for c in cuotas)
            mora_total = sum(c.mora_acumulada for c in cuotas)

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
                    'mora_total': float(mora_total),
                    'total_a_pagar': float(monto_pendiente + mora_total),
                    'porcentaje_pagado': round(
                        (float(monto_pagado) / float(monto_total) * 100), 2
                    ) if monto_total > 0 else 0
                },
                'pagos': [p.to_dict() for p in pagos],
                'cuotas_pendientes': [
                    {
                        'cuota_id': c.cuota_id,
                        'numero_cuota': c.numero_cuota,
                        'fecha_vencimiento': c.fecha_vencimiento.isoformat(),
                        'monto_cuota': float(c.monto_cuota),
                        'monto_pagado': float(c.monto_pagado) if c.monto_pagado else 0,
                        'saldo_pendiente': float(c.saldo_pendiente),
                        'mora_acumulada': float(c.mora_acumulada),
                        'total_a_pagar': float(c.saldo_pendiente + c.mora_acumulada),
                        'estado': 'PAGADA' if c.saldo_pendiente <= 0 else 'PENDIENTE',
                        'dias_atraso': MoraService.calcular_dias_atraso(c.fecha_vencimiento)
                    }
                    for c in sorted(cuotas, key=lambda x: x.numero_cuota)
                    if c.saldo_pendiente > 0 or c.mora_acumulada > 0
                ]
            }

            return respuesta, None, 200

        except Exception as exc:
            logger.error(f"Error en obtener_resumen_pagos_prestamo: {exc}", exc_info=True)
            return None, f'Error: {str(exc)}', 500