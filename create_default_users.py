from app import create_app
from app.common.extensions import db
from app.models.usuario import Usuario

app = create_app()

with app.app_context():
    def create_user_if_not_exists(usuario, password, correo, nombre_completo, rol):
        user = Usuario.query.filter_by(usuario=usuario).first()
        if not user:
            user = Usuario(
                usuario=usuario,
                correo=correo,
                nombre_completo=nombre_completo,
                activo=True,
                rol=rol
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"Usuario '{usuario}' creado.")
        else:
            print(f"Usuario '{usuario}' ya existe.")

    create_user_if_not_exists(
        usuario="admin",
        password="admin123",
        correo="admin@demo.local",
        nombre_completo="Administrador Demo",
        rol="admin"
    )
    create_user_if_not_exists(
        usuario="operador",
        password="operador123",
        correo="operador@demo.local",
        nombre_completo="Operador Demo",
        rol="operador"
    )

print("Usuarios por defecto verificados/creados.")
