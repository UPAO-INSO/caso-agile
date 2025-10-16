# app/utils.py
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta

def generar_cronograma_pdf(nombre_cliente, monto, cuotas, tasa_interes):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, 750, "Cronograma de Pagos")

    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Cliente: {nombre_cliente}")
    p.drawString(100, 700, f"Monto del préstamo: S/ {monto:.2f}")
    p.drawString(100, 680, f"Tasa de interés mensual: {tasa_interes}%")
    p.drawString(100, 660, f"Número de cuotas: {cuotas}")

    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, 630, "N°")
    p.drawString(150, 630, "Fecha de Pago")
    p.drawString(300, 630, "Monto (S/)")
    p.setFont("Helvetica", 12)

    # Simular cuotas mensuales
    monto_cuota = round((monto * (1 + (tasa_interes / 100))) / cuotas, 2)
    fecha_pago = datetime.now()

    for i in range(cuotas):
        p.drawString(100, 610 - (i * 20), str(i + 1))
        p.drawString(150, 610 - (i * 20), (fecha_pago + timedelta(days=30*i)).strftime("%d/%m/%Y"))
        p.drawString(300, 610 - (i * 20), f"{monto_cuota:.2f}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
