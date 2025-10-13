# app.py (en la raíz del proyecto)

from app import create_app, db

# Creamos la instancia de la aplicación usando nuestra fábrica
app = create_app()

@app.cli.command("db-create")
def create_database():
    """
    Lee los modelos de models.py y crea todas las tablas en la BD.
    """
    # Usamos el contexto de la aplicación para que SQLAlchemy sepa a qué BD conectarse
    with app.app_context():
        try:
            db.create_all()
            print("¡Base de datos y tablas creadas exitosamente!")
        except Exception as e:
            print(f" Error al crear la base de datos: {e}")

# Código para iniciar el servidor de desarrollo
if __name__ == '__main__':
    app.run(debug=True)