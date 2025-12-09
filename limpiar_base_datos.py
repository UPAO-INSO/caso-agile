from app import create_app
from app.common.extensions import db
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.declaracion import DeclaracionJurada
from app.models.cliente import Cliente

app = create_app()

with app.app_context():
    print("\n" + "="*80)
    print("LIMPIEZA COMPLETA DE BASE DE DATOS")
    print("="*80 + "\n")
    
    # Contar registros actuales
    num_pagos = Pago.query.count()
    num_cuotas = Cuota.query.count()
    num_prestamos = Prestamo.query.count()
    num_declaraciones = DeclaracionJurada.query.count()
    num_clientes = Cliente.query.count()
    
    print(f"Registros actuales:")
    print(f"  • Pagos: {num_pagos}")
    print(f"  • Cuotas: {num_cuotas}")
    print(f"  • Préstamos: {num_prestamos}")
    print(f"  • Declaraciones Juradas: {num_declaraciones}")
    print()
    
    respuesta = input("¿Estás SEGURO de que deseas ELIMINAR todos estos registros? (S/N): ").strip().upper()
    
    if respuesta == 'S':
        try:
            # Eliminar en orden (FK constraints)
            print("\n🗑️  Eliminando registros...")
            
            # 1. Eliminar pagos
            Pago.query.delete()
            print(f"  ✅ {num_pagos} pagos eliminados")
            
            # 2. Eliminar cuotas
            Cuota.query.delete()
            print(f"  ✅ {num_cuotas} cuotas eliminadas")
            
            # 3. Eliminar préstamos (antes de declaraciones por FK)
            Prestamo.query.delete()
            print(f"  ✅ {num_prestamos} préstamos eliminados")
            
            # 4. Eliminar declaraciones
            DeclaracionJurada.query.delete()
            print(f"  ✅ {num_declaraciones} declaraciones eliminadas")
            
            Cliente.query.delete()

            # Commit
            db.session.commit()
            
            print("\n✅ Base de datos limpiada exitosamente")
            print("   Ahora puedes crear nuevos préstamos desde cero\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error al limpiar la base de datos: {e}\n")
    else:
        print("\n❌ Operación cancelada - No se eliminó ningún registro\n")
    
    print("="*80 + "\n")
