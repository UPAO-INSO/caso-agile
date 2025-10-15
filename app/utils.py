# app/utils.py
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generar_pdf(nombre_cliente):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"Resumen de Solicitud - {nombre_cliente}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Estimado/a {nombre_cliente},")
    p.drawString(100, 700, "Gracias por tu confianza. Este es un ejemplo de PDF adjunto.")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
