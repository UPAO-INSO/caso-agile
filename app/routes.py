from flask import Blueprint, render_template, request, redirect, url_for
from flask_mail import Message
from app import mail
from app.utils import generar_pdf

main = Blueprint('main', __name__)

@main.route('/') 
def home(): 
    return render_template('index.html', title='Inicio') 

@main.route('/enviar_prueba_correo')
def enviar_prueba_correo():
    destinatario = "valeriatbw@gmail.com"
    nombre_cliente = "Valeria"

    try:
        msg = Message(
            subject="Tu resumen de solicitud",
            recipients=[destinatario]
        )

        # Cuerpo en texto plano (por compatibilidad)
        msg.body = f"Hola {nombre_cliente}, te enviamos tu resumen en PDF."

        # Cuerpo HTML (desde plantilla)
        msg.html = render_template("emails/email_cliente.html", nombre=nombre_cliente)

        # Generar y adjuntar PDF
        pdf_buffer = generar_pdf(nombre_cliente)
        msg.attach(
            "resumen.pdf",             # nombre del archivo
            "application/pdf",          # tipo MIME
            pdf_buffer.read()           # contenido binario
        )

        # Enviar correo
        mail.send(msg)
        print(f"Correo enviado correctamente a {destinatario}")

    except Exception as e:
        print(f"Error al enviar el correo: {e}")

    return redirect(url_for('main.home'))