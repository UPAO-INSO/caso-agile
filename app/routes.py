from flask import Blueprint, render_template, request, redirect, url_for
from flask_mail import Message
from app import mail

main = Blueprint('main', __name__)

@main.route('/') 
def home(): 
    return render_template('index.html', title='Inicio') 

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

    # Redirige al inicio
    return redirect(url_for('main.home'))

@main.route('/buscar')
def buscar_cliente():
    return render_template('buscar_cliente.html', title='Buscar Cliente')

@main.route('/cronograma-pagos')
def cronograma_pagos():
    return render_template('cronograma_pagos.html', title='Cronograma de Pagos')

@main.route('/test-modal')
def test_modal():
    return render_template('test_modal.html', title='Test Modal')
