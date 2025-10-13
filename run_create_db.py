# run_create_db.py
#Este de acá si quieren eliminenlo, lo usé para probar que se creaban las tablas bien, se supone que debería bastar con el comando flask db-create

from app import create_app, db

print("--> Iniciando el script de creación de BD...")

try:
    app = create_app()
    with app.app_context():
        print("--> Contexto de la aplicación creado. Intentando crear tablas...")
        db.create_all()
        print("\n✅ ¡ÉXITO! Las tablas fueron creadas en la base de datos.")

except Exception as e:
    print("\n❌ ERROR: Ocurrió un problema al intentar inicializar la aplicación o crear las tablas.")
    print("La causa del error es:")
    # Imprimimos el error completo para poder diagnosticarlo.
    import traceback
    traceback.print_exc()