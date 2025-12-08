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
        meses_atraso = dias_atraso // MoraService.DIAS_POR_MES
        return meses_atraso

    @staticmethod
    def calcular_mora_cuota(
        monto_a_aplicar: Decimal,
        fecha_vencimiento: date,
        numero_meses_atraso: int = None
    ) -> Decimal:
        """
        Calcula la mora de una cuota.
        
        La mora es 1% del monto por cada mes de atraso.
        Solo se aplica si está vencida.
        
        Args:
            monto_a_aplicar: Monto sobre el cual calcular mora (saldo o monto completo)
            fecha_vencimiento: Fecha de vencimiento
            numero_meses_atraso: Meses de atraso (se calcula si no se proporciona)
            
        Returns:
            Monto de mora a aplicar
        """
        if numero_meses_atraso is None:
            numero_meses_atraso = MoraService.calcular_meses_atraso(fecha_vencimiento)
        
        # Solo aplica mora si hay atraso
        if numero_meses_atraso <= 0:
            return Decimal('0.00')
        
        # Mora = monto * 1% * número de meses
        mora = monto_a_aplicar * MoraService.TASA_MORA_MENSUAL * numero_meses_atraso
        return mora.quantize(Decimal('0.01'))

    @staticmethod
    def actualizar_mora_cuota(cuota_id: int) -> Tuple[Decimal, str]:
        """
        Actualiza la mora de una cuota basada en su estado.
        
        Reglas:
        - Si la cuota no está vencida: mora = 0
        - Si está vencida pero sin pago: mora = 1% del monto completo por mes
        - Si tiene pago parcial: mora = 1% del saldo pendiente por mes
        
        Args:
            cuota_id: ID de la cuota
            
        Returns:
            Tuple[nueva_mora, mensaje]
        """
        try:
            cuota = Cuota.query.get(cuota_id)
            if not cuota:
                return Decimal('0.00'), f"Cuota {cuota_id} no encontrada"

            meses_atraso = MoraService.calcular_meses_atraso(cuota.fecha_vencimiento)

            # Si no está vencida, no hay mora
            if meses_atraso <= 0:
                cuota.mora_acumulada = Decimal('0.00')
                db.session.commit()
                return Decimal('0.00'), "Cuota no está vencida"

            # Si está vencida, calcular mora
            # Si hay pago parcial, mora se aplica al saldo pendiente
            # Si no hay pago, mora se aplica al monto completo
            if cuota.saldo_pendiente and cuota.saldo_pendiente > 0:
                mora = MoraService.calcular_mora_cuota(
                    cuota.saldo_pendiente,
                    cuota.fecha_vencimiento,
                    meses_atraso
                )
            else:
                mora = MoraService.calcular_mora_cuota(
                    cuota.monto_cuota,
                    cuota.fecha_vencimiento,
                    meses_atraso
                )

            cuota.mora_acumulada = mora
            db.session.commit()

            logger.info(
                f"Mora actualizada para cuota {cuota_id}: "
                f"Mora={mora}, Saldo Pendiente={cuota.saldo_pendiente}"
            )

            return mora, f"Mora calculada: {mora}"

        except Exception as exc:
            logger.error(f"Error al actualizar mora de cuota {cuota_id}: {exc}")
            return Decimal('0.00'), f"Error: {str(exc)}"

    @staticmethod
    def actualizar_mora_prestamo(prestamo_id: int) -> Dict[str, Any]:
        """
        Actualiza la mora de todas las cuotas de un préstamo.
        
        Args:
            prestamo_id: ID del préstamo
            
        Returns:
            Diccionario con resumen de moras actualizadas
        """
        try:
            cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).all()
            
            total_mora = Decimal('0.00')
            mora_por_cuota = {}

            for cuota in cuotas:
                mora, _ = MoraService.actualizar_mora_cuota(cuota.cuota_id)
                total_mora += mora
                mora_por_cuota[cuota.numero_cuota] = float(mora)

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