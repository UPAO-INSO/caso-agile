"""
Financial Service
Maneja los cálculos financieros de la aplicación.
Centraliza fórmulas de TEA, TEM, cronogramas y sistema francés.
"""

import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

logger = logging.getLogger(__name__)


class FinancialService:
    """Servicio para cálculos financieros"""
    
    # Constantes
    UIT_VALOR = Decimal('5350.00')  # UIT Perú 2025
    
    @staticmethod
    def tea_to_tem(tea):
        """
        Convierte Tasa Efectiva Anual (TEA) a Tasa Efectiva Mensual (TEM).
        Fórmula: TEM = (1 + TEA)^(1/12) - 1
        
        Args:
            tea: Tasa Efectiva Anual (como porcentaje, ej: 10.00 para 10%)
            
        Returns:
            Decimal: Tasa Efectiva Mensual (como decimal, ej: 0.00797)
        """
        try:
            tea_decimal = Decimal(str(tea)) / Decimal('100.00')
            tem = ((Decimal('1') + tea_decimal) ** (Decimal('1') / Decimal('12'))) - Decimal('1')
            return tem
        except (InvalidOperation, Exception) as e:
            logger.error(f"Error al convertir TEA a TEM: {e}")
            return Decimal('0')
    
    @staticmethod
    def calcular_cuota_fija(monto, tea, plazo_meses):
        """
        Calcula la cuota fija mensual usando el sistema francés.
        
        Fórmula: Cuota = Monto * [TEM * (1 + TEM)^n] / [(1 + TEM)^n - 1]
        
        Args:
            monto: Monto del préstamo (Decimal)
            tea: Tasa Efectiva Anual en porcentaje (Decimal)
            plazo_meses: Número de meses del préstamo (int)
            
        Returns:
            Decimal: Cuota mensual fija
        """
        try:
            # Validaciones
            if plazo_meses <= 0 or monto <= 0 or tea < 0:
                logger.error(
                    f"Validación fallida: monto={monto}, tea={tea}, plazo={plazo_meses}"
                )
                return Decimal('0.00')
            
            # Calcular TEM
            tem = FinancialService.tea_to_tem(tea)
            
            # Si TEM es 0, cuota sin interés
            if tem == Decimal('0'):
                return (monto / plazo_meses).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Aplicar fórmula sistema francés
            factor_num = tem * (Decimal('1') + tem) ** plazo_meses
            factor_den = (Decimal('1') + tem) ** plazo_meses - Decimal('1')
            
            if factor_den == Decimal('0'):
                logger.error(f"División por cero: TEM={tem}, Plazo={plazo_meses}")
                return Decimal('0.00')
            
            cuota = monto * (factor_num / factor_den)
            return cuota.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except InvalidOperation as e:
            logger.error(f"Error Decimal: {e}. Entrada: monto={monto}, tea={tea}, plazo={plazo_meses}")
            return Decimal('0.00')
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return Decimal('0.00')
    
    @staticmethod
    def generar_cronograma_pagos(monto_total, interes_tea, plazo, f_otorgamiento):
        """
        Genera el cronograma completo de pagos usando Sistema Francés con ajuste en última cuota.
        
        CARACTERÍSTICAS:
        - Sistema Francés: Cuota fija mensual (capital + interés)
        - Fechas: Cada 30 días exactos desde el otorgamiento
        - TEA correcta: 10% TEA sobre S/12000 = S/13200 total al año
        - Última cuota ajusta residuos para cuadre exacto
        
        Args:
            monto_total: Monto del préstamo (Decimal)
            interes_tea: TEA en porcentaje (Decimal) - ej: 10.00 para 10%
            plazo: Número de cuotas/meses (int)
            f_otorgamiento: Fecha de otorgamiento del préstamo (date)
            
        Returns:
            list: Lista de diccionarios con el cronograma detallado
        """
        try:
            cronograma = []
            
            # Convertir a Decimal para precisión
            P = Decimal(str(monto_total))
            N = int(plazo)
            tea_porcentaje = Decimal(str(interes_tea))
            
            # Calcular TEM (Tasa Efectiva Mensual) correctamente
            # TEM = (1 + TEA)^(1/12) - 1
            tea_decimal = tea_porcentaje / Decimal('100')
            tem = ((Decimal('1') + tea_decimal) ** (Decimal('1') / Decimal('12'))) - Decimal('1')
            
            # Calcular cuota regular usando sistema francés
            # Cuota = P * [TEM * (1 + TEM)^N] / [(1 + TEM)^N - 1]
            if tem == Decimal('0'):
                cuota_regular = (P / N).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                factor = (Decimal('1') + tem) ** N
                cuota_regular = (P * tem * factor / (factor - Decimal('1'))).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            
            if cuota_regular == Decimal('0'):
                logger.error("Cuota calculada es 0")
                return []
            
            # Variables para el cálculo iterativo
            saldo = P
            total_pagado = Decimal('0')
            
            # Generar cada cuota
            for i in range(1, N + 1):
                # Fecha: mismo día del mes, sumando meses
                # Si el mes siguiente no tiene el mismo día, Python ajusta al último día del mes automáticamente
                year = f_otorgamiento.year
                month = f_otorgamiento.month + i
                day = f_otorgamiento.day
                # Ajustar año y mes
                while month > 12:
                    year += 1
                    month -= 12
                try:
                    fecha_vencimiento = f_otorgamiento.replace(year=year, month=month, day=day)
                except ValueError:
                    # Si el mes no tiene ese día (ej: 31 de febrero), usar el último día del mes
                    from calendar import monthrange
                    last_day = monthrange(year, month)[1]
                    fecha_vencimiento = f_otorgamiento.replace(year=year, month=month, day=last_day)
                
                # Calcular interés sobre saldo pendiente
                interes = (saldo * tem).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                # Determinar si es la última cuota (cuota de ajuste)
                es_cuota_ajuste = (i == N)
                
                if es_cuota_ajuste:
                    # ÚLTIMA CUOTA: Absorbe todo el saldo restante
                    capital = saldo
                    monto_cuota = capital + interes
                    nuevo_saldo = Decimal('0.00')
                else:
                    # CUOTAS REGULARES: Cuota fija
                    monto_cuota = cuota_regular
                    capital = cuota_regular - interes
                    
                    # Protección: capital no puede ser negativo
                    if capital < Decimal('0'):
                        capital = Decimal('0.01')
                    
                    nuevo_saldo = saldo - capital
                
                # Agregar al cronograma
                cronograma.append({
                    'numero_cuota': i,
                    'fecha_vencimiento': fecha_vencimiento,
                    'monto_cuota': monto_cuota,
                    'monto_capital': capital,
                    'monto_interes': interes,
                    'saldo_capital': nuevo_saldo,
                    'es_cuota_ajuste': es_cuota_ajuste,
                    'dias': 30  # Siempre 30 días entre cuotas
                })
                
                # Actualizar acumuladores
                total_pagado += monto_cuota
                saldo = nuevo_saldo
            
            # Validaciones finales
            total_capital = sum(c['monto_capital'] for c in cronograma)
            total_interes = sum(c['monto_interes'] for c in cronograma)
            total_cuotas = sum(c['monto_cuota'] for c in cronograma)
            
            # Verificar que el capital pagado coincide con el préstamo
            diferencia_capital = abs(total_capital - P)
            if diferencia_capital > Decimal('0.02'):  # Tolerancia de 2 céntimos
                logger.warning(
                    f"Diferencia en capital: Esperado S/ {P}, Calculado S/ {total_capital}, "
                    f"Diferencia: S/ {diferencia_capital}"
                )
            
            # Calcular el total esperado con TEA (solo para referencia informativa)
            # Nota: El total real depende del sistema francés y puede variar ligeramente
            total_esperado_simple = P * (Decimal('1') + tea_decimal)
            porcentaje_interes_real = ((total_cuotas / P) - Decimal('1')) * Decimal('100')
            
            logger.info(
                f"Cronograma generado: {N} cuotas de 30 días\n"
                f"TEA Nominal: {tea_porcentaje}% | TEM Efectiva: {(tem * 100).quantize(Decimal('0.0001'))}%\n"
                f"Cuota Regular: S/ {cuota_regular}\n"
                f"Capital Prestado: S/ {P}\n"
                f"Total Intereses: S/ {total_interes} ({porcentaje_interes_real.quantize(Decimal('0.01'))}% efectivo)\n"
                f"Total a Pagar: S/ {total_cuotas}\n"
                f"Nota: TEA {tea_porcentaje}% aplicada mensualmente genera {porcentaje_interes_real.quantize(Decimal('0.01'))}% de interés total"
            )
            
            return cronograma
            
        except Exception as e:
            logger.error(f"Error generando cronograma: {e}")
            return []
    
    @staticmethod
    def validar_monto_maximo_pep(es_pep, monto):
        """
        Valida que el monto no exceda 1 UIT para clientes PEP.
        
        Args:
            es_pep: Boolean indicando si el cliente es PEP
            monto: Monto del préstamo
            
        Returns:
            tuple: (es_valido: bool, mensaje: str)
        """
        try:
            monto_decimal = Decimal(str(monto))
            
            if es_pep and monto_decimal > FinancialService.UIT_VALOR:
                return (
                    False, 
                    f"Clientes PEP no pueden solicitar más de 1 UIT (S/ {FinancialService.UIT_VALOR})"
                )
            
            return (True, "")
            
        except Exception as e:
            logger.error(f"Error validando monto PEP: {e}")
            return (False, "Error al validar monto")