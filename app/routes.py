from flask import Blueprint, render_template, redirect, url_for
from flask_mail import Message
from app import mail
from app.utils import generar_cronograma_pdf

main = Blueprint('main', __name__)

@main.route('/') 
def home(): 
    return render_template('index.html', title='Inicio') 

@main.route('/enviar_cronograma')
def enviar_cronograma():
    destinatario = "valeriatbw@gmail.com"
    nombre_cliente = "Valeria Brunelli"
    monto = 1500.00
    cuotas = 6
    tasa_interes = 5.0

    try:
        msg = Message(
            subject="Tu Cronograma de Pagos - Gota a Gota",
            recipients=[destinatario]
        )

        msg.body = f"Hola {nombre_cliente}, te enviamos tu cronograma de pagos en formato PDF."

        # Renderizar plantilla HTML
        msg.html = render_template(
            "emails/email_cronograma.html",
            nombre=nombre_cliente
        )

        # Generar PDF adjunto
        pdf_buffer = generar_cronograma_pdf(nombre_cliente, monto, cuotas, tasa_interes)
        msg.attach("cronograma.pdf", "application/pdf", pdf_buffer.read())

        mail.send(msg)
        print(f"Correo enviado correctamente a {destinatario}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

    return redirect(url_for('main.home'))