import logging
from typing import Tuple, Optional, Dict, Any, List
from datetime import date
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

            fecha_pago = fecha_pago or date.today()

            # APLICAR REDONDEO si es pago en EFECTIVO
            monto_contable = monto_pagado  # Monto que debería pagarse (deuda real)
            ajuste_redondeo = Decimal('0.00')
            
            if medio_pago_enum == MedioPagoEnum.EFECTIVO:
                monto_pagado_redondeado = PagoService.aplicar_redondeo(monto_pagado)
                ajuste_redondeo = monto_pagado_redondeado - monto_contable  # Puede ser positivo o negativo
                monto_pagado = monto_pagado_redondeado
                
                logger.info(
                    f"Pago EFECTIVO - Contable: S/ {monto_contable}, "
                    f"Cliente paga: S/ {monto_pagado}, Ajuste: S/ {ajuste_redondeo}"
                )

            # Actualizar moras de todas las cuotas
            MoraService.actualizar_mora_prestamo(prestamo_id)

            # Obtener cuotas pendientes ordenadas
            cuotas_pendientes = PagoService.obtener_cuotas_pendientes_ordenadas(prestamo_id)
            
            if not cuotas_pendientes:
                return None, "No hay cuotas pendientes para este préstamo", 400

        # → Verificar que si hay mora pendiente, el monto debe cubrirla completamente
            primera_cuota_con_mora = next((c for c in cuotas_pendientes if c.mora_acumulada > 0), None)
            if primera_cuota_con_mora and primera_cuota_con_mora.mora_acumulada > 0:
                if monto_pagado < primera_cuota_con_mora.mora_acumulada:
                    return None, (
                        f"La cuota {primera_cuota_con_mora.numero_cuota} tiene mora de S/ {primera_cuota_con_mora.mora_acumulada:.2f}. "
                        f"Debe pagar la mora completa antes de abonar a la cuota. Monto mínimo: S/ {primera_cuota_con_mora.mora_acumulada:.2f}"
                    ), 400

            # Aplicar el pago con priorización
            # IMPORTANTE: Usar monto_contable (lo que se debía) para distribuir a cuotas
            # El ajuste_redondeo NO se distribuye, queda solo registrado para cuadre de caja
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

            # Registrar el pago principal
            nuevo_pago, error_pago = registrar_pago(
                cuota_id=cuota_id,
                monto_pagado=monto_pagado,
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

            # Preparar respuesta
            respuesta = {
                'success': True,
                'message': f'Pago de S/. {monto_pagado} registrado exitosamente',
                'pago_id': nuevo_pago.pago_id,
                'monto_pagado': float(monto_pagado),
                'monto_mora_pagado': float(monto_mora_total),
                'fecha_pago': fecha_pago.isoformat(),
                'medio_pago': medio_pago_enum.value,
                'detalles_aplicacion': detalles_pago,
                'comprobante_referencia': comprobante_referencia
            }
            
            # Agregar información de redondeo si aplica
            if medio_pago_enum == MedioPagoEnum.EFECTIVO and ajuste_redondeo != 0:
                respuesta['redondeo'] = {
                    'aplicado': True,
                    'ley': 'Ley N° 29571',
                    'monto_contable': float(monto_contable),
                    'monto_pagado_cliente': float(monto_pagado),
                    'ajuste_redondeo': float(ajuste_redondeo),
                    'mensaje': f'{"Ahorro" if ajuste_redondeo < 0 else "Diferencia"} de S/ {abs(ajuste_redondeo):.2f} {"a favor del cliente" if ajuste_redondeo < 0 else "a favor del negocio"}'
                }

            logger.info(
                f"Pago registrado: Préstamo={prestamo_id}, "
                f"Monto={monto_pagado}, Mora={monto_mora_total}, "
                f"Ajuste redondeo={ajuste_redondeo}, Detalles={len(detalles_pago)} movimientos"
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