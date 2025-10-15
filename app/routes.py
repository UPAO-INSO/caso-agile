from flask import Blueprint, render_template, redirect, url_for, request
from flask_mail import Message
from app import mail
from app.utils import generar_cronograma_pdf  # asegúrate que existe en app/utils.py

main = Blueprint('main', __name__)

# 🏠 Página principal
@main.route('/')
def home():
    return render_template('index.html', title='Inicio')


# 📧 Envío del cronograma por correo (con PDF adjunto)
@main.route('/enviar_cronograma', methods=['POST'])
def enviar_cronograma():
    # Capturamos los datos del formulario
    nombre_cliente = request.form.get('nombre', 'Cliente')
    monto = float(request.form.get('monto', 0))
    cuotas = int(request.form.get('cuotas', 1))
    tasa_interes = 5.0  # Puedes cambiarlo o leerlo del form
    destinatario = "valeriatbw@gmail.com"  # o traerlo de tu modelo Cliente

    try:
        # Crear el mensaje
        msg = Message(
            subject="Tu Cronograma de Pagos - Gota a Gota",
            recipients=[destinatario]
        )

        # Cuerpo del correo
        msg.body = f"Hola {nombre_cliente}, te enviamos tu cronograma de pagos en formato PDF."

        # Renderizar plantilla HTML del correo
        msg.html = render_template(
            "emails/email_cronograma.html",
            nombre=nombre_cliente,
            monto=monto,
            cuotas=cuotas,
            tasa=tasa_interes
        )

        # Generar PDF y adjuntarlo
        pdf_buffer = generar_cronograma_pdf(nombre_cliente, monto, cuotas, tasa_interes)
        msg.attach("cronograma.pdf", "application/pdf", pdf_buffer.read())

        # Enviar correo
        mail.send(msg)
        print(f"✅ Correo enviado correctamente a {destinatario}")

    except Exception as e:
        print(f"❌ Error al enviar el correo: {e}")

    return redirect(url_for('main.home'))


# 🧭 Otras rutas que ya tenías
@main.route('/enviar_prueba_correo')
def enviar_prueba_correo():
    destinatario = "valeriatbw@gmail.com"

    try:
        msg = Message(
            subject='Asunto de Prueba: Envío Exitoso',
            recipients=[destinatario]
        )
        msg.body = "Este es el cuerpo del mensaje en texto plano."
        msg.html = "<h1>Este es el cuerpo en HTML (opcional)</h1><p>Funciona con la configuración de Gmail.</p>"

        mail.send(msg)
        print(f"Correo de prueba enviado con éxito a {destinatario}.")
    except Exception as e:
        print(f"Error de Correo: {e}")

    return redirect(url_for('main.home'))


@main.route('/buscar')
def buscar_cliente():
    return render_template('buscar_cliente.html', title='Buscar Cliente')


@main.route('/test-modal')
def test_modal():
    return render_template('test_modal.html', title='Test Modal')
