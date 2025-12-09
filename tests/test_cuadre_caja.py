"""
Test básico del módulo de cuadre de caja.
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date, datetime
from app import create_app
from app.common.extensions import db
from app.services.caja_service import CajaService

def test_cuadre_caja():
# → Se crea la aplicación en modo testing
    app = create_app('testing')
    
    with app.app_context():
        # Crear todas las tablas en la base de datos de testing
        db.create_all()
        
        print("\n" + "="*80)
        print("TEST: Cuadre de Caja")
        print("="*80)
        
        # 1. Resumen del día actual
        print("\n1. RESUMEN DEL DÍA ACTUAL")
        print("-" * 80)
        hoy = date.today()
        resumen_hoy = CajaService.obtener_resumen_diario(hoy)
        
        print(f"\nFecha: {resumen_hoy['fecha']}")
        print(f"\nDetalle por medio de pago:")
        for medio in resumen_hoy['detalle_por_medio']:
            print(f"  - {medio['medio_pago'].upper()}:")
            print(f"    · Cantidad de pagos: {medio['cantidad_pagos']}")
            print(f"    · Total: S/. {medio['total']:.2f}")
            print(f"    · Mora cobrada: S/. {medio['total_mora']:.2f}")
            print(f"    · Capital cobrado: S/. {medio['total_capital']:.2f}")
        
        print(f"\nRESUMEN TOTAL:")
        resumen = resumen_hoy['resumen']
        print(f"  - Total de pagos: {resumen['cantidad_total_pagos']}")
        print(f"  - Total recaudado: S/. {resumen['total_recaudado']:.2f}")
        print(f"  - Mora cobrada: S/. {resumen['total_mora_cobrada']:.2f}")
        print(f"  - Capital cobrado: S/. {resumen['total_capital_cobrado']:.2f}")
        
        # 2. Detalle de pagos del día
        print("\n\n2. DETALLE DE PAGOS DEL DÍA")
        print("-" * 80)
        detalle = CajaService.obtener_detalle_pagos_dia(hoy)
        
        if detalle:
            for pago in detalle:
                print(f"\n  Pago #{pago['pago_id']} - {pago['hora']}")
                print(f"    Cliente: {pago['cliente']['nombre']} (DNI: {pago['cliente']['dni']})")
                print(f"    Préstamo: #{pago['prestamo_id']} - Cuota #{pago['cuota_numero']}")
                print(f"    Medio: {pago['medio_pago'].upper()}")
                print(f"    Monto total: S/. {pago['monto_pagado']:.2f}")
                print(f"      └─ Mora: S/. {pago['monto_mora']:.2f}")
                print(f"      └─ Capital: S/. {pago['monto_capital']:.2f}")
                if pago['comprobante']:
                    print(f"    Comprobante: {pago['comprobante']}")
                if pago['observaciones']:
                    print(f"    Observaciones: {pago['observaciones']}")
        else:
            print("\n  No hay pagos registrados para esta fecha.")
        
        # 3. Estadísticas generales
        print("\n\n3. ESTADÍSTICAS GENERALES (Últimos 30 días)")
        print("-" * 80)
        estadisticas = CajaService.obtener_estadisticas_caja()
        
        print(f"\nPeriodo analizado: {estadisticas['periodo_analisis']}")
        print(f"Total recaudado: S/. {estadisticas['total_recaudado_30d']:.2f}")
        print(f"Días con movimiento: {estadisticas['dias_con_movimiento']}")
        print(f"Promedio diario: S/. {estadisticas['promedio_diario']:.2f}")
        print(f"\nMedio de pago más usado: {estadisticas['medio_pago_mas_usado']}")
        print(f"Cantidad de veces: {estadisticas['veces_usado']}")
        
        print("\n" + "="*80)
        print("✅ Test completado exitosamente")
        print("="*80 + "\n")


if __name__ == '__main__':
    test_cuadre_caja()
