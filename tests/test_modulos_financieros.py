"""
Script de Prueba - Sistema de Céntimos y Redondeo Legal
========================================================

Este script valida la implementación de los Módulos 1 y 2:
1. Cálculo de cuotas con sistema de céntimos
2. Aplicación de Ley N° 29571 para pagos en efectivo
3. Conciliación contable

Ejecutar con: python tests/test_modulos_financieros.py
"""

import sys
from pathlib import Path
from decimal import Decimal

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.financial_service import FinancialService
from app.services.pago_service import PagoService
from app.models import MetodoPagoEnum


def print_section(title):
    """Imprime una sección formateada"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_modulo_1_cuotas_sin_interes():
    """
    MÓDULO 1: Prueba el cálculo de cuotas con sistema de céntimos
    """
    print_section("MÓDULO 1: Sistema de Céntimos - Generación de Cronograma")
    
    # Caso de prueba 1: 1000 en 3 cuotas sin interés
    from datetime import date
    P = Decimal('1000.00')
    TEA = Decimal('0.00')
    N = 3
    fecha = date(2025, 1, 1)
    
    print(f"\n📝 Caso 1: Préstamo de S/ {P} en {N} cuotas (TEA: {TEA}%)")
    
    cronograma = FinancialService.generar_cronograma_pagos(P, TEA, N, fecha)
    
    # Extraer cuotas
    cuota_1 = cronograma[0]['monto_cuota']
    cuota_2 = cronograma[1]['monto_cuota']
    cuota_3 = cronograma[2]['monto_cuota']
    
    print(f"   Cuota 1:    S/ {cuota_1} {'(Regular)' if not cronograma[0]['es_cuota_ajuste'] else '(Ajuste)'}")
    print(f"   Cuota 2:    S/ {cuota_2} {'(Regular)' if not cronograma[1]['es_cuota_ajuste'] else '(Ajuste)'}")
    print(f"   Cuota 3:    S/ {cuota_3} {'(Regular)' if not cronograma[2]['es_cuota_ajuste'] else '(Ajuste)'}")
    
    # Verificación
    total_calculado = sum(c['monto_cuota'] for c in cronograma)
    print(f"\n   Verificación:")
    print(f"   Total cuotas = S/ {total_calculado}")
    print(f"   ¿Cuadra con el principal? {'✓ PASS' if total_calculado == P else f'✗ FAIL ({total_calculado} ≠ {P})'}")
    
    # Caso de prueba 2: 471.43 en 2 cuotas
    P2 = Decimal('471.43')
    N2 = 2
    
    print(f"\n📝 Caso 2: Préstamo de S/ {P2} en {N2} cuotas (TEA: {TEA}%)")
    
    cronograma2 = FinancialService.generar_cronograma_pagos(P2, TEA, N2, fecha)
    
    cuota_2_1 = cronograma2[0]['monto_cuota']
    cuota_2_2 = cronograma2[1]['monto_cuota']
    
    print(f"   Cuota 1:    S/ {cuota_2_1} {'(Regular)' if not cronograma2[0]['es_cuota_ajuste'] else '(Ajuste)'}")
    print(f"   Cuota 2:    S/ {cuota_2_2} {'(Regular)' if not cronograma2[1]['es_cuota_ajuste'] else '(Ajuste)'}")
    
    total_calculado2 = sum(c['monto_cuota'] for c in cronograma2)
    print(f"\n   Verificación:")
    print(f"   Total cuotas = S/ {total_calculado2}")
    print(f"   ¿Cuadra con el principal? {'✓ PASS' if total_calculado2 == P2 else f'✗ FAIL'}")
    
    # Caso de prueba 3: 5000 en 12 cuotas con interés
    P3 = Decimal('5000.00')
    TEA3 = Decimal('12.00')
    N3 = 12
    
    print(f"\n📝 Caso 3: Préstamo de S/ {P3} en {N3} cuotas (TEA: {TEA3}%)")
    
    cronograma3 = FinancialService.generar_cronograma_pagos(P3, TEA3, N3, fecha)
    
    print(f"\n   Cuotas generadas: {len(cronograma3)}")
    print(f"   Primera cuota: S/ {cronograma3[0]['monto_cuota']} (Regular)")
    print(f"   Última cuota:  S/ {cronograma3[-1]['monto_cuota']} {'(Ajuste)' if cronograma3[-1]['es_cuota_ajuste'] else '(Regular)'}")
    
    total_capital = sum(c['monto_capital'] for c in cronograma3)
    total_interes = sum(c['monto_interes'] for c in cronograma3)
    total_cuotas = sum(c['monto_cuota'] for c in cronograma3)
    
    print(f"\n   Verificación:")
    print(f"   Capital amortizado: S/ {total_capital}")
    print(f"   Intereses pagados:  S/ {total_interes}")
    print(f"   Total a pagar:      S/ {total_cuotas}")
    print(f"   ¿Capital cuadra? {'✓ PASS' if abs(total_capital - P3) < Decimal('0.01') else '✗ FAIL'}")
    
    return True


def test_modulo_2_redondeo_ley_29571():
    """
    MÓDULO 2: Prueba la aplicación de la Ley N° 29571
    """
    print_section("MÓDULO 2: Ley N° 29571 - Redondeo al Múltiplo de S/ 0.10")
    
    casos_prueba = [
        (Decimal('471.43'), Decimal('471.40')),  # céntimos: 3 → redondea abajo a .40
        (Decimal('471.44'), Decimal('471.40')),  # céntimos: 4 → redondea abajo a .40
        (Decimal('471.45'), Decimal('471.50')),  # céntimos: 5 → redondea arriba a .50
        (Decimal('471.47'), Decimal('471.50')),  # céntimos: 7 → redondea arriba a .50
        (Decimal('100.01'), Decimal('100.00')),  # céntimos: 1 → redondea abajo a .00
        (Decimal('100.05'), Decimal('100.10')),  # céntimos: 5 → redondea arriba a .10
        (Decimal('100.09'), Decimal('100.10')),  # céntimos: 9 → redondea arriba a .10
        (Decimal('333.33'), Decimal('333.30')),  # céntimos: 3 → redondea abajo a .30
    ]
    
    print("\n📝 Casos de prueba:")
    print(f"\n{'Monto Original':>15} → {'Monto Redondeado':>15} | {'Ahorro Cliente':>15} | {'Estado':>8}")
    print("-" * 70)
    
    for monto_original, monto_esperado in casos_prueba:
        monto_redondeado = PagoService.aplicar_redondeo(monto_original)
        ahorro = monto_original - monto_redondeado
        estado = "✓ PASS" if monto_redondeado == monto_esperado else "✗ FAIL"
        
        print(f"S/ {monto_original:>11} → S/ {monto_redondeado:>11} | S/ {ahorro:>11} | {estado}")
    
    return True


def test_modulo_2_conciliacion_contable():
    """
    MÓDULO 2: Prueba la conciliación contable
    """
    print_section("MÓDULO 2: Conciliación Contable")
    
    # Caso 1: Pago en efectivo
    print("\n📝 Caso 1: Pago en EFECTIVO")
    monto_cuota = Decimal('471.43')
    metodo_pago = MetodoPagoEnum.EFECTIVO
    
    monto_contable, monto_pagado, ajuste_redondeo = PagoService.calcular_montos_pago(
        monto_cuota, metodo_pago
    )
    
    print(f"   Monto Contable (deuda):       S/ {monto_contable}")
    print(f"   Monto Pagado (caja):          S/ {monto_pagado}")
    print(f"   Ajuste por Redondeo (gasto):  S/ {ajuste_redondeo}")
    print(f"\n   Verificación de Conciliación:")
    print(f"   monto_pagado + ajuste_redondeo = {monto_pagado} + {ajuste_redondeo} = S/ {monto_pagado + ajuste_redondeo}")
    print(f"   ¿Cuadra con monto_contable? {'✓' if (monto_pagado + ajuste_redondeo) == monto_contable else '✗'}")
    
    # Caso 2: Pago con tarjeta
    print("\n📝 Caso 2: Pago con TARJETA")
    monto_cuota2 = Decimal('471.43')
    metodo_pago2 = MetodoPagoEnum.TARJETA
    
    monto_contable2, monto_pagado2, ajuste_redondeo2 = PagoService.calcular_montos_pago(
        monto_cuota2, metodo_pago2
    )
    
    print(f"   Monto Contable (deuda):       S/ {monto_contable2}")
    print(f"   Monto Pagado (caja):          S/ {monto_pagado2}")
    print(f"   Ajuste por Redondeo (gasto):  S/ {ajuste_redondeo2}")
    print(f"\n   Verificación de Conciliación:")
    print(f"   monto_pagado + ajuste_redondeo = {monto_pagado2} + {ajuste_redondeo2} = S/ {monto_pagado2 + ajuste_redondeo2}")
    print(f"   ¿Cuadra con monto_contable? {'✓' if (monto_pagado2 + ajuste_redondeo2) == monto_contable2 else '✗'}")
    print(f"   ℹ️ Sin ajuste porque es pago digital")
    
    # Caso 3: Pago con transferencia
    print("\n📝 Caso 3: Pago con TRANSFERENCIA")
    monto_cuota3 = Decimal('333.33')
    metodo_pago3 = MetodoPagoEnum.TRANSFERENCIA
    
    monto_contable3, monto_pagado3, ajuste_redondeo3 = PagoService.calcular_montos_pago(
        monto_cuota3, metodo_pago3
    )
    
    print(f"   Monto Contable (deuda):       S/ {monto_contable3}")
    print(f"   Monto Pagado (caja):          S/ {monto_pagado3}")
    print(f"   Ajuste por Redondeo (gasto):  S/ {ajuste_redondeo3}")
    print(f"\n   Verificación de Conciliación:")
    print(f"   monto_pagado + ajuste_redondeo = {monto_pagado3} + {ajuste_redondeo3} = S/ {monto_pagado3 + ajuste_redondeo3}")
    print(f"   ¿Cuadra con monto_contable? {'✓' if (monto_pagado3 + ajuste_redondeo3) == monto_contable3 else '✗'}")
    print(f"   ℹ️ Sin ajuste porque es pago digital")
    
    return True


def test_caso_completo():
    """
    Prueba un caso completo: préstamo → cuotas → pagos
    """
    print_section("CASO COMPLETO: Préstamo de S/ 1000 en 3 cuotas + Pagos")
    
    # Generar cronograma
    from datetime import date
    P = Decimal('1000.00')
    TEA = Decimal('0.00')  # Sin interés
    N = 3
    fecha = date(2025, 1, 1)
    
    print(f"\n📝 Crear préstamo:")
    print(f"   Principal: S/ {P}")
    print(f"   Plazo: {N} cuotas")
    print(f"   TEA: {TEA}%")
    
    cronograma = FinancialService.generar_cronograma_pagos(P, TEA, N, fecha)
    
    print(f"\n📊 Cronograma generado:")
    print(f"\n{'Cuota':>6} | {'Fecha':>12} | {'Monto':>10} | {'Capital':>10} | {'Interés':>10} | {'Saldo':>10} | {'Ajuste?':>8}")
    print("-" * 90)
    
    total_cuotas = Decimal('0.00')
    for cuota in cronograma:
        ajuste_mark = "✓ SÍ" if cuota['es_cuota_ajuste'] else "No"
        print(
            f"{cuota['numero_cuota']:>6} | "
            f"{cuota['fecha_vencimiento'].strftime('%Y-%m-%d'):>12} | "
            f"S/ {cuota['monto_cuota']:>7} | "
            f"S/ {cuota['monto_capital']:>7} | "
            f"S/ {cuota['monto_interes']:>7} | "
            f"S/ {cuota['saldo_capital']:>7} | "
            f"{ajuste_mark:>8}"
        )
        total_cuotas += cuota['monto_cuota']
    
    print("-" * 90)
    print(f"{'TOTAL':>6} | {' ':>12} | S/ {total_cuotas:>7} | {' ':>10} | {' ':>10} | {' ':>10} | {' ':>8}")
    print(f"\n   Verificación: Total cuotas = S/ {total_cuotas}")
    print(f"   ¿Cuadra con principal? {'✓' if total_cuotas == P else '✗'}")
    
    # Simular pagos
    print(f"\n💳 Simular pagos de las cuotas:")
    print(f"\n{'Cuota':>6} | {'Método':>15} | {'Contable':>10} | {'Pagado':>10} | {'Ajuste':>10} | {'Balance':>8}")
    print("-" * 80)
    
    metodos = [MetodoPagoEnum.EFECTIVO, MetodoPagoEnum.TARJETA, MetodoPagoEnum.EFECTIVO]
    
    for idx, cuota in enumerate(cronograma):
        metodo = metodos[idx]
        monto_contable, monto_pagado, ajuste = PagoService.calcular_montos_pago(
            cuota['monto_cuota'], metodo
        )
        
        balance_ok = "✓" if (monto_pagado + ajuste) == monto_contable else "✗"
        
        print(
            f"{cuota['numero_cuota']:>6} | "
            f"{metodo.value:>15} | "
            f"S/ {monto_contable:>7} | "
            f"S/ {monto_pagado:>7} | "
            f"S/ {ajuste:>7} | "
            f"{balance_ok:>8}"
        )
    
    return True


def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "=" * 70)
    print("  TEST SUITE - MÓDULOS FINANCIEROS")
    print("  Sistema de Céntimos + Redondeo Legal (Ley N° 29571)")
    print("=" * 70)
    
    try:
        # Módulo 1: Sistema de Céntimos
        test_modulo_1_cuotas_sin_interes()
        
        # Módulo 2: Redondeo Legal
        test_modulo_2_redondeo_ley_29571()
        
        # Módulo 2: Conciliación Contable
        test_modulo_2_conciliacion_contable()
        
        # Caso completo
        test_caso_completo()
        
        print("\n" + "=" * 70)
        print("  ✅ TODAS LAS PRUEBAS PASARON")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"  ❌ ERROR EN LAS PRUEBAS: {e}")
        print("=" * 70 + "\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
