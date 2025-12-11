import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Tuple, Optional, Dict, Any
from app.common.extensions import db
from app.models import Cuota, Prestamo

logger = logging.getLogger(__name__)

class MoraService:
    """Servicio para calcular y aplicar mora a las cuotas"""

    TASA_MORA_MENSUAL = Decimal('0.01')  # 1% mensual
    DIAS_POR_MES = 30

    @staticmethod
    def calcular_dias_atraso(fecha_vencimiento: date) -> int:
        """
        Calcula los días de atraso desde la fecha de vencimiento.
        
        Args:
            fecha_vencimiento: Fecha de vencimiento de la cuota
            
        Returns:
            Número de días de atraso (0 si no está atrasada)
        """
        dias_atraso = (date.today() - fecha_vencimiento).days
        return max(0, dias_atraso)

    @staticmethod
    def calcular_meses_atraso(fecha_vencimiento: date) -> int:
        """
        Calcula los meses de atraso (considerando 30 días = 1 mes).
        
        Args:
            fecha_vencimiento: Fecha de vencimiento de la cuota
            
        Returns:
            Número de meses de atraso
        """
        dias_atraso = MoraService.calcular_dias_atraso(fecha_vencimiento)

        # Si no hay atraso, no hay meses de mora
        if dias_atraso <= 0:
            return 0

        meses_atraso = ((dias_atraso - 1) // MoraService.DIAS_POR_MES) + 1
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
        - Si hay pago parcial en esta cuota, la mora se congela HASTA que 
          llegue la fecha de vencimiento de la SIGUIENTE cuota.
        - Si ya pasó la fecha de vencimiento de la siguiente cuota, 
          la mora SÍ se aplica.
        - Si es la última cuota (no hay siguiente), se usa la lógica normal
          basada en 30 días desde su fecha de vencimiento.
        
        Returns:
            True si la mora está congelada, False si debe aplicarse
        """
        # Si no es pago parcial, la mora no está congelada
        if not MoraService.es_pago_parcial(cuota):
            return False
        
        # Buscar la siguiente cuota
        siguiente_cuota = MoraService.obtener_siguiente_cuota(cuota)
        
        if siguiente_cuota:
            # Hay siguiente cuota: comparar con su fecha de vencimiento
            hoy = date.today()
            
            if hoy < siguiente_cuota.fecha_vencimiento:
                # Aún no llega la fecha de vencimiento de la siguiente cuota
                # → Mora CONGELADA
                logger.info(
                    f"Mora CONGELADA para cuota {cuota.cuota_id} (pago parcial): "
                    f"Hoy={hoy} < Venc. siguiente cuota={siguiente_cuota.fecha_vencimiento}"
                )
                return True
            else:
                # Ya pasó la fecha de vencimiento de la siguiente cuota
                # → Mora debe aplicarse
                logger.info(
                    f"Mora ACTIVA para cuota {cuota.cuota_id} (pago parcial): "
                    f"Hoy={hoy} >= Venc. siguiente cuota={siguiente_cuota.fecha_vencimiento}"
                )
                return False
        else:
            # Es la última cuota del préstamo: usar lógica normal de 30 días
            # No congelar mora si ya pasaron los 30 días de tolerancia
            logger.info(
                f"Cuota {cuota.cuota_id} es la última del préstamo. "
                f"Aplicando lógica normal de mora."
            )
            return False
    
    @staticmethod
    def obtener_siguiente_cuota(cuota: 'Cuota') -> Optional['Cuota']:
        """
        Obtiene la siguiente cuota del mismo préstamo.
        """
        return Cuota.query.filter_by(
            prestamo_id=cuota.prestamo_id,
            numero_cuota=cuota.numero_cuota + 1
        ).first()

    staticmethod
    def calcular_mora_cuota(
        monto_a_aplicar: Decimal,
        fecha_vencimiento: date,
        numero_meses_atraso: int = None
    ) -> Decimal:
        """
        Calcula la mora de una cuota.
        
        La mora es 1% FIJO del monto, sin importar cuántos meses hayan pasado.
        """
        if numero_meses_atraso is None:
            numero_meses_atraso = MoraService.calcular_meses_atraso(fecha_vencimiento)
        
        if numero_meses_atraso <= 0:
            return Decimal('0.00')
        
        mora = monto_a_aplicar * MoraService.TASA_MORA_MENSUAL
        return mora.quantize(Decimal('0.01'))

    @staticmethod
    def actualizar_mora_cuota(cuota_id: int) -> Tuple[Decimal, str]:
        """
        Actualiza la mora de una cuota basada en su estado.
        
        REGLAS:
        1. Si la cuota NO está vencida → mora = 0
        2. Si tiene pago parcial Y aún no vence la siguiente cuota → mora = 0 (CONGELADA)
        3. Si tiene pago parcial Y ya venció la siguiente cuota → mora = 1% del SALDO PENDIENTE
        4. Si no tiene pago (saldo completo) y está vencida → mora = 1% del saldo pendiente
        """
        try:
            cuota = Cuota.query.get(cuota_id)
            if not cuota:
                return Decimal('0.00'), f"Cuota {cuota_id} no encontrada"

            meses_atraso = MoraService.calcular_meses_atraso(cuota.fecha_vencimiento)

            # REGLA 1: Si no está vencida (ni siquiera 1 día), no hay mora
            if meses_atraso <= 0:
                cuota.mora_acumulada = Decimal('0.00')
                db.session.commit()
                return Decimal('0.00'), "Cuota no está vencida"

            # REGLA 2: Verificar si la mora está CONGELADA por pago parcial
            if MoraService.mora_congelada_por_pago_parcial(cuota):
                cuota.mora_acumulada = Decimal('0.00')
                db.session.commit()
                return Decimal('0.00'), "Mora congelada por pago parcial (esperando vencimiento de siguiente cuota)"

            # REGLA 3 y 4: Calcular mora sobre saldo pendiente
            if cuota.saldo_pendiente and cuota.saldo_pendiente > 0:
                mora_nueva = MoraService.calcular_mora_cuota(
                    cuota.saldo_pendiente,
                    cuota.fecha_vencimiento,
                    meses_atraso
                )
                
                cuota.mora_generada = mora_nueva
                cuota.mora_acumulada = mora_nueva
                
                db.session.commit()
                
                logger.info(
                    f"Mora actualizada para cuota {cuota_id}: "
                    f"Mora={mora_nueva}, Saldo={cuota.saldo_pendiente}"
                )
                
                return mora_nueva, f"Mora calculada: {mora_nueva}"
            else:
                # Cuota completamente pagada
                mora_historica = cuota.mora_generada or Decimal('0.00')
                
                logger.info(
                    f"Cuota {cuota_id} pagada. Mora histórica: {mora_historica}"
                )
                
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
                mora_por_cuota[cuota.numero_cuota] = {
                    'mora': float(mora),
                    'mensaje': mensaje,
                    'es_pago_parcial': MoraService.es_pago_parcial(cuota)
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