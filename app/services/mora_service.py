import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Tuple, Optional, Dict, Any, List
from app.common.extensions import db
from app.models import Cuota, Prestamo

logger = logging.getLogger(__name__)

class MoraService:
    """Servicio para calcular y aplicar mora a las cuotas"""

    TASA_MORA_MENSUAL = Decimal('0.01')  # 1% mensual
    DIAS_POR_MES = 30  # Solo para última cuota (fallback)

    @staticmethod
    def esta_vencida(fecha_vencimiento: date) -> bool:
        """
        Verifica si una cuota está vencida.
        
        REGLA: La cuota vence DESPUÉS del día de vencimiento, no el mismo día.
        Ejemplo: Si vence 09/01:
        - 08/01: NO vencida
        - 09/01: NO vencida (mismo día)
        - 10/01: SÍ vencida
        """
        return date.today() > fecha_vencimiento

    @staticmethod
    def calcular_dias_atraso(fecha_vencimiento: date) -> int:
        """
        Calcula los días de atraso desde la fecha de vencimiento.
        Solo cuenta si ya pasó el día de vencimiento.
        """
        if not MoraService.esta_vencida(fecha_vencimiento):
            return 0
        return (date.today() - fecha_vencimiento).days

    @staticmethod
    def obtener_siguiente_cuota(cuota: 'Cuota') -> Optional['Cuota']:
        """
        Obtiene la siguiente cuota del mismo préstamo.
        """
        return Cuota.query.filter_by(
            prestamo_id=cuota.prestamo_id,
            numero_cuota=cuota.numero_cuota + 1
        ).first()

    @staticmethod
    def obtener_cuotas_desde(cuota: 'Cuota') -> List['Cuota']:
        """
        Obtiene todas las cuotas desde la cuota dada hasta la última (inclusive).
        """
        return Cuota.query.filter(
            Cuota.prestamo_id == cuota.prestamo_id,
            Cuota.numero_cuota >= cuota.numero_cuota
        ).order_by(Cuota.numero_cuota).all()

    @staticmethod
    def calcular_meses_atraso_por_cuotas(cuota: 'Cuota', desde_cuota: 'Cuota' = None) -> int:
        """
        Calcula los meses de atraso basándose en las fechas de vencimiento de cuotas.
        
        LÓGICA:
        - Un "mes" = cuando pasa una fecha de vencimiento de cuota (hoy > fecha_vencimiento).
        - Meses de atraso = cuántas fechas de vencimiento (desde la cuota de referencia) ya pasaron.
        
        Args:
            cuota: Cuota a evaluar
            desde_cuota: Cuota desde donde empezar a contar (para pagos parciales).
                         Si es None, se usa la misma cuota.
        
        Ejemplo SIN pago parcial:
        - Cuota 1 vence 09/Ene, Cuota 2 vence 09/Feb, Cuota 3 vence 09/Mar
        - Hoy = 10/Ene: Cuota 1 → 1 mes (solo su fecha venció)
        - Hoy = 10/Feb: Cuota 1 → 2 meses (vencieron 09/Ene y 09/Feb)
        
        Ejemplo CON pago parcial (desde_cuota = Cuota 2):
        - Hoy = 10/Feb: Cuota 1 → 1 mes (cuenta desde Cuota 2)
        - Hoy = 10/Mar: Cuota 1 → 2 meses (vencieron 09/Feb y 09/Mar)
        """
        hoy = date.today()
        cuota_referencia = desde_cuota or cuota
        
        # Si la cuota de referencia no está vencida, no hay atraso
        if not MoraService.esta_vencida(cuota_referencia.fecha_vencimiento):
            return 0
        
        # Obtener todas las cuotas desde la cuota de referencia
        cuotas_desde_referencia = MoraService.obtener_cuotas_desde(cuota_referencia)
        
        if not cuotas_desde_referencia:
            return 0
        
        # Contar cuántas fechas de vencimiento ya pasaron (hoy > fecha_vencimiento)
        meses_atraso = 0
        
        for c in cuotas_desde_referencia:
            if hoy > c.fecha_vencimiento:
                meses_atraso += 1
            else:
                break
        
        # Si es la última cuota y ya pasó su vencimiento, calcular meses adicionales
        # basándose en 30 días desde la última fecha de vencimiento
        if meses_atraso == len(cuotas_desde_referencia) and meses_atraso > 0:
            ultima_cuota = cuotas_desde_referencia[-1]
            dias_extra = (hoy - ultima_cuota.fecha_vencimiento).days
            
            if dias_extra > 0:
                # Meses adicionales después de la última cuota
                meses_extra = (dias_extra - 1) // MoraService.DIAS_POR_MES
                meses_atraso += meses_extra
        
        logger.debug(
            f"Cuota {cuota.cuota_id} (#{cuota.numero_cuota}): "
            f"{meses_atraso} mes(es) de atraso (desde cuota #{cuota_referencia.numero_cuota})"
        )
        
        return meses_atraso

    @staticmethod
    def es_pago_parcial(cuota: 'Cuota') -> bool:
        """
        Verifica si una cuota tiene un pago parcial.
        
        Pago parcial = hay algún monto pagado PERO aún queda saldo pendiente
        """
        monto_pagado = cuota.monto_pagado or Decimal('0.00')
        saldo_pendiente = cuota.saldo_pendiente or Decimal('0.00')
        
        return monto_pagado > 0 and saldo_pendiente > 0

    @staticmethod
    def mora_congelada_por_pago_parcial(cuota: 'Cuota') -> bool:
        """
        Verifica si la mora está congelada debido a un pago parcial.
        
        REGLA DE NEGOCIO:
        - Si hay pago parcial, la mora se congela HASTA que pase la fecha 
          de vencimiento de la SIGUIENTE cuota (hoy > siguiente.fecha_vencimiento).
        - Si ya pasó, la mora se aplica desde la siguiente cuota.
        
        Returns:
            True si la mora está congelada, False si debe aplicarse
        """
        # Si no es pago parcial, la mora no está congelada
        if not MoraService.es_pago_parcial(cuota):
            return False
        
        # Buscar la siguiente cuota
        siguiente_cuota = MoraService.obtener_siguiente_cuota(cuota)
        
        if siguiente_cuota:
            hoy = date.today()
            
            # Mora congelada si hoy <= fecha de vencimiento de la siguiente cuota
            if hoy <= siguiente_cuota.fecha_vencimiento:
                logger.info(
                    f"Mora CONGELADA para cuota {cuota.cuota_id} (pago parcial): "
                    f"Hoy={hoy} <= Venc. siguiente cuota={siguiente_cuota.fecha_vencimiento}"
                )
                return True
            else:
                logger.info(
                    f"Mora ACTIVA para cuota {cuota.cuota_id} (pago parcial): "
                    f"Hoy={hoy} > Venc. siguiente cuota={siguiente_cuota.fecha_vencimiento}"
                )
                return False
        else:
            # Es la última cuota: aplicar lógica normal de 30 días
            logger.info(
                f"Cuota {cuota.cuota_id} es la última del préstamo. "
                f"Aplicando lógica normal de mora."
            )
            return False

    @staticmethod
    def calcular_mora_cuota(monto_a_aplicar: Decimal, numero_meses_atraso: int) -> Decimal:
        """
        Calcula la mora de una cuota.
        
        Mora = monto × 1% × número de meses de atraso
        """
        if numero_meses_atraso <= 0:
            return Decimal('0.00')
        
        mora = monto_a_aplicar * MoraService.TASA_MORA_MENSUAL * numero_meses_atraso
        return mora.quantize(Decimal('0.01'))

    @staticmethod
    def actualizar_mora_cuota(cuota_id: int) -> Tuple[Decimal, str]:
        """
        Actualiza la mora de una cuota basada en su estado.
        
        REGLAS:
        1. Si la cuota NO está vencida (hoy <= fecha_vencimiento) → mora = 0
        2. Si tiene pago parcial Y hoy <= venc. siguiente cuota → mora = 0 (CONGELADA)
        3. Si tiene pago parcial Y hoy > venc. siguiente cuota → mora = 1% × meses DESDE la siguiente cuota
        4. Si NO tiene pago parcial y está vencida → mora = 1% × meses desde esta cuota
        """
        try:
            cuota = Cuota.query.get(cuota_id)
            if not cuota:
                return Decimal('0.00'), f"Cuota {cuota_id} no encontrada"

            # REGLA 1: Si no está vencida, no hay mora
            if not MoraService.esta_vencida(cuota.fecha_vencimiento):
                cuota.mora_acumulada = Decimal('0.00')
                db.session.commit()
                return Decimal('0.00'), "Cuota no está vencida"

            # REGLA 2: Verificar si la mora está CONGELADA por pago parcial
            if MoraService.mora_congelada_por_pago_parcial(cuota):
                cuota.mora_acumulada = Decimal('0.00')
                db.session.commit()
                return Decimal('0.00'), "Mora congelada por pago parcial"

            # REGLA 3 y 4: Calcular mora sobre saldo pendiente
            if cuota.saldo_pendiente and cuota.saldo_pendiente > 0:
                
                # Determinar desde qué cuota contar los meses
                desde_cuota = cuota  # Por defecto, desde esta cuota
                
                if MoraService.es_pago_parcial(cuota):
                    # REGLA 3: Pago parcial descongelado → contar desde la siguiente cuota
                    siguiente_cuota = MoraService.obtener_siguiente_cuota(cuota)
                    if siguiente_cuota:
                        desde_cuota = siguiente_cuota
                
                # Calcular meses de atraso desde la cuota de referencia
                meses_atraso = MoraService.calcular_meses_atraso_por_cuotas(cuota, desde_cuota)
                
                if meses_atraso <= 0:
                    cuota.mora_acumulada = Decimal('0.00')
                    db.session.commit()
                    return Decimal('0.00'), "Sin meses de atraso"
                
                mora_nueva = MoraService.calcular_mora_cuota(
                    cuota.saldo_pendiente,
                    meses_atraso
                )
                
                cuota.mora_generada = mora_nueva
                cuota.mora_acumulada = mora_nueva
                
                db.session.commit()
                
                logger.info(
                    f"Mora actualizada para cuota {cuota_id}: "
                    f"Mora={mora_nueva}, Saldo={cuota.saldo_pendiente}, "
                    f"Meses={meses_atraso}, Desde cuota #{desde_cuota.numero_cuota}"
                )
                
                return mora_nueva, f"Mora: {mora_nueva} ({meses_atraso} mes(es))"
            else:
                # Cuota completamente pagada
                mora_historica = cuota.mora_generada or Decimal('0.00')
                return mora_historica, f"Mora histórica: {mora_historica}"

        except Exception as exc:
            logger.error(f"Error al actualizar mora de cuota {cuota_id}: {exc}")
            return Decimal('0.00'), f"Error: {str(exc)}"

    @staticmethod
    def actualizar_mora_prestamo(prestamo_id: int) -> Dict[str, Any]:
        """
        Actualiza la mora de todas las cuotas de un préstamo.
        """
        try:
            cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
            
            total_mora = Decimal('0.00')
            mora_por_cuota = {}

            for cuota in cuotas:
                mora, mensaje = MoraService.actualizar_mora_cuota(cuota.cuota_id)
                total_mora += mora
                
                # Calcular meses para mostrar en respuesta
                desde_cuota = cuota
                if MoraService.es_pago_parcial(cuota):
                    siguiente = MoraService.obtener_siguiente_cuota(cuota)
                    if siguiente:
                        desde_cuota = siguiente
                
                meses_atraso = MoraService.calcular_meses_atraso_por_cuotas(cuota, desde_cuota)
                
                mora_por_cuota[cuota.numero_cuota] = {
                    'mora': float(mora),
                    'mensaje': mensaje,
                    'es_pago_parcial': MoraService.es_pago_parcial(cuota),
                    'meses_atraso': meses_atraso,
                    'mora_congelada': MoraService.mora_congelada_por_pago_parcial(cuota)
                }

            logger.info(f"Mora actualizada para préstamo {prestamo_id}: Total={total_mora}")

            return {
                'prestamo_id': prestamo_id,
                'total_mora': float(total_mora),
                'mora_por_cuota': mora_por_cuota,
                'total_cuotas': len(cuotas)
            }

        except Exception as exc:
            logger.error(f"Error al actualizar mora del préstamo {prestamo_id}: {exc}")
            return {
                'error': str(exc),
                'prestamo_id': prestamo_id
            }