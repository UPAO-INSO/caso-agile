import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Tuple, Optional, Dict, Any, List
from app.common.extensions import db
from app.models import Cuota, Prestamo

logger = logging.getLogger(__name__)

class MoraService:
    """Servicio para calcular y aplicar mora a las cuotas"""

    TASA_MORA_POR_PERIODO = Decimal('0.01')  # 1% por período vencido

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
    def obtener_fechas_vencimiento_prestamo(prestamo_id: int) -> List[date]:
        """
        Obtiene todas las fechas de vencimiento de las cuotas de un préstamo,
        ordenadas cronológicamente.
        
        Args:
            prestamo_id: ID del préstamo
            
        Returns:
            Lista de fechas de vencimiento ordenadas
        """
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota.asc()).all()
        return [c.fecha_vencimiento for c in cuotas]

    @staticmethod
    def calcular_periodos_vencidos(cuota: Cuota, fecha_referencia: date = None) -> int:
        """
        Calcula cuántos períodos (fechas de vencimiento) han pasado desde que venció la cuota.
        
        Un período = intervalo entre fecha de vencimiento de esta cuota y la siguiente.
        
        Args:
            cuota: Objeto Cuota
            fecha_referencia: Fecha para calcular (default: hoy)
            
        Returns:
            Número de períodos vencidos (0 si no está vencida)
        """
        if fecha_referencia is None:
            fecha_referencia = date.today()
        
        # Si no está vencida, no hay períodos vencidos
        if fecha_referencia <= cuota.fecha_vencimiento:
            return 0
        
        # Obtener todas las fechas de vencimiento del préstamo
        fechas_vencimiento = MoraService.obtener_fechas_vencimiento_prestamo(cuota.prestamo_id)
        
        if not fechas_vencimiento:
            return 0
        
        # Encontrar el índice de esta cuota
        try:
            idx_cuota_actual = fechas_vencimiento.index(cuota.fecha_vencimiento)
        except ValueError:
            # Si no se encuentra, calcular de forma aproximada
            logger.warning(f"Fecha de vencimiento de cuota {cuota.cuota_id} no encontrada en lista")
            return 1 if fecha_referencia > cuota.fecha_vencimiento else 0
        
        # Contar cuántas fechas de vencimiento han pasado desde la fecha de esta cuota
        periodos_vencidos = 0
        
        for i in range(idx_cuota_actual, len(fechas_vencimiento)):
            if fechas_vencimiento[i] < fecha_referencia:
                periodos_vencidos += 1
            else:
                break
        
        # Si estamos más allá de la última fecha de vencimiento, contar períodos adicionales
        if fecha_referencia > fechas_vencimiento[-1]:
            # Calcular el intervalo promedio entre cuotas
            if len(fechas_vencimiento) > 1:
                intervalo_promedio = (fechas_vencimiento[-1] - fechas_vencimiento[0]).days // (len(fechas_vencimiento) - 1)
            else:
                intervalo_promedio = 30  # Default a 30 días si solo hay una cuota
            
            dias_despues_ultima = (fecha_referencia - fechas_vencimiento[-1]).days
            periodos_adicionales = dias_despues_ultima // intervalo_promedio
            periodos_vencidos += periodos_adicionales
        
        return max(0, periodos_vencidos)

    @staticmethod
    def cuota_tiene_pago_en_periodo_actual(cuota: Cuota) -> bool:
        """
        Verifica si la cuota tuvo un pago (parcial o total) en el período actual.
        
        El período actual es desde la fecha de vencimiento de esta cuota hasta
        la fecha de vencimiento de la siguiente cuota.
        
        Args:
            cuota: Objeto Cuota
            
        Returns:
            True si hubo pago en el período actual
        """
        if not cuota.pagos:
            return False
        
        # Obtener fechas de vencimiento del préstamo
        fechas_vencimiento = MoraService.obtener_fechas_vencimiento_prestamo(cuota.prestamo_id)
        
        try:
            idx_cuota = fechas_vencimiento.index(cuota.fecha_vencimiento)
        except ValueError:
            return False
        
        # Definir el período actual
        fecha_inicio_periodo = cuota.fecha_vencimiento
        
        # La fecha fin del período es la siguiente fecha de vencimiento
        if idx_cuota + 1 < len(fechas_vencimiento):
            fecha_fin_periodo = fechas_vencimiento[idx_cuota + 1]
        else:
            # Si es la última cuota, usar un intervalo estimado
            if len(fechas_vencimiento) > 1:
                intervalo = (fechas_vencimiento[-1] - fechas_vencimiento[-2]).days
            else:
                intervalo = 30
            fecha_fin_periodo = cuota.fecha_vencimiento + timedelta(days=intervalo)
        
        hoy = date.today()
        
        # Solo verificar si estamos dentro del período actual
        if not (fecha_inicio_periodo < hoy <= fecha_fin_periodo):
            return False
        
        # Verificar si hay algún pago dentro de este período
        for pago in cuota.pagos:
            if fecha_inicio_periodo < pago.fecha_pago <= fecha_fin_periodo:
                return True
        
        return False

    @staticmethod
    def calcular_mora_cuota(
        cuota: Cuota,
        fecha_referencia: date = None
    ) -> Decimal:
        """
        Calcula la mora de una cuota considerando:
        - Períodos vencidos (basados en fechas de vencimiento, no días fijos)
        - Pagos parciales que anulan la mora del período actual
        - La mora se aplica al saldo pendiente, no al monto original
        
        Args:
            cuota: Objeto Cuota
            fecha_referencia: Fecha para calcular (default: hoy)
            
        Returns:
            Monto de mora a aplicar
        """
        if fecha_referencia is None:
            fecha_referencia = date.today()
        
        # Si la cuota está pagada completamente, no hay mora
        if cuota.saldo_pendiente <= 0:
            return Decimal('0.00')
        
        # Si no está vencida, no hay mora
        if fecha_referencia <= cuota.fecha_vencimiento:
            return Decimal('0.00')
        
        # Verificar si hubo pago parcial en el período actual
        # Si hubo pago parcial, la mora del período actual se anula
        pago_en_periodo_actual = MoraService.cuota_tiene_pago_en_periodo_actual(cuota)
        
        # Calcular períodos vencidos
        periodos_vencidos = MoraService.calcular_periodos_vencidos(cuota, fecha_referencia)
        
        if periodos_vencidos <= 0:
            return Decimal('0.00')
        
        # Si hubo pago parcial en el período actual, descontar 1 período esto esta raro
        if pago_en_periodo_actual and periodos_vencidos > 0:
            periodos_vencidos -= 1
            logger.info(f"Cuota {cuota.cuota_id}: Pago parcial detectado, períodos de mora reducidos a {periodos_vencidos}")
        
        if periodos_vencidos <= 0:
            return Decimal('0.00')
        
        # La mora se aplica al SALDO PENDIENTE, no al monto original
        # 1% por cada período vencido
        mora = cuota.saldo_pendiente * MoraService.TASA_MORA_POR_PERIODO * periodos_vencidos
        
        logger.info(
            f"Cuota {cuota.cuota_id}: Saldo={cuota.saldo_pendiente}, "
            f"Períodos vencidos={periodos_vencidos}, Mora calculada={mora}"
        )
        
        return mora.quantize(Decimal('0.01'))

    @staticmethod
    def actualizar_mora_cuota(cuota_id: int) -> Tuple[Decimal, str]:
        """
        Actualiza la mora de una cuota basada en su estado.
        
        Reglas:
        - Si la cuota no está vencida: mora = 0
        - Si está vencida: mora = 1% del saldo pendiente por período vencido
        - Si hubo pago parcial en el período actual: se descuenta ese período
        
        Args:
            cuota_id: ID de la cuota
            
        Returns:
            Tuple[nueva_mora, mensaje]
        """
        try:
            cuota = Cuota.query.get(cuota_id)
            if not cuota:
                return Decimal('0.00'), "Cuota no encontrada"

            # Si la cuota está completamente pagada, no actualizar mora
            if cuota.saldo_pendiente <= 0:
                logger.info(f"Cuota {cuota_id}: Ya está pagada, mora histórica mantenida")
                return cuota.mora_acumulada, "Cuota pagada - mora histórica mantenida"

            # Calcular nueva mora
            nueva_mora = MoraService.calcular_mora_cuota(cuota)
            
            # Actualizar campos de mora
            mora_anterior = cuota.mora_acumulada or Decimal('0.00')
            
            # mora_generada: Total histórico de mora generada
            # mora_acumulada: Mora pendiente de pago (puede ser 0 si se pagó)
            if nueva_mora > mora_anterior:
                cuota.mora_generada = (cuota.mora_generada or Decimal('0.00')) + (nueva_mora - mora_anterior)
            
            cuota.mora_acumulada = nueva_mora
            
            db.session.commit()
            
            mensaje = f"Mora actualizada: S/ {mora_anterior} -> S/ {nueva_mora}"
            logger.info(f"Cuota {cuota_id}: {mensaje}")
            
            return nueva_mora, mensaje

        except Exception as exc:
            logger.error(f"Error al actualizar mora de cuota {cuota_id}: {exc}")
            db.session.rollback()
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
            cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota.asc()).all()
            
            if not cuotas:
                return {
                    'prestamo_id': prestamo_id,
                    'cuotas_actualizadas': 0,
                    'total_mora': Decimal('0.00'),
                    'mensaje': 'No se encontraron cuotas'
                }
            
            total_mora = Decimal('0.00')
            cuotas_con_mora = 0
            detalles = []
            
            for cuota in cuotas:
                mora, mensaje = MoraService.actualizar_mora_cuota(cuota.cuota_id)
                total_mora += mora
                
                if mora > 0:
                    cuotas_con_mora += 1
                
                detalles.append({
                    'cuota_id': cuota.cuota_id,
                    'numero_cuota': cuota.numero_cuota,
                    'mora': float(mora),
                    'saldo_pendiente': float(cuota.saldo_pendiente),
                    'mensaje': mensaje
                })
            
            logger.info(f"Préstamo {prestamo_id}: Mora total actualizada = S/ {total_mora}")
            
            return {
                'prestamo_id': prestamo_id,
                'cuotas_actualizadas': len(cuotas),
                'cuotas_con_mora': cuotas_con_mora,
                'total_mora': float(total_mora),
                'detalles': detalles,
                'mensaje': 'Moras actualizadas correctamente'
            }

        except Exception as exc:
            logger.error(f"Error al actualizar moras del préstamo {prestamo_id}: {exc}")
            db.session.rollback()
            return {
                'prestamo_id': prestamo_id,
                'error': str(exc),
                'mensaje': 'Error al actualizar moras'
            }

    @staticmethod
    def congelar_mora_por_pago_parcial(cuota_id: int) -> Tuple[bool, str]:
        """
        Congela/anula la mora del período actual cuando se realiza un pago parcial.
        
        Esta función se llama después de registrar un pago parcial para
        resetear la mora del período actual.
        
        Args:
            cuota_id: ID de la cuota
            
        Returns:
            Tuple[éxito, mensaje]
        """
        try:
            cuota = Cuota.query.get(cuota_id)
            if not cuota:
                return False, "Cuota no encontrada"
            
            # Si la cuota está completamente pagada, no hacer nada
            if cuota.saldo_pendiente <= 0:
                return True, "Cuota completamente pagada"
            
            # Recalcular la mora considerando el pago parcial
            # (la función calcular_mora_cuota ya tiene en cuenta los pagos parciales)
            nueva_mora = MoraService.calcular_mora_cuota(cuota)
            
            mora_anterior = cuota.mora_acumulada or Decimal('0.00')
            cuota.mora_acumulada = nueva_mora
            
            db.session.commit()
            
            mensaje = f"Mora congelada por pago parcial: S/ {mora_anterior} -> S/ {nueva_mora}"
            logger.info(f"Cuota {cuota_id}: {mensaje}")
            
            return True, mensaje

        except Exception as exc:
            logger.error(f"Error al congelar mora de cuota {cuota_id}: {exc}")
            db.session.rollback()
            return False, f"Error: {str(exc)}"

    @staticmethod
    def calcular_meses_atraso(fecha_vencimiento: date) -> int:
        """
        DEPRECATED: Usar calcular_periodos_vencidos en su lugar.
        
        Mantiene compatibilidad con código existente.
        Ahora calcula basado en períodos de cuotas, no días fijos.
        """
        dias_atraso = MoraService.calcular_dias_atraso(fecha_vencimiento)
        if dias_atraso <= 0:
            return 0
        # Aproximación: si no tenemos contexto de la cuota, usar 30 días
        return ((dias_atraso - 1) // 30) + 1