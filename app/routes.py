from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_mail import Message
from app import mail
from app.utils import generar_cronograma_pdf

main = Blueprint('main', __name__)

@main.route('/') 
def home(): 
    return render_template('index.html', title='Inicio') 

@main.route('/enviar_cronograma', methods=['GET', 'POST'])
def enviar_cronograma():
    if request.method != 'POST':
        return redirect(url_for('main.home'))

    nombre_cliente = request.form.get('nombre', '').strip()
    destinatario = request.form.get('email', '').strip()
    monto_raw = request.form.get('monto', '').strip()
    cuotas_raw = request.form.get('cuotas', '').strip()
    tasa_interes_raw = request.form.get('tasa_interes', '').strip()

    try:
        monto = float(monto_raw)
    except (TypeError, ValueError):
        monto = None

    try:
        cuotas = int(cuotas_raw)
    except (TypeError, ValueError):
        cuotas = None

    try:
        tasa_interes = float(tasa_interes_raw) if tasa_interes_raw else 5.0
    except (TypeError, ValueError):
        tasa_interes = 5.0

    if not all([nombre_cliente, destinatario, monto, cuotas]):
        flash('Por favor completa nombre, correo, monto y cuotas para enviar el cronograma.', 'error')
        return redirect(url_for('main.home'))

    if monto <= 0 or cuotas <= 0:
        flash('El monto y el numero de cuotas deben ser mayores a cero.', 'error')
        return redirect(url_for('main.home'))

    try:
        msg = Message(
            subject="Tu Cronograma de Pagos - Gota a Gota",
            recipients=[destinatario]
        )

        msg.body = (
            f"Hola {nombre_cliente},\n\n"
            "Adjuntamos tu cronograma de pagos en formato PDF con los detalles del prestamo registrado.\n"
            "Por favor revisa el documento y conserva una copia para tu control."
        )

        msg.html = render_template(
            "email/email_cliente.html",
            nombre=nombre_cliente,
            monto=monto,
            cuotas=cuotas,
            tasa_interes=tasa_interes
        )

        pdf_buffer = generar_cronograma_pdf(nombre_cliente, monto, cuotas, tasa_interes)
        msg.attach("cronograma.pdf", "application/pdf", pdf_buffer.read())

        mail.send(msg)
        flash('Cronograma enviado correctamente al correo del cliente.', 'success')
    except Exception as error:
        print(f"Error al enviar el correo: {error}")
        flash('Ocurrio un problema al enviar el correo. Intentalo nuevamente.', 'error')

    return redirect(url_for('main.home'))