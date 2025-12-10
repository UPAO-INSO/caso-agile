from typing import Tuple, Optional, Dict, Any, List
from datetime import date, datetime
from decimal import Decimal
from app.common.extensions import db
from app.models import Pago, Cuota, Prestamo, EstadoPrestamoEnum, MedioPagoEnum
from app.crud.pago_crud import (
    registrar_pago,
    obtener_pago_por_id,
    listar_pagos_por_cuota,
    listar_pagos_por_prestamo,
    obtener_pagos_pendientes_por_prestamo,
    actualizar_pago
)
from app.services.mora_service import MoraService
from app.services.caja_service import CajaService

import logging

logger = logging.getLogger(__name__)
    
# → Servicio para manejar la lógica de negocios de pagos con mora
class PagoService:

# → Aplicar redondeo según Ley N° 29571: 1-4 BAJA, 5-9 SUBE
    @staticmethod
    def aplicar_redondeo(monto_contable: Decimal) -> Decimal:
        """
        Redondea al múltiplo de 0.10 más cercano según regla 1-4 baja, 5-9 sube.
        Ejemplos:
        - 552.52 → 552.50 (centimos 2, baja)
        - 552.54 → 552.50 (centimos 4, baja)
        - 552.55 → 552.60 (centimos 5, sube)
        - 552.59 → 552.60 (centimos 9, sube)
        - 552.50 → 552.50 (ya es múltiplo)
        """
        try:
            # Obtener el último dígito (centimos de la segunda cifra decimal)
            centimos = int((monto_contable * 100) % 10)
            
            if centimos == 0:
                # Ya es múltiplo de 0.10
                return monto_contable
            elif centimos <= 4:
                # 1-4: Redondear hacia abajo
                monto_redondeado = (monto_contable * 10).to_integral_value() / 10
            else:
                # 5-9: Redondear hacia arriba
                import math
                monto_redondeado = math.ceil(monto_contable * 10) / 10
            
            return Decimal(str(monto_redondeado)).quantize(Decimal('0.10'))
            
        except Exception as e:
            logger.error(f"Error aplicando redondeo: {e}")
            return monto_contable

# → Validamos que el préstamo esté vigente
    @staticmethod
    def validar_prestamo_vigente(prestamo_id: int) -> Tuple[bool, Optional[str]]:
    # → Consultamos y obtenemos el préstamo
        prestamo = Prestamo.query.get(prestamo_id)

        if not prestamo:
            return False, f"Préstamo con ID {prestamo_id} no encontrado"

        if prestamo.estado != EstadoPrestamoEnum.VIGENTE:
            return False, f"El préstamo no está vigente. Estado actual: {prestamo.estado.value}"

        return True, None

    @staticmethod
# → Obtiene cuotas pendientes ordenadas por número - FRONT: Registrar pago
    def obtener_cuotas_pendientes_ordenadas(prestamo_id: int) -> List[Cuota]:
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
        
        # → Filtrar solo las cuotas con saldo pendiente
        cuotas_pendientes = [c for c in cuotas if c.saldo_pendiente > 0]
        
        # → Ordenar por número de cuota (para pagar en orden)
        return sorted(cuotas_pendientes, key=lambda c: c.numero_cuota)

    @staticmethod
    def registrar_pago_cuota(prestamo_id: int, cuota_id: int, monto_pagado: Decimal,
        medio_pago: str, fecha_pago: Optional[date] = None, comprobante_referencia: Optional[str] = None,
        observaciones: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """ 
        Registra un pago de una cuota con priorización automática y redondeo según Ley N° 29571.
        
        PRIORIZACIÓN DE PAGO:
        1. Mora de cuotas anteriores vencidas
        2. Saldo pendiente de cuotas anteriores
        3. Mora de la cuota actual (si vencida)
        4. Saldo pendiente de la cuota actual
        
        REDONDEO:
        - Si el pago es en EFECTIVO, se aplica redondeo al monto pagado.
        - El cliente paga el monto redondeado, y se registra el ajuste.

        Args:
            prestamo_id: ID del préstamo
            cuota_id: ID de la cuota (para registro)
            monto_pagado: Monto total a pagar (antes de redondeo)
            medio_pago: Medio de pago (EFECTIVO, TRANSFERENCIA, etc.)
            fecha_pago: Fecha del pago
            comprobante_referencia: Referencia del comprobante
            observaciones: Observaciones adicionales
            
        Returns:
            Tuple[respuesta_dict, error, status_code] """
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

            # Obtener cuota
            cuota = Cuota.query.get(cuota_id)
            if not cuota:
                return None, "Cuota no encontrada", 404

            if cuota.prestamo_id != prestamo_id:
                return None, "La cuota no pertenece al préstamo especificado", 400

            fecha_pago = fecha_pago or date.today()

            # Actualizar mora ANTES del pago para tener el valor correcto
            MoraService.actualizar_mora_cuota(cuota_id)
            
            # Refrescar la cuota para obtener la mora actualizada
            db.session.refresh(cuota)

            logger.info(f"Registrando pago para préstamo {prestamo_id} con fecha: {fecha_pago}")

            # Determinar si es pago en efectivo para redondeo
            es_efectivo = medio_pago == 'EFECTIVO'
            monto_contable = monto_pagado
            ajuste_redondeo = Decimal('0.00')
            
            if es_efectivo:
                monto_redondeado = PagoService.aplicar_redondeo(monto_pagado)
                ajuste_redondeo = monto_redondeado - monto_contable
                monto_pagado = monto_redondeado

            cuotas_pendientes = PagoService.obtener_cuotas_pendientes_ordenadas(prestamo_id)
            if not cuotas_pendientes:
                return None, "No hay cuotas pendientes para este préstamo", 400

            # Monto total de deuda a aplicar (saldo + mora)
            total_deuda = sum((Decimal(c.saldo_pendiente or 0) + Decimal(c.mora_acumulada or 0)) for c in cuotas_pendientes)


            # Calcular deuda de la cuota seleccionada
            deuda_cuota = Decimal(cuota.saldo_pendiente or 0) + Decimal(cuota.mora_acumulada or 0)
            
            # Validar que monto_pagado no exceda la deuda de la cuota
            if Decimal(str(monto_pagado)) > deuda_cuota:
                return None, f"El monto a pagar (S/ {monto_pagado}) no puede ser mayor a la deuda de la cuota (S/ {deuda_cuota:.2f})", 400
            
            # Validar monto_dado si es efectivo
            if medio_pago_enum == MedioPagoEnum.EFECTIVO:
                if monto_dado is None or monto_dado <= 0:
                    return None, "Para pagos en efectivo debe ingresar el monto dado (billetes entregados)", 400
                
                # Validar que monto_dado >= monto_pagado
                if monto_dado < Decimal(str(monto_pagado)):
                    return None, f"El monto dado (S/ {monto_dado}) debe ser mayor o igual al monto a pagar (S/ {monto_pagado})", 400
                
                # Validar que la diferencia no sea mayor a 200 soles
                diferencia = monto_dado - Decimal(str(monto_pagado))
                if diferencia > 200:
                    return None, f"La diferencia entre monto dado y monto a pagar no puede ser mayor a S/ 200.00 (actual: S/ {diferencia:.2f})", 400
                
                # Calcular vuelto
                vuelto = monto_dado - Decimal(str(monto_pagado))
            
            # Interpretar monto_pagado como monto entregado por el cliente
            monto_entregado = Decimal(str(monto_pagado))
            ajuste_redondeo = Decimal('0.00')
            monto_contable = monto_entregado
            
            # Si es pago en EFECTIVO: aplicar redondeo a lo que se registrará en caja
            if medio_pago_enum == MedioPagoEnum.EFECTIVO:
                # Aplicar redondeo al monto que se registrará en caja (según Ley)
                monto_pagado_registrado = PagoService.aplicar_redondeo(monto_entregado)
                # El monto que realmente se aplicará a la deuda es como máximo la deuda
                monto_contable = min(monto_pagado_registrado, total_deuda)
                ajuste_redondeo = (monto_pagado_registrado - monto_contable)

                logger.info(
                    f"Pago EFECTIVO - Deuda: S/ {total_deuda}, Cliente entregó: S/ {monto_entregado}, "
                    f"Caja registra: S/ {monto_pagado_registrado}, Ajuste: S/ {ajuste_redondeo}"
                )
            else:
                # Pagos digitales/tarjeta: no redondeo, monto aplicado es min(entregado, deuda)
                monto_pagado_registrado = monto_entregado
                monto_contable = min(monto_pagado_registrado, total_deuda)

            #Guardar saldo antes del pago para detectar si es pago parcial
            saldo_antes_pago = cuota.saldo_pendiente


            # Aplicar pago a la cuota seleccionada únicamente
            # Sin restricción de mora mínima: cualquier monto se acepta
            monto_restante = monto_contable
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

            # REGLA DE NEGOCIO: Si es pago parcial, congelar mora del período actual
            # Un pago parcial es cuando después del pago aún queda saldo pendiente
            es_pago_parcial = cuota.saldo_pendiente > 0
            if es_pago_parcial:
                MoraService.congelar_mora_por_pago_parcial(cuota.cuota_id)
                logger.info(
                    f"Pago parcial detectado en cuota {cuota.cuota_id}: "
                    f"Saldo antes={saldo_antes_pago}, Saldo después={cuota.saldo_pendiente}. "
                    f"Mora del período actual congelada."
                )

            # Registrar el pago principal
            nuevo_pago, error_pago = registrar_pago(
                cuota_id=cuota_id,
                monto_pagado=monto_pagado_registrado,
                monto_contable=monto_contable,
                ajuste_redondeo=ajuste_redondeo,
                fecha_pago=fecha_pago,
                comprobante_referencia=comprobante_referencia,
                observaciones=observaciones,
                medio_pago=medio_pago_enum,
                monto_mora=monto_mora_total
            )

            if error_pago:
                return None, error_pago, 500

            try:
                prestamo = Prestamo.query.get(prestamo_id)
                # Enviar voucher de pago por email deberia
                from app.services.email_service import EmailService
                cliente = prestamo.cliente if prestamo else None
                cuota = Cuota.query.get(cuota_id)
                if cliente and prestamo and cuota and nuevo_pago:
                    EmailService.enviar_voucher_pago(cliente, prestamo, cuota, nuevo_pago)
            except Exception as email_exc:
                logger.error(f"Error al enviar voucher de pago: {email_exc}", exc_info=True)

            # Preparar respuesta
            # monto_pagado_registrado: lo que queda en caja (tras redondeo), monto_contable: lo aplicado a la deuda
            respuesta = {
                'success': True,
                'message': f'Pago registrado exitosamente',
                'pago_id': nuevo_pago.pago_id,
                'monto_pagado_en_caja': float(monto_pagado_registrado),
                'monto_aplicado_a_deuda': float(monto_contable),
                'monto_mora_pagado': float(monto_mora_total),
                'fecha_pago': fecha_pago.isoformat(),
                'medio_pago': medio_pago_enum.value,
                'detalles_aplicacion': detalles_pago,
                'comprobante_referencia': comprobante_referencia,
                'es_pago_parcial': es_pago_parcial
            }
            
              # Agregar información de mora congelada si aplica
            if es_pago_parcial:
                respuesta['mora_info'] = {
                    'mora_congelada': True,
                    'mensaje': 'Pago parcial registrado. La mora del período actual ha sido congelada hasta la próxima fecha de vencimiento.'
                }

            # Agregar información de redondeo si aplica
            if medio_pago_enum == MedioPagoEnum.EFECTIVO and ajuste_redondeo != 0:
                respuesta['redondeo'] = {
                    'aplicado': True,
                    'ley': 'Ley N° 29571',
                    'monto_contable': float(monto_contable),
                    'monto_pagado_cliente': float(monto_pagado_registrado),
                    'ajuste_redondeo': float(ajuste_redondeo),
                    'mensaje': f'{"Ahorro" if ajuste_redondeo < 0 else "Diferencia"} de S/ {abs(ajuste_redondeo):.2f} {"a favor del cliente" if ajuste_redondeo < 0 else "a favor del negocio"}'
                }


             # Si el cliente entregó más dinero que lo registrado en caja, registrar el vuelto como egreso
            try:
                from app.services.caja_service import CajaService
                vuelto_caja = monto_entregado - monto_pagado_registrado
                if vuelto_caja and vuelto_caja > 0:
                    CajaService.registrar_egreso(vuelto_caja, f'Vuelto por pago #{nuevo_pago.pago_id}', pago_id=nuevo_pago.pago_id)
                    respuesta['vuelto_registrado'] = float(vuelto_caja)
            except Exception as exc:
                logger.error(f"Error registrando vuelto: {exc}", exc_info=True)

            # Verificar si el préstamo está completamente pagado
            cuotas_pendientes_check = PagoService.obtener_cuotas_pendientes_ordenadas(prestamo_id)
            if not cuotas_pendientes_check:  # No hay cuotas pendientes
                prestamo = Prestamo.query.get(prestamo_id)
                if prestamo and prestamo.estado == EstadoPrestamoEnum.VIGENTE:
                    prestamo.estado = EstadoPrestamoEnum.CANCELADO
                    db.session.commit()
                    logger.info(f"Préstamo {prestamo_id} marcado como CANCELADO - todas las cuotas pagadas")
                    respuesta['prestamo_cancelado'] = True

            logger.info(
                f"Pago registrado: Préstamo={prestamo_id}, Caja={monto_pagado_registrado}, Mora={monto_mora_total}, "
                f"Ajuste redondeo={ajuste_redondeo}, Detalles={len(detalles_pago)} movimientos, "
                f"Pago parcial={es_pago_parcial}"
            )

            return respuesta, None, 201

        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error en registrar_pago_cuota: {exc}", exc_info=True)
            return None, f'Error al registrar el pago: {str(exc)}', 500

    @staticmethod
    def _aplicar_pago_a_cuota(cuota: Cuota, monto_disponible: Decimal, fecha_pago: date,
        detalles: List[Dict[str, Any]]) -> Tuple[Decimal, Decimal]:
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