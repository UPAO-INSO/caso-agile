"""
Script de Verificación de Credenciales de Gmail
================================================

Este script prueba si las credenciales de Gmail están correctas
ANTES de ejecutar los tests completos.

Ejecutar con:
    python tests/test_gmail_credentials.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Cargar variables de entorno
load_dotenv()

def test_gmail_connection():
    """Prueba la conexión SMTP con Gmail"""
    
    print("\n" + "=" * 70)
    print("  TEST DE CONEXIÓN GMAIL SMTP")
    print("=" * 70)
    
    # Obtener credenciales del .env
    mail_username = os.getenv('MAIL_USERNAME')
    mail_password = os.getenv('MAIL_PASSWORD')
    mail_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    mail_port = int(os.getenv('MAIL_PORT', '587'))
    
    print(f"\n📧 Configuración:")
    print(f"   Servidor: {mail_server}:{mail_port}")
    print(f"   Usuario: {mail_username}")
    print(f"   Password: {'*' * len(mail_password) if mail_password else 'NO CONFIGURADO'}")
    
    if not mail_username or not mail_password:
        print("\n❌ ERROR: MAIL_USERNAME o MAIL_PASSWORD no están configurados en .env")
        return False
    
    if mail_password == 'tu_password_app':
        print("\n⚠️  ADVERTENCIA: Estás usando el password placeholder.")
        print("   Necesitas generar un App Password de Gmail real.")
        print("\n📖 Instrucciones:")
        print("   1. Ve a: https://myaccount.google.com/apppasswords")
        print("   2. Genera un nuevo App Password")
        print("   3. Actualiza MAIL_PASSWORD en .env")
        return False
    
    try:
        print(f"\n🔌 Conectando a {mail_server}:{mail_port}...")
        server = smtplib.SMTP(mail_server, mail_port)
        server.set_debuglevel(0)  # Cambiar a 1 para ver detalles
        
        print("🔐 Iniciando TLS...")
        server.starttls()
        
        print("🔑 Autenticando...")
        server.login(mail_username, mail_password)
        
        print("✅ ¡AUTENTICACIÓN EXITOSA!")
        print(f"   Gmail aceptó las credenciales de {mail_username}")
        
        # Opcional: Enviar email de prueba
        respuesta = input("\n¿Deseas enviar un email de prueba? (s/n): ")
        
        if respuesta.lower() == 's':
            destinatario = input("Ingresa el email destino (Enter para usar el mismo): ")
            if not destinatario.strip():
                destinatario = mail_username
            
            print(f"\n📤 Enviando email de prueba a {destinatario}...")
            
            msg = MIMEMultipart()
            msg['From'] = mail_username
            msg['To'] = destinatario
            msg['Subject'] = '✅ Test de Gmail SMTP - Financiera Demo'
            
            body = """
¡Hola!

Este es un email de prueba del sistema de notificaciones.

Si recibes este mensaje, significa que:
✅ Las credenciales de Gmail están correctas
✅ El servidor SMTP está funcionando
✅ Los emails se pueden enviar exitosamente

El sistema está listo para enviar:
- Cronogramas de préstamos
- Vouchers de pago
- Notificaciones automáticas

---
Financiera Demo - Sistema de Gestión
Enviado desde: """ + mail_username
            
            msg.attach(MIMEText(body, 'plain'))
            
            server.send_message(msg)
            print("✅ ¡Email enviado exitosamente!")
            print(f"   Revisa la bandeja de entrada de {destinatario}")
        
        server.quit()
        print("\n🎉 Todas las pruebas pasaron correctamente")
        print("   El sistema está listo para enviar emails")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print("\n❌ ERROR DE AUTENTICACIÓN")
        print(f"   Gmail rechazó las credenciales: {e}")
        print("\n🔧 Posibles soluciones:")
        print("   1. Verifica que el App Password sea correcto (sin espacios)")
        print("   2. Genera un nuevo App Password en:")
        print("      https://myaccount.google.com/apppasswords")
        print("   3. Asegúrate que la verificación en 2 pasos esté activada")
        print("   4. Actualiza MAIL_PASSWORD en .env con el nuevo password")
        return False
        
    except smtplib.SMTPException as e:
        print(f"\n❌ ERROR SMTP: {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False


def verificar_config_flask():
    """Verifica la configuración de Flask-Mail"""
    
    print("\n" + "=" * 70)
    print("  VERIFICACIÓN DE CONFIGURACIÓN FLASK")
    print("=" * 70)
    
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        print(f"\n⚙️  Configuración actual:")
        print(f"   MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
        print(f"   MAIL_PORT: {app.config.get('MAIL_PORT')}")
        print(f"   MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
        print(f"   MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
        print(f"   MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
        print(f"   MAIL_DEBUG: {app.config.get('MAIL_DEBUG')}")
        
        mail_debug = app.config.get('MAIL_DEBUG', False)
        
        if mail_debug:
            print("\n⚠️  ADVERTENCIA: MAIL_DEBUG está en True")
            print("   Los emails NO se enviarán realmente, solo se imprimirán en consola")
            print("\n🔧 Para enviar emails reales:")
            print("   1. Abre app/common/config.py")
            print("   2. Busca la línea: MAIL_DEBUG = True")
            print("   3. Cámbiala a: MAIL_DEBUG = False")
            print("   4. Reinicia la aplicación")
        else:
            print("\n✅ MAIL_DEBUG está en False - Los emails se enviarán realmente")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  🔍 DIAGNÓSTICO COMPLETO DE SISTEMA DE EMAILS")
    print("=" * 70)
    
    try:
        # Paso 1: Verificar configuración de Flask
        verificar_config_flask()
        
        # Paso 2: Probar conexión SMTP
        resultado = test_gmail_connection()
        
        if resultado:
            print("\n" + "=" * 70)
            print("  ✅ SISTEMA LISTO PARA ENVIAR EMAILS")
            print("=" * 70)
            print("\n📝 Próximos pasos:")
            print("   1. Ejecuta: python tests/test_pago_completo.py")
            print("   2. Verifica que lleguen 4 emails:")
            print("      - 1 cronograma de préstamo")
            print("      - 3 vouchers de pago (uno por cada cuota)")
            sys.exit(0)
        else:
            print("\n" + "=" * 70)
            print("  ❌ CONFIGURACIÓN INCOMPLETA")
            print("=" * 70)
            print("\nRevisa los errores arriba y corrígelos antes de continuar.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
