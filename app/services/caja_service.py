# → Servicio para gestión de cuadre de caja
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy import func, and_
from app.common.extensions import db
from app.models.pago import Pago, MedioPagoEnum
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)

# → Servicio para gestión de cuadre de caja
class CajaService:
# → Obtiene el resumen diario de caja para una fecha específica
    @staticmethod
    def obtener_resumen_diario(fecha: date) -> Dict:
        """Returns: Dict con totales por medio de pago y resumen general"""
        try:
            # Pagos del día agrupados por medio de pago
            pagos_dia = db.session.query(
                Pago.medio_pago,
                func.count(Pago.pago_id).label('cantidad'),
                func.sum(Pago.monto_pagado).label('total'),
                func.sum(Pago.monto_mora).label('total_mora'),
                func.sum(Pago.monto_pagado - Pago.monto_mora).label('total_capital')
            ).filter(
                func.date(Pago.fecha_pago) == fecha
            ).group_by(Pago.medio_pago).all()
            
            # Construir detalle por medio de pago
            detalle_medios = []
            total_general = Decimal('0')
            total_mora_general = Decimal('0')
            total_capital_general = Decimal('0')
            cantidad_total = 0
            
            for medio, cantidad, total, mora, capital in pagos_dia:
                detalle_medios.append({
                    'medio_pago': medio.value,
                    'cantidad_pagos': cantidad,
                    'total': float(total or 0),
                    'total_mora': float(mora or 0),
                    'total_capital': float(capital or 0)
                })
                total_general += (total or Decimal('0'))
                total_mora_general += (mora or Decimal('0'))
                total_capital_general += (capital or Decimal('0'))
                cantidad_total += cantidad
            
            return {
                'fecha': fecha.isoformat(),
                'detalle_por_medio': detalle_medios,
                'resumen': {
                    'cantidad_total_pagos': cantidad_total,
                    'total_recaudado': float(total_general),
                    'total_mora_cobrada': float(total_mora_general),
                    'total_capital_cobrado': float(total_capital_general)
                }
            }
            
        except Exception as exc:
            logger.error(f"Error en obtener_resumen_diario: {exc}", exc_info=True)
            raise
    
    @staticmethod
    def obtener_resumen_periodo(fecha_inicio: date, fecha_fin: date) -> Dict:
        """Args: fecha_inicio + fecha_fin
        Returns:
            Dict con totales del periodo y detalle por día  """
        try:
            # Pagos del periodo agrupados por fecha y medio de pago
            pagos_periodo = db.session.query(
                func.date(Pago.fecha_pago).label('fecha'),
                Pago.medio_pago,
                func.count(Pago.pago_id).label('cantidad'),
                func.sum(Pago.monto_pagado).label('total'),
                func.sum(Pago.monto_mora).label('total_mora')
            ).filter(
                and_(
                    func.date(Pago.fecha_pago) >= fecha_inicio,
                    func.date(Pago.fecha_pago) <= fecha_fin
                )
            ).group_by(
                func.date(Pago.fecha_pago),
                Pago.medio_pago
            ).order_by(func.date(Pago.fecha_pago)).all()
            
            # Organizar por fecha
            detalle_por_dia = {}
            total_periodo = Decimal('0')
            total_mora_periodo = Decimal('0')
            cantidad_total_periodo = 0
            
            for fecha, medio, cantidad, total, mora in pagos_periodo:
                fecha_str = fecha.isoformat()
                
                if fecha_str not in detalle_por_dia:
                    detalle_por_dia[fecha_str] = {
                        'fecha': fecha_str,
                        'medios': [],
                        'total_dia': Decimal('0'),
                        'cantidad_dia': 0
                    }
                
                detalle_por_dia[fecha_str]['medios'].append({
                    'medio_pago': medio.value,
                    'cantidad': cantidad,
                    'total': float(total or 0),
                    'total_mora': float(mora or 0)
                })
                
                detalle_por_dia[fecha_str]['total_dia'] += (total or Decimal('0'))
                detalle_por_dia[fecha_str]['cantidad_dia'] += cantidad
                total_periodo += (total or Decimal('0'))
                total_mora_periodo += (mora or Decimal('0'))
                cantidad_total_periodo += cantidad
            
            # Convertir a lista y formatear totales
            detalle_lista = []
            for dia in detalle_por_dia.values():
                dia['total_dia'] = float(dia['total_dia'])
                detalle_lista.append(dia)
            
            return {
                'periodo': {
                    'fecha_inicio': fecha_inicio.isoformat(),
                    'fecha_fin': fecha_fin.isoformat()
                },
                'detalle_por_dia': detalle_lista,
                'resumen_periodo': {
                    'cantidad_total_pagos': cantidad_total_periodo,
                    'total_recaudado': float(total_periodo),
                    'total_mora_cobrada': float(total_mora_periodo),
                    'total_capital_cobrado': float(total_periodo - total_mora_periodo),
                    'dias_con_movimiento': len(detalle_por_dia)
                }
            }
            
        except Exception as exc:
            logger.error(f"Error en obtener_resumen_periodo: {exc}", exc_info=True)
            raise
    
    @staticmethod
    def obtener_detalle_pagos_dia(fecha: date) -> List[Dict]:
        """Args: fecha: Fecha a consultar 
        Returns: Lista de pagos con información del cliente y préstamo        """
        try:
            pagos = db.session.query(Pago).filter(
                func.date(Pago.fecha_pago) == fecha
            ).order_by(Pago.fecha_pago).all()
            
            detalle = []
            for pago in pagos:
                cuota = pago.cuota
                prestamo = cuota.prestamo
                cliente = prestamo.cliente
                
                detalle.append({
                    'pago_id': pago.pago_id,
                    'hora': pago.fecha_pago.strftime('%H:%M:%S'),
                    'comprobante': pago.comprobante_referencia,
                    'cliente': {
                        'nombre': cliente.nombre_completo,
                        'dni': cliente.dni
                    },
                    'prestamo_id': prestamo.prestamo_id,
                    'cuota_numero': cuota.numero_cuota,
                    'medio_pago': pago.medio_pago.value,
                    'monto_pagado': float(pago.monto_pagado),
                    'monto_mora': float(pago.monto_mora),
                    'monto_capital': float(pago.monto_pagado - pago.monto_mora),
                    'observaciones': pago.observaciones
                })
            
            return detalle
            
        except Exception as exc:
            logger.error(f"Error en obtener_detalle_pagos_dia: {exc}", exc_info=True)
            raise

# → Obtiene estadísticas generales de caja - últimos 30 días    
    @staticmethod
    def obtener_estadisticas_caja() -> Dict:
        """ Returns: Dict con promedios, tendencias y comparativas """
        try:
            from datetime import timedelta
            
            hoy = date.today()
            hace_30_dias = hoy - timedelta(days=30)
            
            # Total últimos 30 días
            total_30d = db.session.query(
                func.sum(Pago.monto_pagado)
            ).filter(
                func.date(Pago.fecha_pago) >= hace_30_dias
            ).scalar() or Decimal('0')
            
            # Promedio diario
            dias_con_pagos = db.session.query(
                func.count(func.distinct(func.date(Pago.fecha_pago)))
            ).filter(
                func.date(Pago.fecha_pago) >= hace_30_dias
            ).scalar() or 1
            
            promedio_diario = total_30d / dias_con_pagos
            
            # Medio de pago más usado
            medio_mas_usado = db.session.query(
                Pago.medio_pago,
                func.count(Pago.pago_id).label('cantidad')
            ).filter(
                func.date(Pago.fecha_pago) >= hace_30_dias
            ).group_by(Pago.medio_pago).order_by(func.count(Pago.pago_id).desc()).first()
            
            return {
                'periodo_analisis': '30 días',
                'total_recaudado_30d': float(total_30d),
                'dias_con_movimiento': dias_con_pagos,
                'promedio_diario': float(promedio_diario),
                'medio_pago_mas_usado': medio_mas_usado[0].value if medio_mas_usado else None,
                'veces_usado': medio_mas_usado[1] if medio_mas_usado else 0
            }
            
        except Exception as exc:
            logger.error(f"Error en obtener_estadisticas_caja: {exc}", exc_info=True)
            raise
