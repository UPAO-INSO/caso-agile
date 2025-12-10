"""
PDF Service
Maneja la generación de archivos PDF para la aplicación.
Centraliza la lógica de creación de documentos PDF.
"""

import logging
from reportlab.lib.pagesizes import letter
import qrcode
import hashlib
import base64
from io import BytesIO
from num2words import num2words
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFService:
    """Servicio para generación de PDFs"""

    EMPRESA = {
        "ruc": "20601234567",
        "razon_social": "FINANCIERA CASO AGILE S.A.C.",
        "direccion": "Av. Larco 123, Trujillo, La Libertad",
        "telefono": "(044) 20-2020",
        "email": "comfyprestamos@gmail.com"
    }

    @staticmethod
    def _generar_qr_img(data):
        """Genera imagen QR para incrustar en PDF"""
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return ImageReader(buffer)

    @staticmethod
    def _generar_hash(data):
        """Simula el Hash de la firma digital (SHA256)"""
        return base64.b64encode(hashlib.sha256(data.encode()).digest()).decode()[:28]

    @staticmethod
    def generar_voucher_pago(cliente, prestamo, cuota, pago):
        """
        Genera el PDF con formato de FACTURA o BOLETA ELECTRÓNICA.
        """
        try:
            buffer = BytesIO()
            # Usamos A4 que es el estándar para impresión de facturas
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4 # 595.27 x 841.89
            
            # --- 1. LÓGICA TRIBUTARIA ---
            # Si el documento del cliente tiene 11 dígitos, es RUC -> FACTURA
            es_factura = len(cliente.dni) == 11 
            
            tipo_comprobante = "FACTURA ELECTRÓNICA" if es_factura else "BOLETA DE VENTA ELECTRÓNICA"
            codigo_tipo = "01" if es_factura else "03"
            serie = "F001" if es_factura else "B001"
            correlativo = f"{pago.pago_id:08d}" # Ej: 00000123
            
            # Cálculos (Asumiendo que el pago es precio final con IGV)
            total = float(pago.monto_pagado)
            subtotal = total / 1.18
            igv = total - subtotal

            # --- 2. DIBUJAR ENCABEZADO (EMPRESA) ---
            # Logo (simulado con texto grande)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(40, height - 50, PDFService.EMPRESA["razon_social"])
            
            c.setFont("Helvetica", 9)
            c.drawString(40, height - 70, PDFService.EMPRESA["direccion"])
            c.drawString(40, height - 82, f"Telf: {PDFService.EMPRESA['telefono']} | Email: {PDFService.EMPRESA['email']}")
            
            # --- 3. RECUADRO RUC (Elemento Distintivo SUNAT) ---
            # Borde Rectangular
            c.setLineWidth(1.5)
            c.roundRect(350, height - 110, 200, 80, 4, stroke=1, fill=0)
            
            # Contenido del Recuadro
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(450, height - 50, f"R.U.C. {PDFService.EMPRESA['ruc']}")
            
            # Franja de Tipo de Documento
            c.setFillColorRGB(0.9, 0.9, 0.9) # Gris claro
            c.rect(351, height - 80, 198, 20, stroke=0, fill=1)
            c.setFillColorRGB(0, 0, 0) # Volver a negro
            
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(450, height - 74, tipo_comprobante)
            
            c.setFont("Helvetica", 14)
            c.drawCentredString(450, height - 100, f"{serie} - {correlativo}")

            # --- 4. DATOS DEL CLIENTE ---
            y = height - 150
            c.setFont("Helvetica-Bold", 9)
            c.drawString(40, y, "FECHA DE EMISIÓN:")
            c.drawString(40, y - 15, "SEÑOR(ES):")
            c.drawString(40, y - 30, "RUC/DNI:")
            c.drawString(40, y - 45, "DIRECCIÓN:")
            c.drawString(380, y, "MONEDA:")
            c.drawString(380, y - 15, "FORMA DE PAGO:")

            c.setFont("Helvetica", 9)
            nombre_cli = f"{cliente.nombre_completo} {cliente.apellido_paterno} {cliente.apellido_materno}"
            c.drawString(140, y, pago.fecha_registro.strftime("%d/%m/%Y"))
            c.drawString(140, y - 15, nombre_cli.upper())
            c.drawString(140, y - 30, cliente.dni)
            c.drawString(140, y - 45, (cliente.direccion or "NO REGISTRADO").upper())
            c.drawString(470, y, "SOLES")
            c.drawString(470, y - 15, "CONTADO")

            # --- 5. TABLA DE PRODUCTOS ---
            y_table = y - 75
            # Encabezados de tabla
            c.setLineWidth(0.5)
            c.line(40, y_table, 550, y_table) # Linea superior
            c.line(40, y_table - 15, 550, y_table - 15) # Linea inferior cabecera
            
            c.setFont("Helvetica-Bold", 8)
            c.drawString(45, y_table - 10, "CANT.")
            c.drawString(80, y_table - 10, "UNIDAD")
            c.drawString(130, y_table - 10, "DESCRIPCIÓN")
            c.drawRightString(480, y_table - 10, "P. UNIT")
            c.drawRightString(540, y_table - 10, "TOTAL")

            # Items (Solo uno: La cuota)
            y_item = y_table - 30
            c.setFont("Helvetica", 8)
            
            descripcion = f"PAGO DE CUOTA N° {cuota.numero_cuota} - PRESTAMO #{prestamo.prestamo_id}"
            if pago.ajuste_redondeo != 0:
                descripcion += " (Incluye redondeo de ley)"

            c.drawString(45, y_item, "1")
            c.drawString(80, y_item, "ZZ") # ZZ = Unidad servicio
            c.drawString(130, y_item, descripcion)
            c.drawRightString(480, y_item, f"{subtotal:.2f}")
            c.drawRightString(540, y_item, f"{subtotal:.2f}")

            # --- 6. TOTALES Y PIE DE PÁGINA ---
            y_footer = y_item - 50
            c.line(40, y_item - 10, 550, y_item - 10) # Linea fin items

            # Monto en Letras
            try:
                letras = num2words(total, lang='es').upper()
            except:
                letras = "MONTO EN LETRAS"
            c.setFont("Helvetica", 8)
            c.drawString(40, y_footer, f"SON: {letras} CON {int(total*100)%100}/100 SOLES")

            # Cuadro de Totales (Derecha Inferior)
            c.setFont("Helvetica-Bold", 9)
            c.drawRightString(480, y_footer, "OP. GRAVADA:")
            c.drawRightString(480, y_footer - 15, "I.G.V. (18%):")
            c.drawRightString(480, y_footer - 30, "IMPORTE TOTAL:")

            c.setFont("Helvetica", 9)
            c.drawRightString(540, y_footer, f"S/ {subtotal:.2f}")
            c.drawRightString(540, y_footer - 15, f"S/ {igv:.2f}")
            c.setFont("Helvetica-Bold", 9)
            c.drawRightString(540, y_footer - 30, f"S/ {total:.2f}")

            # --- 7. SEGURIDAD (QR y HASH) ---
            y_security = y_footer - 80
            
            # Texto semilla para Hash y QR
            texto_qr = f"{PDFService.EMPRESA['ruc']}|{codigo_tipo}|{serie}|{correlativo}|{igv:.2f}|{total:.2f}|{pago.fecha_registro.date()}|6|{cliente.dni}|"
            
            # Generar e insertar QR
            qr_img = PDFService._generar_qr_img(texto_qr)
            c.drawImage(qr_img, 40, y_security - 10, width=90, height=90)
            
            # Hash y Textos legales
            c.setFont("Helvetica", 7)
            hash_code = PDFService._generar_hash(texto_qr)
            c.drawString(140, y_security + 60, f"Resumen (Hash): {hash_code}")
            c.drawString(140, y_security + 50, "Representación Impresa del Comprobante Electrónico")
            c.drawString(140, y_security + 40, "Autorizado mediante Resolución de Superintendencia N° 300-2014/SUNAT")
            c.drawString(140, y_security + 30, "Consulte su documento en www.casoagile.com/buscar")

            c.save()
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            raise
    
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
    
