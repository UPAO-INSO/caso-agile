"""
Email Service
Maneja el envío de correos electrónicos de la aplicación.
Centraliza la lógica de composición y envío de emails.
"""

import logging
from flask import render_template
from flask_mail import Message
from app.extensions import mail
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de correos electrónicos"""
    
    @staticmethod
    def enviar_confirmacion_prestamo(cliente, prestamo, cronograma):
        """
        Envía un correo electrónico al cliente con los detalles del préstamo aprobado.
        
        Args:
            cliente: Objeto Cliente con los datos del cliente
            prestamo: Objeto Prestamo con los datos del préstamo
            cronograma: Lista de diccionarios con el cronograma de pagos
            
        Returns:
            bool: True si el email se envió exitosamente, False en caso contrario
        """
        try:
            if not cliente.correo_electronico:
                logger.warning(f"Cliente {cliente.dni} no tiene correo electrónico registrado")
                return False
            
            # Crear mensaje
            msg = Message(
                subject="Confirmación de Préstamo - Gota a Gota",
                recipients=[cliente.correo_electronico]
            )
            
            # Cuerpo de texto plano
            msg.body = EmailService._generar_cuerpo_texto(cliente, prestamo, cronograma)
            
            # Cuerpo HTML
            msg.html = render_template(
                "emails/email_cliente.html",
                nombre=cliente.nombre_completo,
                prestamo_id=prestamo.prestamo_id,
                monto=float(prestamo.monto_total),
                interes_tea=float(prestamo.interes_tea),
                plazo=prestamo.plazo,
                fecha=prestamo.f_otorgamiento.strftime('%d/%m/%Y'),
                num_cuotas=len(cronograma)
            )
            
            # Adjuntar PDF del cronograma
            try:
                pdf_buffer = PDFService.generar_cronograma_pdf(
                    cliente.nombre_completo,
                    float(prestamo.monto_total),
                    len(cronograma),
                    float(prestamo.interes_tea)
                )
                pdf_buffer.seek(0)
                pdf_bytes = pdf_buffer.read()
                msg.attach("cronograma.pdf", "application/pdf", pdf_bytes)
                logger.debug(f"PDF adjuntado para préstamo {prestamo.prestamo_id}")
            except Exception as attach_exc:
                logger.error(f"Error al adjuntar PDF: {attach_exc}")
                # Continuar sin PDF si falla
            
            # Enviar email
            mail.send(msg)
            logger.info(f"Email enviado exitosamente a {cliente.correo_electronico}")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar correo a {cliente.correo_electronico}: {str(e)}")
            return False
    
    @staticmethod
    def _generar_cuerpo_texto(cliente, prestamo, cronograma):
        """
        Genera el cuerpo de texto plano del email.
        
        Args:
            cliente: Objeto Cliente
            prestamo: Objeto Prestamo
            cronograma: Lista de cronograma
            
        Returns:
            str: Cuerpo del email en texto plano
        """
        return f"""
Hola {cliente.nombre_completo},

Tu préstamo ha sido aprobado exitosamente.

Detalles del Préstamo:
- ID: {prestamo.prestamo_id}
- Monto: S/ {float(prestamo.monto_total):.2f}
- Tasa de Interés (TEA): {float(prestamo.interes_tea):.2f}%
- Plazo: {prestamo.plazo} meses
- Fecha de Otorgamiento: {prestamo.f_otorgamiento.strftime('%d/%m/%Y')}
- Número de Cuotas: {len(cronograma)}

Gracias por confiar en nosotros.

Atentamente,
Gota a Gota
"""
    
    @staticmethod
    def enviar_cronograma_simple(nombre_cliente, destinatario, monto, cuotas, tasa_interes):
        """
        Envía un cronograma simple sin préstamo registrado (función legacy).
        
        Args:
            nombre_cliente: Nombre del cliente
            destinatario: Email destino
            monto: Monto del préstamo
            cuotas: Número de cuotas
            tasa_interes: Tasa de interés
            
        Returns:
            bool: True si se envió exitosamente
        """
        try:
            msg = Message(
                subject="Tu Cronograma de Pagos - Gota a Gota",
                recipients=[destinatario]
            )
            
            msg.body = f"""
Hola {nombre_cliente},

Adjunto encontrarás el cronograma de pagos para tu préstamo.

Detalles:
- Monto: S/ {monto:.2f}
- Cuotas: {cuotas}
- Tasa de Interés: {tasa_interes}%

Saludos,
Gota a Gota
"""
            
            # Adjuntar PDF
            pdf_buffer = PDFService.generar_cronograma_pdf(
                nombre_cliente, monto, cuotas, tasa_interes
            )
            pdf_buffer.seek(0)
            msg.attach("cronograma.pdf", "application/pdf", pdf_buffer.read())
            
            mail.send(msg)
            logger.info(f"Cronograma simple enviado a {destinatario}")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar cronograma simple: {e}")
            return False
