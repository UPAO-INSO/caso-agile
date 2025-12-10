"""
Script para simular cuotas vencidas modificando las fechas de vencimiento
Retrocede las fechas de vencimiento de las primeras cuotas para que aparezcan como vencidas
"""
from datetime import datetime, timedelta
from app import create_app
from app.common.extensions import db
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

# ==================== CONFIGURACIÓN ====================
PRESTAMO_ID = 2  # ← CAMBIA ESTE ID AL PRÉSTAMO QUE QUIERES SIMULAR
NUM_CUOTAS_VENCIDAS = 10  # Número de cuotas que quieres que estén vencidas
DIAS_ATRASADO_POR_CUOTA = 30  # Días de atraso por cada cuota (para generar mora)
# =======================================================

app = create_app()

with app.app_context():
    print("\n" + "="*80)
    print("🕐 SIMULADOR DE CUOTAS VENCIDAS")
    print("="*80 + "\n")
    
    # Verificar que el préstamo existe
    prestamo = Prestamo.query.get(PRESTAMO_ID)
    if not prestamo:
        print(f"❌ Error: No existe el préstamo con ID {PRESTAMO_ID}")
        print("   Primero crea un préstamo y luego ejecuta este script\n")
        exit(1)
    
    print(f"📋 Préstamo seleccionado: #{PRESTAMO_ID}")
    print(f"   Cliente: {prestamo.cliente.nombre_completo}")
    print(f"   Monto: S/ {prestamo.monto_total:,.2f}")
    print()
    
    # Obtener cuotas
    cuotas = Cuota.query.filter_by(prestamo_id=PRESTAMO_ID).order_by(Cuota.numero_cuota).limit(NUM_CUOTAS_VENCIDAS).all()
    
    if not cuotas:
        print(f"❌ Error: El préstamo #{PRESTAMO_ID} no tiene cuotas")
        exit(1)
    
    print(f"📅 Configuración:")
    print(f"   • Cuotas a vencer: {NUM_CUOTAS_VENCIDAS}")
    print(f"   • Días de atraso por cuota: {DIAS_ATRASADO_POR_CUOTA}")
    print(f"   • Fecha actual: {datetime.now().date()}")
    print()
    
    print("Cuotas que se modificarán:")
    for i, cuota in enumerate(cuotas, 1):
        dias_atraso = DIAS_ATRASADO_POR_CUOTA * (NUM_CUOTAS_VENCIDAS - i + 1)
        nueva_fecha = datetime.now().date() - timedelta(days=dias_atraso)
        print(f"   • Cuota {cuota.numero_cuota}: {cuota.fecha_vencimiento} → {nueva_fecha} ({dias_atraso} días atrás)")
    print()
    
    respuesta = input("¿Deseas modificar estas fechas para simular moras? (S/N): ").strip().upper()
    
    if respuesta == 'S':
        try:
            for i, cuota in enumerate(cuotas, 1):
                # Calcular días de atraso: la primera cuota más atrasada
                dias_atraso = DIAS_ATRASADO_POR_CUOTA * (NUM_CUOTAS_VENCIDAS - i + 1)
                nueva_fecha = datetime.now().date() - timedelta(days=dias_atraso)
                
                cuota.fecha_vencimiento = nueva_fecha
                print(f"  ✅ Cuota {cuota.numero_cuota} vencida hace {dias_atraso} días")
            
            db.session.commit()
            
            print(f"\n✅ Fechas modificadas exitosamente")
            print(f"\n📊 Ahora visita el préstamo #{PRESTAMO_ID} en la web para ver:")
            print(f"   • Las cuotas marcadas como 'Vencido'")
            print(f"   • La mora acumulada en rojo (1% por mes de atraso)")
            print(f"   • El monto total pendiente incluyendo mora\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error al modificar fechas: {e}\n")
    else:
        print("\n❌ Operación cancelada - No se modificó ninguna fecha\n")
    
    print("="*80 + "\n")
