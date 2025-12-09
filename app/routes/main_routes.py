from flask import render_template, redirect, url_for, request, flash
from app.services.email_service import EmailService
from app.routes import main_bp

@main_bp.route('/') 
def home(): 
    return render_template('index.html', title='Inicio')

@main_bp.route('/buscar-cliente')
def buscar_cliente():
    """Vista para buscar cliente y otorgar préstamo"""
    return render_template('buscar_cliente.html', title='Buscar Cliente') 

@main_bp.route('/enviar_cronograma', methods=['GET', 'POST'])
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
        # Usar servicio de email refactorizado
        exito = EmailService.enviar_cronograma_simple(
            nombre_cliente, 
            destinatario, 
            monto, 
            cuotas, 
            tasa_interes
        )
        
        if exito:
            flash('Cronograma enviado correctamente al correo del cliente.', 'success')
        else:
            flash('Ocurrio un problema al enviar el correo. Intentalo nuevamente.', 'error')
            
    except Exception as error:
        print(f"Error al enviar el correo: {error}")
        flash('Ocurrio un problema al enviar el correo. Intentalo nuevamente.', 'error')

    return redirect(url_for('main.home'))