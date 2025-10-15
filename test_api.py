"""
Script para probar la API de clientes y verificar la BD
"""
from app import create_app, db
from app.clients.model.clients import Cliente

app = create_app()

with app.app_context():
    # Verificar cuántos clientes hay
    total_clientes = Cliente.query.count()
    print(f"\n📊 Total de clientes en BD: {total_clientes}")
    
    if total_clientes > 0:
        print("\n👥 Clientes registrados:")
        clientes = Cliente.query.limit(10).all()
        for cliente in clientes:
            print(f"  - DNI: {cliente.dni} | Nombre: {cliente.nombre_completo} {cliente.apellido_paterno}")
    else:
        print("\n⚠️  No hay clientes en la base de datos")
        print("\n💡 Para registrar un cliente, necesitas:")
        print("   1. Tener configurada la variable API_KEY de Factiliza")
        print("   2. Usar un DNI válido de Perú (8 dígitos)")
        print("   3. Hacer una petición POST a /api/v1/clientes con el DNI")
        
        print("\n🔍 Ejemplo de DNI válidos para probar:")
        print("   - 12345678 (si está en RENIEC)")
        print("   - Cualquier DNI real de 8 dígitos")
