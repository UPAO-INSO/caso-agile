"""
Script para insertar clientes de prueba en la base de datos
"""
from app import create_app, db
from app.clients.model.clients import Cliente

app = create_app()

with app.app_context():
    print("\n🔧 Insertando clientes de prueba...\n")
    
    # Clientes de prueba
    clientes_prueba = [
        Cliente(
            dni="12345678",
            nombre_completo="Juan Carlos",
            apellido_paterno="Pérez",
            apellido_materno="García",
            pep=False
        ),
        Cliente(
            dni="87654321",
            nombre_completo="María Elena",
            apellido_paterno="Torres",
            apellido_materno="Rojas",
            pep=True
        ),
        Cliente(
            dni="11223344",
            nombre_completo="Pedro Pablo",
            apellido_paterno="Kucinski",
            apellido_materno="López",
            pep=False
        ),
        Cliente(
            dni="44332211",
            nombre_completo="Ana Sofía",
            apellido_paterno="Ramírez",
            apellido_materno="Mendoza",
            pep=False
        ),
        Cliente(
            dni="55667788",
            nombre_completo="Carlos Alberto",
            apellido_paterno="Sánchez",
            apellido_materno="Vargas",
            pep=True
        )
    ]
    
    insertados = 0
    existentes = 0
    
    for cliente in clientes_prueba:
        # Verificar si ya existe
        existe = Cliente.query.filter_by(dni=cliente.dni).first()
        if not existe:
            db.session.add(cliente)
            print(f"✅ Cliente agregado: DNI {cliente.dni} - {cliente.nombre_completo} {cliente.apellido_paterno}")
            insertados += 1
        else:
            print(f"⚠️  Ya existe: DNI {cliente.dni}")
            existentes += 1
    
    db.session.commit()
    
    print(f"\n📊 Resumen:")
    print(f"  ✅ Insertados: {insertados}")
    print(f"  ⚠️  Ya existían: {existentes}")
    
    # Listar todos los clientes
    todos = Cliente.query.all()
    print(f"\n👥 Total de clientes en la BD: {len(todos)}")
    print("\n📋 Lista completa:")
    for c in todos:
        pep_status = "🔴 PEP" if c.pep else "🟢 Normal"
        print(f"  {pep_status} | DNI: {c.dni} | {c.nombre_completo} {c.apellido_paterno} {c.apellido_materno}")
    
    print("\n✨ ¡Listo! Ahora puedes buscar estos DNIs en el frontend:")
    print("   - 12345678")
    print("   - 87654321 (PEP)")
    print("   - 11223344")
    print("   - 44332211")
    print("   - 55667788 (PEP)")
