"""
PDF Service
Maneja la generación de archivos PDF para la aplicación.
Centraliza la lógica de creación de documentos PDF.
"""

import logging
from io import BytesIO
from num2words import num2words
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PDFService:
    """Servicio para generación de PDFs"""
    
    @staticmethod
    def generar_cronograma_detallado_pdf(nombre_cliente, prestamo, cronograma):
        """
        Genera un PDF detallado con el cronograma completo (capital, interés, saldo).
        
        Args:
            nombre_cliente: Nombre del cliente
            prestamo: Objeto Prestamo con los datos
            cronograma: Lista de diccionarios con cronograma detallado
            
        Returns:
            BytesIO: Buffer con el contenido del PDF
        """
        try:
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Encabezado
            p.setFont("Helvetica-Bold", 16)
            p.drawString(150, 750, "Cronograma Detallado de Pagos")
            
            # Información del préstamo
            p.setFont("Helvetica", 11)
            p.drawString(50, 720, f"Cliente: {nombre_cliente}")
            p.drawString(50, 705, f"ID Préstamo: {prestamo.prestamo_id}")
            p.drawString(50, 690, f"Monto: S/ {float(prestamo.monto_total):.2f}")
            p.drawString(300, 705, f"TEA: {float(prestamo.interes_tea):.2f}%")
            p.drawString(300, 690, f"Plazo: {prestamo.plazo} meses")
            
            # Cabecera de la tabla
            p.setFont("Helvetica-Bold", 10)
            y_pos = 660
            p.drawString(50, y_pos, "N°")
            p.drawString(80, y_pos, "Fecha Venc.")
            p.drawString(170, y_pos, "Cuota")
            p.drawString(240, y_pos, "Capital")
            p.drawString(310, y_pos, "Interés")
            p.drawString(380, y_pos, "Saldo")
            
            # Dibujar línea
            p.line(50, y_pos - 5, 550, y_pos - 5)
            
            # Datos del cronograma
            p.setFont("Helvetica", 9)
            
            for cuota in cronograma:
                y_pos -= 20
                
                # Nueva página si es necesario
                if y_pos < 50:
                    p.showPage()
                    p.setFont("Helvetica-Bold", 10)
                    p.drawString(50, 750, "N°")
                    p.drawString(80, 750, "Fecha Venc.")
                    p.drawString(170, 750, "Cuota")
                    p.drawString(240, 750, "Capital")
                    p.drawString(310, 750, "Interés")
                    p.drawString(380, 750, "Saldo")
                    p.line(50, 745, 550, 745)
                    p.setFont("Helvetica", 9)
                    y_pos = 730
                
                p.drawString(50, y_pos, str(cuota['numero']))
                p.drawString(80, y_pos, cuota['fecha_vencimiento'])
                p.drawString(170, y_pos, f"S/ {cuota['monto_cuota']:.2f}")
                p.drawString(240, y_pos, f"S/ {cuota['capital']:.2f}")
                p.drawString(310, y_pos, f"S/ {cuota['interes']:.2f}")
                p.drawString(380, y_pos, f"S/ {cuota['saldo']:.2f}")
            
            p.showPage()
            p.save()
            buffer.seek(0)
            
            logger.debug(f"PDF detallado generado para préstamo {prestamo.prestamo_id}")
            return buffer
            
        except Exception as e:
            logger.error(f"Error al generar PDF detallado: {e}")
            raise
    
    @staticmethod
    def generar_voucher_pago(cliente, prestamo, cuota, pago):
        """
        Genera un PDF con el voucher/comprobante de pago.
        
        MÓDULO 2: Incluye información de conciliación contable y ajuste de redondeo.
        
        Args:
            cliente: Objeto Cliente
            prestamo: Objeto Prestamo
            cuota: Objeto Cuota
            pago: Objeto Pago con todos los detalles del pago
            
        Returns:
            BytesIO: Buffer con el contenido del PDF
        """
        try:
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            # === ENCABEZADO ===
            p.setFont("Helvetica-Bold", 18)
            p.drawCentredString(width / 2, height - 50, "FINANCIERA DEMO S.A.")
            
            p.setFont("Helvetica", 10)
            p.drawCentredString(width / 2, height - 70, "RUC: 20123456789")
            p.drawCentredString(width / 2, height - 85, "Av. Financiera 123, San Isidro, Lima")
            
            # Línea separadora
            p.line(50, height - 95, width - 50, height - 95)
            
            # === TÍTULO DEL COMPROBANTE ===
            p.setFont("Helvetica-Bold", 14)
            p.drawCentredString(width / 2, height - 120, "COMPROBANTE DE PAGO")
            
            p.setFont("Helvetica", 10)
            fecha_hora = pago.fecha_registro.strftime("%d/%m/%Y %H:%M:%S")
            p.drawCentredString(width / 2, height - 140, f"Fecha: {fecha_hora}")
            
            # === DATOS DE LA TRANSACCIÓN ===
            y_pos = height - 170
            p.setFont("Helvetica-Bold", 11)
            p.drawString(50, y_pos, "DATOS DE LA TRANSACCIÓN")
            p.line(50, y_pos - 5, width - 50, y_pos - 5)
            
            y_pos -= 25
            p.setFont("Helvetica", 10)
            
            # Operación
            p.drawString(50, y_pos, "Operación N°:")
            p.setFont("Helvetica-Bold", 10)
            p.drawString(200, y_pos, f"#{pago.pago_id:08d}")
            
            # Comprobante referencia
            y_pos -= 20
            p.setFont("Helvetica", 10)
            p.drawString(50, y_pos, "Comprobante:")
            p.setFont("Helvetica-Bold", 10)
            p.drawString(200, y_pos, pago.comprobante_referencia or "N/A")
            
            # === DATOS DEL CLIENTE ===
            y_pos -= 35
            p.setFont("Helvetica-Bold", 11)
            p.drawString(50, y_pos, "DATOS DEL CLIENTE")
            p.line(50, y_pos - 5, width - 50, y_pos - 5)
            
            y_pos -= 25
            p.setFont("Helvetica", 10)
            
            # Cliente
            p.drawString(50, y_pos, "Cliente:")
            p.setFont("Helvetica-Bold", 10)
            nombre_completo = f"{cliente.nombre_completo} {cliente.apellido_paterno} {cliente.apellido_materno}"
            p.drawString(200, y_pos, nombre_completo)
            
            # DNI
            y_pos -= 20
            p.setFont("Helvetica", 10)
            p.drawString(50, y_pos, "DNI:")
            p.setFont("Helvetica-Bold", 10)
            p.drawString(200, y_pos, cliente.dni)
            
            # === DATOS DEL PRÉSTAMO Y CUOTA ===
            y_pos -= 35
            p.setFont("Helvetica-Bold", 11)
            p.drawString(50, y_pos, "DATOS DEL PRÉSTAMO")
            p.line(50, y_pos - 5, width - 50, y_pos - 5)
            
            y_pos -= 25
            p.setFont("Helvetica", 10)
            
            # Préstamo ID
            p.drawString(50, y_pos, "Préstamo N°:")
            p.setFont("Helvetica-Bold", 10)
            p.drawString(200, y_pos, f"#{prestamo.prestamo_id}")
            
            # Cuota
            y_pos -= 20
            p.setFont("Helvetica", 10)
            p.drawString(50, y_pos, "Cuota N°:")
            p.setFont("Helvetica-Bold", 10)
            total_cuotas = len(prestamo.cuotas)
            p.drawString(200, y_pos, f"{cuota.numero_cuota} de {total_cuotas}")
            
            # Fecha de vencimiento
            y_pos -= 20
            p.setFont("Helvetica", 10)
            p.drawString(50, y_pos, "Fecha Vencimiento:")
            p.setFont("Helvetica-Bold", 10)
            p.drawString(200, y_pos, cuota.fecha_vencimiento.strftime("%d/%m/%Y"))
            
            # === DETALLE FINANCIERO ===
            y_pos -= 35
            p.setFont("Helvetica-Bold", 11)
            p.drawString(50, y_pos, "DETALLE DE LA CUOTA")
            p.line(50, y_pos - 5, width - 50, y_pos - 5)
            
            # Recuadro gris (Fondo)
            p.setFillColorRGB(0.95, 0.95, 0.95)
            p.rect(50, y_pos - 130, width - 100, 120, fill=True, stroke=False) # Aumenté altura
            p.setFillColorRGB(0, 0, 0)
            
            y_pos -= 25
            p.setFont("Helvetica", 10)
            
            # 1. Capital
            p.drawString(60, y_pos, "Amortización Capital:")
            p.drawRightString(width - 60, y_pos, f"S/ {float(cuota.monto_capital):.2f}")
            
            # 2. Interés
            y_pos -= 20
            p.drawString(60, y_pos, "Interés Compensatorio:")
            p.drawRightString(width - 60, y_pos, f"S/ {float(cuota.monto_interes):.2f}")
            
            # 3. Mora / Penalidad (CORRECCIÓN: No lo dejes hardcoded en 0)
            # Asumiendo que el objeto pago o cuota tiene el dato real
            mora_monto = getattr(pago, 'monto_mora', 0.00) 
            y_pos -= 20
            p.drawString(60, y_pos, "Interés Moratorio / Penalidad:")
            p.drawRightString(width - 60, y_pos, f"S/ {float(mora_monto):.2f}")
            
            # Línea de suma
            y_pos -= 10
            p.setDash(1, 2) # Línea punteada para separar subtotales
            p.line(60, y_pos, width - 60, y_pos)
            p.setDash([]) # Reset línea sólida
            
            # 4. TOTAL NUMÉRICO
            y_pos -= 20
            p.setFont("Helvetica-Bold", 12)
            p.drawString(60, y_pos, "TOTAL PAGADO:")
            p.setFillColorRGB(0.2, 0.4, 0.7) # Azul corporativo
            p.drawRightString(width - 60, y_pos, f"S/ {float(pago.monto_pagado):.2f}")
            p.setFillColorRGB(0, 0, 0)

            # 5. IMPORTE EN LETRAS (Elemento CRÍTICO en Perú)
            # Esto da formalidad y evita fraudes por adulteración de números
            y_pos -= 20
            p.setFont("Helvetica-Oblique", 9)
            monto_letras = num2words(float(pago.monto_pagado), lang='es').upper()
            p.drawCentredString(width / 2, y_pos, f"SON: {monto_letras} CON {int(pago.monto_pagado * 100) % 100}/100 SOLES")
            
            # === CONCILIACIÓN CONTABLE (Solo si hay ajuste) ===
            if float(pago.ajuste_redondeo) != 0:
                y_pos -= 35
                p.setFont("Helvetica-Bold", 11)
                p.drawString(50, y_pos, "CONCILIACIÓN CONTABLE")
                p.setFillColorRGB(1, 0.75, 0)
                p.rect(45, y_pos - 5, width - 90, 2, fill=True, stroke=False)
                p.setFillColorRGB(0, 0, 0)
                
                # Recuadro amarillo
                p.setFillColorRGB(1, 0.98, 0.8)
                p.rect(50, y_pos - 85, width - 100, 75, fill=True, stroke=True)
                p.setFillColorRGB(0, 0, 0)
                
                y_pos -= 25
                p.setFont("Helvetica", 9)
                
                # Monto contable
                p.drawString(60, y_pos, "Monto Contable (Deuda):")
                p.drawRightString(width - 60, y_pos, f"S/ {float(pago.monto_contable):.2f}")
                
                # Monto recibido
                y_pos -= 15
                p.drawString(60, y_pos, "Monto Recibido (Caja):")
                p.drawRightString(width - 60, y_pos, f"S/ {float(pago.monto_pagado):.2f}")
                
                # Ajuste redondeo
                y_pos -= 15
                p.setFont("Helvetica-Bold", 9)
                p.drawString(60, y_pos, "Ajuste por Redondeo:")
                p.drawRightString(width - 60, y_pos, f"S/ {float(pago.ajuste_redondeo):.2f}")
                
                # Nota legal
                y_pos -= 20
                p.setFont("Helvetica-Oblique", 8)
                p.drawString(60, y_pos, "* Ley N° 29571 - Redondeo a favor del consumidor")
            
            # === OBSERVACIONES ===
            if pago.observaciones:
                y_pos -= 35
                p.setFont("Helvetica-Bold", 11)
                p.drawString(50, y_pos, "OBSERVACIONES")
                p.line(50, y_pos - 5, width - 50, y_pos - 5)
                
                y_pos -= 25
                p.setFont("Helvetica", 9)
                # Manejar texto largo
                texto = pago.observaciones
                max_width = width - 100
                from reportlab.pdfbase.pdfmetrics import stringWidth
                if stringWidth(texto, "Helvetica", 9) > max_width:
                    # Dividir en líneas
                    palabras = texto.split()
                    linea_actual = ""
                    for palabra in palabras:
                        test_linea = linea_actual + " " + palabra if linea_actual else palabra
                        if stringWidth(test_linea, "Helvetica", 9) <= max_width:
                            linea_actual = test_linea
                        else:
                            p.drawString(60, y_pos, linea_actual)
                            y_pos -= 12
                            linea_actual = palabra
                    if linea_actual:
                        p.drawString(60, y_pos, linea_actual)
                else:
                    p.drawString(60, y_pos, texto)
            
            # === PIE DE PÁGINA ===
            p.setFont("Helvetica", 7)
            disclaimer = "Este documento es una CONSTANCIA DE PAGO INTERNA y no reemplaza a la Boleta de Venta o Factura Electrónica."
            if hasattr(pago, 'es_fiscal') and pago.es_fiscal:
                 disclaimer = "Representación Impresa de la Boleta de Venta Electrónica."
            
            p.drawCentredString(width / 2, 50, disclaimer)
            
            # Finalizar
            p.showPage()
            p.save()
            buffer.seek(0)
            
            logger.info(f"Voucher PDF generado para pago #{pago.pago_id}")
            return buffer
            
        except Exception as e:
            logger.error(f"Error al generar voucher PDF: {e}")
            raise
