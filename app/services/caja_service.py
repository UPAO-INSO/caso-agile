# → Servicio para gestión de cuadre de caja
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy import func, and_
from app.common.extensions import db
from app.models.pago import Pago, MedioPagoEnum
from app.models.prestamo import Prestamo
from app.models.egreso import Egreso
from app.models.apertura_caja import AperturaCaja

logger = logging.getLogger(__name__)

# → Servicio para gestión de cuadre de caja
class CajaService:
# → Obtiene el resumen diario de caja para una fecha específica
    @staticmethod
    def obtener_resumen_diario(fecha: date) -> Dict:
        """Returns: Dict con totales por medio de pago y resumen general"""
        try:
            logger.info(f"Obteniendo resumen de caja para fecha: {fecha}")
            
            # Pagos del día agrupados por medio de pago
            pagos_dia = db.session.query(
                Pago.medio_pago,
                func.count(Pago.pago_id).label('cantidad'),
                func.sum(Pago.monto_pagado).label('total'),
                func.sum(Pago.monto_mora).label('total_mora'),
                func.sum(Pago.monto_pagado - Pago.monto_mora).label('total_capital'),
                func.sum(Pago.ajuste_redondeo).label('total_ajuste')
            ).filter(
                Pago.fecha_pago == fecha
            ).group_by(Pago.medio_pago).all()
            
            logger.info(f"Pagos encontrados: {len(pagos_dia)} grupos de medios de pago")
            
            # Construir detalle por medio de pago
            detalle_medios = []
            total_general = Decimal('0')
            total_mora_general = Decimal('0')
            total_capital_general = Decimal('0')
            total_ajuste_general = Decimal('0')
            cantidad_total = 0
            
            for medio, cantidad, total, mora, capital, ajuste in pagos_dia:
                logger.info(f"  {medio.value}: {cantidad} pagos, Total: S/ {total}, Ajuste: S/ {ajuste}")
                detalle_medios.append({
                    'medio_pago': medio.value,
                    'cantidad_pagos': cantidad,
                    'total': float(total or 0),
                    'total_mora': float(mora or 0),
                    'total_capital': float(capital or 0),
                    'ajuste_redondeo': float(ajuste or 0)
                })
                total_general += (total or Decimal('0'))
                total_mora_general += (mora or Decimal('0'))
                total_capital_general += (capital or Decimal('0'))
                total_ajuste_general += (ajuste or Decimal('0'))
                cantidad_total += cantidad
            # Total egresos del día
            total_egresos = db.session.query(func.sum(Egreso.monto)).filter(func.date(Egreso.fecha_registro) == fecha).scalar() or Decimal('0')

            return {
                'fecha': fecha.isoformat(),
                'detalle_por_medio': detalle_medios,
                'resumen': {
                    'cantidad_total_pagos': cantidad_total,
                    'total_recaudado': float(total_general),
                    'total_mora_cobrada': float(total_mora_general),
                    'total_capital_cobrado': float(total_capital_general),
                    'total_ajuste_redondeo': float(total_ajuste_general),
                    'total_egresos': float(total_egresos),
                    'nota_ajuste': 'Positivo = ganancia del negocio, Negativo = condonación al cliente'
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
                func.sum(Pago.monto_mora).label('total_mora'),
                func.sum(Pago.ajuste_redondeo).label('total_ajuste')
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
            total_ajuste_periodo = Decimal('0')
            cantidad_total_periodo = 0
            
            for fecha, medio, cantidad, total, mora, ajuste in pagos_periodo:
                fecha_str = fecha.isoformat()
                
                if fecha_str not in detalle_por_dia:
                    detalle_por_dia[fecha_str] = {
                        'fecha': fecha_str,
                        'medios': [],
                        'total_dia': Decimal('0'),
                        'ajuste_dia': Decimal('0'),
                        'cantidad_dia': 0
                    }
                
                detalle_por_dia[fecha_str]['medios'].append({
                    'medio_pago': medio.value,
                    'cantidad': cantidad,
                    'total': float(total or 0),
                    'total_mora': float(mora or 0),
                    'ajuste_redondeo': float(ajuste or 0)
                })
                
                detalle_por_dia[fecha_str]['total_dia'] += (total or Decimal('0'))
                detalle_por_dia[fecha_str]['ajuste_dia'] += (ajuste or Decimal('0'))
                detalle_por_dia[fecha_str]['cantidad_dia'] += cantidad
                total_periodo += (total or Decimal('0'))
                total_mora_periodo += (mora or Decimal('0'))
                total_ajuste_periodo += (ajuste or Decimal('0'))
                cantidad_total_periodo += cantidad
            
            # Convertir a lista y formatear totales
            detalle_lista = []
            for dia in detalle_por_dia.values():
                dia['total_dia'] = float(dia['total_dia'])
                dia['ajuste_dia'] = float(dia['ajuste_dia'])
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
                    'total_ajuste_redondeo': float(total_ajuste_periodo),
                    'dias_con_movimiento': len(detalle_por_dia),
                    'nota_ajuste': 'Positivo = ganancia del negocio, Negativo = condonación al cliente'
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
            logger.info(f"Obteniendo detalle de pagos para fecha: {fecha}")
            
            pagos = db.session.query(Pago).filter(
                Pago.fecha_pago == fecha
            ).order_by(Pago.fecha_pago).all()
            
            logger.info(f"Pagos detallados encontrados: {len(pagos)}")
            
            detalle = []
            for pago in pagos:
                cuota = pago.cuota
                prestamo = cuota.prestamo
                cliente = prestamo.cliente
                
                # Como no tenemos hora exacta, usamos el ID del pago para simular una hora
                hora_ficticia = f"{8 + (pago.pago_id % 12):02d}:{(pago.pago_id * 15) % 60:02d}:00"
                
                detalle.append({
                    'pago_id': pago.pago_id,
                    'hora': hora_ficticia,
                    'comprobante': pago.comprobante_referencia,
                    'cliente': {
                        'nombre': cliente.nombre_completo,
                        'dni': cliente.dni
                    },
                    'prestamo_id': prestamo.prestamo_id,
                    'cuota_numero': cuota.numero_cuota,
                    'medio_pago': pago.medio_pago.value,
                    'monto_contable': float(pago.monto_contable) if pago.monto_contable else float(pago.monto_pagado),
                    'monto_pagado': float(pago.monto_pagado),
                    'ajuste_redondeo': float(pago.ajuste_redondeo),
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

    @staticmethod
    def registrar_egreso(monto: Decimal, concepto: str, pago_id: Optional[int] = None, usuario_id: Optional[int] = None) -> Dict:
        """Registra un egreso en la caja (por ejemplo: vuelto entregado al cliente).

        Args:
            monto: Monto del egreso (positivo)
            concepto: Concepto/descripción del egreso
            pago_id: (opcional) pago asociado al egreso
            usuario_id: (opcional) usuario que registró el egreso

        Returns:
            Diccionario con el egreso registrado
        """
        try:
            from app.models import Egreso

            if monto <= 0:
                raise ValueError('El monto del egreso debe ser mayor que cero')

            nuevo = Egreso(
                pago_id=pago_id,
                monto=monto,
                concepto=concepto,
                usuario_id=usuario_id
            )
            db.session.add(nuevo)
            db.session.commit()

            logger.info(f"Egreso registrado: ID={nuevo.egreso_id}, Monto={monto}, Pago={pago_id}")

            return nuevo.to_dict()

        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error en registrar_egreso: {exc}", exc_info=True)
            raise

    @staticmethod
    def registrar_apertura(fecha: date, monto: Decimal, usuario_id: Optional[int] = None) -> Dict:
        """Registra la apertura de caja para una fecha determinada.

        Si ya existe una apertura para la fecha, la actualiza con el nuevo monto.
        """
        try:
            if monto < Decimal('0'):
                raise ValueError('El monto de apertura no puede ser negativo')

            apertura = db.session.query(AperturaCaja).filter(AperturaCaja.fecha == fecha).first()
            if apertura:
                apertura.monto = monto
                apertura.usuario_id = usuario_id
                apertura.fecha_registro = datetime.utcnow()
            else:
                apertura = AperturaCaja(fecha=fecha, monto=monto, usuario_id=usuario_id)
                db.session.add(apertura)

            db.session.commit()
            return apertura.to_dict()

        except Exception as exc:
            db.session.rollback()
            logger.error(f"Error en registrar_apertura: {exc}", exc_info=True)
            raise

    @staticmethod
    def obtener_apertura_por_fecha(fecha: date) -> Optional[Dict]:
        """Devuelve la apertura registrada para la fecha, o None si no existe."""
        try:
            apertura = db.session.query(AperturaCaja).filter(AperturaCaja.fecha == fecha).first()
            return apertura.to_dict() if apertura else None
        except Exception as exc:
            logger.error(f"Error en obtener_apertura_por_fecha: {exc}", exc_info=True)
            raise
