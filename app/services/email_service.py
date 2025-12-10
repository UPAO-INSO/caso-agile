"""
Email Service
Maneja el envío de correos electrónicos de la aplicación.
Centraliza la lógica de composición y envío de emails.
"""

import logging
from flask import render_template
from flask_mail import Message
from app.common.extensions import mail
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de correos electrónicos"""
    
    @staticmethod
    def enviar_cronograma_completo(cliente, prestamo, cronograma):
        """
        Envía un correo electrónico con el cronograma COMPLETO y DETALLADO del préstamo.
        
        Este método reemplaza a enviar_confirmacion_prestamo() y proporciona:
        - Resumen del préstamo
        - Tabla HTML completa con todas las cuotas (capital, interés, saldo)
        - Identificación de cuotas de ajuste
        - PDF adjunto con cronograma detallado
        
        Args:
            cliente: Objeto Cliente con los datos del cliente
            prestamo: Objeto Prestamo con los datos del préstamo
            cronograma: Lista de diccionarios con cronograma detallado del FinancialService
            
        Returns:
            bool: True si el email se envió exitosamente, False en caso contrario
        """
        try:
            if not cliente.correo_electronico:
                logger.warning(f"Cliente {cliente.dni} no tiene correo electrónico registrado")
                return False
            
            # Preparar datos para el template
            nombre_completo = f"{cliente.nombre_completo} {cliente.apellido_paterno} {cliente.apellido_materno}"
            
            # Calcular totales
            total_cuotas = sum(c['monto_cuota'] for c in cronograma)
            total_capital = sum(c['monto_capital'] for c in cronograma)
            total_interes = sum(c['monto_interes'] for c in cronograma)
            
            # Primera fecha de vencimiento
            primera_fecha = cronograma[0]['fecha_vencimiento'].strftime('%d/%m/%Y') if cronograma else "N/A"
            
            # Crear mensaje
            msg = Message(
                subject=f"📋 Cronograma Detallado de Pagos - Préstamo #{prestamo.prestamo_id}",
                recipients=[cliente.correo_electronico]
            )
            
            # Cuerpo de texto plano
            msg.body = f"""
Hola {nombre_completo},

¡Felicidades! Tu préstamo ha sido desembolsado exitosamente.

RESUMEN DEL PRÉSTAMO
====================
Préstamo N°: #{prestamo.prestamo_id}
Monto Desembolsado: S/ {float(prestamo.monto_total):.2f}
Tasa de Interés (TEA): {float(prestamo.interes_tea):.2f}%
Plazo: {prestamo.plazo} meses
Fecha de Otorgamiento: {prestamo.f_otorgamiento.strftime('%d/%m/%Y')}
Primera Cuota: {primera_fecha}
Número de Cuotas: {len(cronograma)}

TOTALES
=======
Total a Pagar: S/ {float(total_cuotas):.2f}
Total Capital: S/ {float(total_capital):.2f}
Total Intereses: S/ {float(total_interes):.2f}

Adjunto encontrarás el cronograma detallado en formato PDF y también en el cuerpo del correo.

Gracias por confiar en nosotros.

Atentamente,
Financiera Demo S.A.
"""
            
            # Cuerpo HTML con tabla detallada
            msg.html = render_template(
                "emails/cronograma_detallado.html",
                nombre_cliente=nombre_completo,
                prestamo_id=prestamo.prestamo_id,
                monto_total=float(prestamo.monto_total),
                interes_tea=float(prestamo.interes_tea),
                plazo=prestamo.plazo,
                fecha_otorgamiento=prestamo.f_otorgamiento.strftime('%d/%m/%Y'),
                primera_fecha_vencimiento=primera_fecha,
                num_cuotas=len(cronograma),
                cronograma=cronograma,
                total_cuotas=float(total_cuotas),
                total_capital=float(total_capital),
                total_interes=float(total_interes)
            )
            
            # Adjuntar PDF detallado del cronograma
            try:
                pdf_buffer = PDFService.generar_cronograma_detallado_pdf(
                    nombre_completo,
                    prestamo,
                    [{
                        'numero': c['numero_cuota'],
                        'fecha_vencimiento': c['fecha_vencimiento'].strftime('%d/%m/%Y'),
                        'monto_cuota': float(c['monto_cuota']),
                        'capital': float(c['monto_capital']),
                        'interes': float(c['monto_interes']),
                        'saldo': float(c['saldo_capital'])
                    } for c in cronograma]
                )
                pdf_buffer.seek(0)
                pdf_bytes = pdf_buffer.read()
                msg.attach(
                    f"cronograma_prestamo_{prestamo.prestamo_id}.pdf",
                    "application/pdf",
                    pdf_bytes
                )
                logger.debug(f"PDF detallado adjuntado para préstamo {prestamo.prestamo_id}")
            except Exception as attach_exc:
                logger.error(f"Error al adjuntar PDF detallado: {attach_exc}")
                # Continuar sin PDF si falla
            
            # Enviar email
            mail.send(msg)
            logger.info(
                f"Cronograma completo enviado exitosamente a {cliente.correo_electronico} "
                f"para préstamo #{prestamo.prestamo_id}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar cronograma completo a {cliente.correo_electronico}: {str(e)}")
            return False
    
    @staticmethod
    def enviar_voucher_pago(cliente, prestamo, cuota, pago):
        """
        Envía un correo electrónico con el voucher/comprobante de pago.
        
        MÓDULO 2: Incluye información de conciliación contable y ajuste de redondeo
        según la Ley N° 29571.
        
        Args:
            cliente: Objeto Cliente
            prestamo: Objeto Prestamo
            cuota: Objeto Cuota que fue pagada
            pago: Objeto Pago con todos los detalles del pago
            
        Returns:
            bool: True si el email se envió exitosamente, False en caso contrario
        """
        try:
            if not cliente.correo_electronico:
                logger.warning(f"Cliente {cliente.dni} no tiene correo electrónico registrado")
                return False
            
            # Preparar datos
            nombre_completo = f"{cliente.nombre_completo} {cliente.apellido_paterno} {cliente.apellido_materno}"
            total_cuotas = len(prestamo.cuotas)
            
            # Calcular cuotas pendientes
            cuotas_pendientes = sum(1 for c in prestamo.cuotas if not c.monto_pagado or c.monto_pagado == 0)
            
            # Próxima fecha de vencimiento (primera cuota sin pagar)
            proxima_cuota = next(
                (c for c in sorted(prestamo.cuotas, key=lambda x: x.numero_cuota)
                 if not c.monto_pagado or c.monto_pagado == 0),
                None
            )
            proxima_fecha = proxima_cuota.fecha_vencimiento.strftime('%d/%m/%Y') if proxima_cuota else "N/A"
            
            # Crear mensaje
            msg = Message(
                subject=f"✓ Comprobante de Pago - Cuota #{cuota.numero_cuota} - Préstamo #{prestamo.prestamo_id}",
                recipients=[cliente.correo_electronico]
            )
            
            # Cuerpo de texto plano
            msg.body = f"""
Hola {nombre_completo},

¡Tu pago ha sido registrado exitosamente!

COMPROBANTE DE PAGO
===================
Operación N°: #{pago.pago_id:08d}
Fecha: {pago.fecha_registro.strftime('%d/%m/%Y %H:%M:%S')}
Comprobante: {pago.comprobante_referencia or 'N/A'}

DATOS DEL PRÉSTAMO
==================
Préstamo N°: #{prestamo.prestamo_id}
Cuota N°: {cuota.numero_cuota} de {total_cuotas}
Fecha Vencimiento: {cuota.fecha_vencimiento.strftime('%d/%m/%Y')}

DETALLE FINANCIERO
==================
Amortización Capital: S/ {float(cuota.monto_capital):.2f}
Intereses: S/ {float(cuota.monto_interes):.2f}
Mora/Otros: S/ 0.00
-----------------------------------------
TOTAL PAGADO: S/ {float(pago.monto_pagado):.2f}

MÉTODO DE PAGO: {pago.metodo_pago.value}
"""
            
            # Agregar información de conciliación si hay ajuste
            if float(pago.ajuste_redondeo) != 0:
                msg.body += f"""
CONCILIACIÓN CONTABLE (Ley N° 29571)
=====================================
Monto Contable (Deuda): S/ {float(pago.monto_contable):.2f}
Monto Recibido (Caja): S/ {float(pago.monto_pagado):.2f}
Ajuste por Redondeo: S/ {float(pago.ajuste_redondeo):.2f}
"""
            
            msg.body += f"""
ESTADO DEL PRÉSTAMO
===================
Cuotas Pendientes: {cuotas_pendientes}
{'Próxima Cuota: ' + proxima_fecha if cuotas_pendientes > 0 else '¡Préstamo completado!'}

Conserva este comprobante para tu control personal.

Gracias por tu puntualidad.

Atentamente,
Financiera Demo S.A.
"""
            
            # Cuerpo HTML
            msg.html = render_template(
                "emails/voucher_pago.html",
                nombre_cliente=nombre_completo,
                dni_cliente=cliente.dni,
                prestamo_id=prestamo.prestamo_id,
                numero_cuota=cuota.numero_cuota,
                total_cuotas=total_cuotas,
                pago_id=pago.pago_id,
                fecha_pago=pago.fecha_registro.strftime('%d/%m/%Y'),
                hora_pago=pago.fecha_registro.strftime('%H:%M:%S'),
                comprobante_referencia=pago.comprobante_referencia,
                monto_capital=float(cuota.monto_capital),
                monto_interes=float(cuota.monto_interes),
                mora_otros=0.00,
                monto_pagado=float(pago.monto_pagado),
                monto_contable=float(pago.monto_contable),
                ajuste_redondeo=float(pago.ajuste_redondeo),
                metodo_pago=pago.metodo_pago.value,
                cuotas_pendientes=cuotas_pendientes,
                proxima_fecha_vencimiento=proxima_fecha,
                observaciones=pago.observaciones
            )
            
            # Adjuntar PDF del voucher
            try:
                pdf_buffer = PDFService.generar_voucher_pago(
                    cliente,
                    prestamo,
                    cuota,
                    pago
                )
                pdf_buffer.seek(0)
                pdf_bytes = pdf_buffer.read()
                msg.attach(
                    f"voucher_pago_{pago.pago_id}.pdf",
                    "application/pdf",
                    pdf_bytes
                )
                logger.debug(f"Voucher PDF adjuntado para pago #{pago.pago_id}")
            except Exception as attach_exc:
                logger.error(f"Error al adjuntar voucher PDF: {attach_exc}")
                # Continuar sin PDF si falla
            
            # Enviar email
            mail.send(msg)
            logger.info(
                f"Voucher de pago enviado exitosamente a {cliente.correo_electronico} "
                f"para pago #{pago.pago_id} (Cuota #{cuota.numero_cuota})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar voucher de pago a {cliente.correo_electronico}: {str(e)}")
            return False
