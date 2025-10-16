"""
PDF Service
Maneja la generación de archivos PDF para la aplicación.
Centraliza la lógica de creación de documentos PDF.
"""

import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PDFService:
    """Servicio para generación de PDFs"""
    
    @staticmethod
    def generar_cronograma_pdf(nombre_cliente, monto, cuotas, tasa_interes):
        """
        Genera un PDF con el cronograma de pagos.
        
        Args:
            nombre_cliente: Nombre completo del cliente
            monto: Monto total del préstamo
            cuotas: Número de cuotas
            tasa_interes: Tasa de interés (TEA en porcentaje)
            
        Returns:
            BytesIO: Buffer con el contenido del PDF
        """
        try:
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Encabezado
            p.setFont("Helvetica-Bold", 16)
            p.drawString(180, 750, "Cronograma de Pagos")
            
            # Información del préstamo
            p.setFont("Helvetica", 12)
            p.drawString(100, 720, f"Cliente: {nombre_cliente}")
            p.drawString(100, 700, f"Monto del préstamo: S/ {monto:.2f}")
            p.drawString(100, 680, f"Tasa de interés (TEA): {tasa_interes:.2f}%")
            p.drawString(100, 660, f"Número de cuotas: {cuotas}")
            
            # Cabecera de la tabla
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, 630, "N°")
            p.drawString(150, 630, "Fecha de Pago")
            p.drawString(300, 630, "Monto (S/)")
            
            # Datos de las cuotas
            p.setFont("Helvetica", 12)
            
            # Calcular cuota mensual simple (para el PDF)
            # En producción real, esto debería usar los mismos cálculos que financial_service
            monto_cuota = round((monto * (1 + (tasa_interes / 100))) / cuotas, 2)
            fecha_pago = datetime.now()
            
            for i in range(cuotas):
                y_pos = 610 - (i * 20)
                
                # Verificar si necesitamos nueva página
                if y_pos < 50:
                    p.showPage()
                    p.setFont("Helvetica", 12)
                    y_pos = 750
                
                p.drawString(100, y_pos, str(i + 1))
                p.drawString(150, y_pos, (fecha_pago + timedelta(days=30*i)).strftime("%d/%m/%Y"))
                p.drawString(300, y_pos, f"{monto_cuota:.2f}")
            
            p.showPage()
            p.save()
            buffer.seek(0)
            
            logger.debug(f"PDF generado exitosamente para {nombre_cliente}")
            return buffer
            
        except Exception as e:
            logger.error(f"Error al generar PDF: {e}")
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
