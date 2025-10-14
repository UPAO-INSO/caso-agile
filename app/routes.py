from flask import Blueprint, render_template, request, redirect, url_for
from flask_mail import Message
from app import mail

main = Blueprint('main', __name__)

@main.route('/') 
def home(): 
    return render_template('index.html', title='Inicio') 

@main.route('/enviar_prueba_correo') 
def enviar_prueba_correo(): 
    # El correo del destinatario
    destinatario = "valeriatbw@gmail.com"
    
    try:
        msg = Message(
            subject='Asunto de Prueba: Envío Exitoso',
            
            recipients=[destinatario] # Lista de destinatarios
        )
        # El cuerpo del mensaje
        msg.body = "Este es el cuerpo del mensaje en texto plano."
        msg.html = "<h1>Este es el cuerpo en HTML (opcional)</h1><p>Funciona con la configuración de Gmail.</p>"
        
        # Envía el mensaje
        mail.send(msg)
        
        # Opcional: Muestra un mensaje de éxito en la página
        flash(f"Correo de prueba enviado con éxito a {destinatario}.", 'success')
        
    except Exception as e:
        # Muestra un error si falla el envío
        flash(f"Error al enviar correo. Revise la configuración de Gmail: {e}", 'error')
        print(f"Error de Correo: {e}") 

    # Redirige al inicio
    return redirect(url_for('main.home'))