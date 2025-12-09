"""
Test de Integración - Registro Completo de Pagos
=================================================

Prueba el flujo completo:
1. Crear cliente
2. Crear préstamo con cronograma
3. Registrar pagos con diferentes métodos
4. Verificar conciliación contable en BD

Ejecutar con: 
    python tests/test_pago_completo.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
from datetime import date
from app import create_app
from app.common.extensions import db
from app.models import Cliente, Prestamo, Cuota, Pago, MetodoPagoEnum
from app.services.prestamo_service import PrestamoService
from app.services.pago_service import PagoService


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_flujo_completo():
    """Prueba el flujo completo de préstamo y pagos"""
    
    # Crear aplicación y contexto
    app = create_app()
    
    with app.app_context():
        print_header("TEST DE INTEGRACIÓN: FLUJO COMPLETO DE PRÉSTAMO Y PAGOS")
        
        # Limpiar datos de prueba previos
        print("\n🧹 Limpiando datos de prueba previos...")
        db.session.query(Pago).filter(Pago.pago_id > 0).delete()
        db.session.query(Cuota).filter(Cuota.cuota_id > 0).delete()
        db.session.query(Prestamo).filter(Prestamo.prestamo_id > 0).delete()
        db.session.query(Cliente).filter(Cliente.dni == '12345678').delete()
        db.session.commit()
        print("   ✓ Datos limpiados")
        
        # PASO 1: Crear préstamo
        print_header("PASO 1: CREAR PRÉSTAMO")
        
        dni = 'xxxxxxxx'
        correo = 'example@gmail.com'
        monto = Decimal('10000.00')
        tea = Decimal('0.00')  # Sin interés para prueba simple, si se prueba con tea fallara 1. Total contable = Monto préstamo: ✗ FAIL es normal pues tiene tea
        plazo = 3
        fecha_otorgamiento = date.today()
        
        print(f"\n📝 Datos del préstamo:")
        print(f"   DNI Cliente: {dni}")
        print(f"   Correo: {correo}")
        print(f"   Monto: S/ {monto}")
        print(f"   TEA: {tea}%")
        print(f"   Plazo: {plazo} meses")
        print(f"   Fecha: {fecha_otorgamiento}")
        
        respuesta, error, status = PrestamoService.registrar_prestamo_completo(
            dni=dni,
            correo_electronico=correo,
            monto_total=monto,
            interes_tea=tea,
            plazo=plazo,
            f_otorgamiento=fecha_otorgamiento
        )
        
        if error:
            print(f"\n   ❌ ERROR: {error}")
            return False
        
        print(f"\n   ✓ Préstamo creado exitosamente")
        print(f"   ID Préstamo: {respuesta['prestamo']['prestamo_id']}")
        print(f"   ID Cliente: {respuesta['cliente']['cliente_id']}")
        
        prestamo_id = respuesta['prestamo']['prestamo_id']
        
        # Mostrar cronograma
        print(f"\n📊 Cronograma de Cuotas:")
        print(f"\n{'#':>3} | {'Fecha Venc.':>12} | {'Monto':>10} | {'Capital':>10} | {'Interés':>10} | {'Saldo':>10} | {'Ajuste?':>8}")
        print("-" * 85)
        
        for cuota in respuesta['cronograma']:
            ajuste = "✓ SÍ" if cuota.get('es_cuota_ajuste', False) else "No"
            print(
                f"{cuota['numero_cuota']:>3} | "
                f"{cuota['fecha_vencimiento']:>12} | "
                f"S/ {cuota['monto_cuota']:>7.2f} | "
                f"S/ {cuota['monto_capital']:>7.2f} | "
                f"S/ {cuota['monto_interes']:>7.2f} | "
                f"S/ {cuota['saldo_capital']:>7.2f} | "
                f"{ajuste:>8}"
            )
        
        # PASO 2: Obtener cuotas de la BD
        print_header("PASO 2: VERIFICAR CUOTAS EN BD")
        
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota).all()
        
        print(f"\n✓ Se encontraron {len(cuotas)} cuotas en la BD")
        
        for cuota in cuotas:
            ajuste_text = " (CUOTA DE AJUSTE)" if cuota.es_cuota_ajuste else ""
            print(f"   Cuota #{cuota.numero_cuota}: S/ {cuota.monto_cuota}{ajuste_text}")
        
        # PASO 3: Registrar pagos con diferentes métodos
        print_header("PASO 3: REGISTRAR PAGOS")
        
        metodos_pago = [
            MetodoPagoEnum.EFECTIVO,
            MetodoPagoEnum.TARJETA,
            MetodoPagoEnum.EFECTIVO
        ]
        
        print(f"\n{'Cuota':>5} | {'Método':>15} | {'Monto Cuota':>12} | {'Monto Pagado':>13} | {'Ajuste':>10} | {'Estado':>8}")
        print("-" * 85)
        
        pagos_registrados = []
        
        for idx, cuota in enumerate(cuotas):
            metodo = metodos_pago[idx]
            
            # Registrar el pago
            respuesta_pago, error_pago, status_pago = PagoService.registrar_pago_cuota(
                prestamo_id=prestamo_id,
                cuota_id=cuota.cuota_id,
                metodo_pago=metodo,
                fecha_pago=date.today(),
                comprobante_referencia=f"COMP-{cuota.numero_cuota:03d}",
                observaciones=f"Pago de prueba cuota {cuota.numero_cuota}"
            )
            
            if error_pago:
                print(f"   {cuota.numero_cuota:>5} | {metodo.value:>15} | ❌ ERROR: {error_pago}")
                continue
            
            # Extraer información del pago
            conciliacion = respuesta_pago['conciliacion']
            monto_contable = conciliacion['monto_contable']
            monto_pagado = conciliacion['monto_recibido_caja']
            ajuste = conciliacion['ajuste_redondeo']
            
            # Verificar conciliación
            suma_verif = monto_pagado + ajuste
            estado = "✓ OK" if abs(suma_verif - monto_contable) < 0.01 else "✗ ERROR"
            
            print(
                f"{cuota.numero_cuota:>5} | "
                f"{metodo.value:>15} | "
                f"S/ {monto_contable:>9.2f} | "
                f"S/ {monto_pagado:>10.2f} | "
                f"S/ {ajuste:>7.2f} | "
                f"{estado:>8}"
            )
            
            pagos_registrados.append(respuesta_pago['pago'])
        
        # PASO 4: Verificar pagos en BD
        print_header("PASO 4: VERIFICAR PAGOS EN BASE DE DATOS")
        
        pagos_bd = Pago.query.join(Cuota).filter(Cuota.prestamo_id == prestamo_id).all()
        
        print(f"\n✓ Se encontraron {len(pagos_bd)} pagos registrados")
        print(f"\n{'ID Pago':>8} | {'Cuota':>5} | {'Método':>15} | {'Contable':>10} | {'Pagado':>10} | {'Ajuste':>10} | {'OK?':>5}")
        print("-" * 85)
        
        total_contable = Decimal('0.00')
        total_pagado = Decimal('0.00')
        total_ajuste = Decimal('0.00')
        
        for pago in pagos_bd:
            # Verificar invariante: monto_pagado + ajuste_redondeo = monto_contable
            suma = pago.monto_pagado + pago.ajuste_redondeo
            diferencia = abs(suma - pago.monto_contable)
            ok = "✓" if diferencia < Decimal('0.01') else "✗"
            
            print(
                f"{pago.pago_id:>8} | "
                f"{pago.cuota.numero_cuota:>5} | "
                f"{pago.metodo_pago.value:>15} | "
                f"S/ {pago.monto_contable:>7.2f} | "
                f"S/ {pago.monto_pagado:>7.2f} | "
                f"S/ {pago.ajuste_redondeo:>7.2f} | "
                f"{ok:>5}"
            )
            
            total_contable += pago.monto_contable
            total_pagado += pago.monto_pagado
            total_ajuste += pago.ajuste_redondeo
        
        print("-" * 85)
        print(
            f"{'TOTAL':>8} | {' ':>5} | {' ':>15} | "
            f"S/ {total_contable:>7.2f} | "
            f"S/ {total_pagado:>7.2f} | "
            f"S/ {total_ajuste:>7.2f} | "
        )
        
        # PASO 5: Verificar estado de cuotas
        print_header("PASO 5: VERIFICAR ESTADO DE CUOTAS")
        
        cuotas_actualizadas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota).all()
        
        print(f"\n{'Cuota':>5} | {'Monto Cuota':>12} | {'Monto Pagado':>13} | {'Fecha Pago':>12} | {'Estado':>10}")
        print("-" * 70)
        
        for cuota in cuotas_actualizadas:
            estado_pago = "PAGADA ✓" if cuota.monto_pagado and cuota.monto_pagado > 0 else "PENDIENTE"
            fecha_pago_str = cuota.fecha_pago.strftime('%Y-%m-%d') if cuota.fecha_pago else "N/A"
            monto_pagado_str = f"S/ {cuota.monto_pagado:>7.2f}" if cuota.monto_pagado else "S/ 0.00"
            
            print(
                f"{cuota.numero_cuota:>5} | "
                f"S/ {cuota.monto_cuota:>9.2f} | "
                f"{monto_pagado_str:>13} | "
                f"{fecha_pago_str:>12} | "
                f"{estado_pago:>10}"
            )
        
        # PASO 6: Resumen final y verificaciones
        print_header("PASO 6: RESUMEN Y VERIFICACIONES FINALES")
        
        print(f"\n📊 Resumen Financiero:")
        print(f"   Monto del Préstamo:        S/ {monto:>9.2f}")
        print(f"   Total Contable (cuotas):   S/ {total_contable:>9.2f}")
        print(f"   Total Pagado (caja):       S/ {total_pagado:>9.2f}")
        print(f"   Total Ajustes:             S/ {total_ajuste:>9.2f}")
        
        print(f"\n✅ Verificaciones:")
        
        # Verificación 1: Total contable = Monto préstamo
        verif1 = abs(total_contable - monto) < Decimal('0.01')
        print(f"   1. Total contable = Monto préstamo: {'✓ PASS' if verif1 else '✗ FAIL'}")
        
        # Verificación 2: Total pagado + ajustes = Total contable
        suma_total = total_pagado + total_ajuste
        verif2 = abs(suma_total - total_contable) < Decimal('0.01')
        print(f"   2. Pagado + Ajustes = Contable: {'✓ PASS' if verif2 else '✗ FAIL'}")
        print(f"      ({total_pagado} + {total_ajuste} = {suma_total})")
        
        # Verificación 3: Todas las cuotas están pagadas
        verif3 = all(c.monto_pagado and c.monto_pagado > 0 for c in cuotas_actualizadas)
        print(f"   3. Todas las cuotas pagadas: {'✓ PASS' if verif3 else '✗ FAIL'}")
        
        # Verificación 4: Todos los pagos tienen conciliación correcta
        verif4 = all(abs((p.monto_pagado + p.ajuste_redondeo) - p.monto_contable) < Decimal('0.01') for p in pagos_bd)
        print(f"   4. Conciliación correcta en todos los pagos: {'✓ PASS' if verif4 else '✗ FAIL'}")
        
        # Resultado final
        todas_ok = verif1 and verif2 and verif3 and verif4
        
        if todas_ok:
            print_header("✅ PRUEBA EXITOSA - TODAS LAS VERIFICACIONES PASARON")
            return True
        else:
            print_header("❌ PRUEBA FALLIDA - REVISAR VERIFICACIONES")
            return False


if __name__ == "__main__":
    try:
        resultado = test_flujo_completo()
        sys.exit(0 if resultado else 1)
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)