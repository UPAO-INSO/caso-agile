from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta

def generar_cronograma_pdf(nombre_cliente, monto, cuotas, tasa_interes):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    elements = []

    # --- ENCABEZADO ---
    title_style = styles["Title"]
    subtitle_style = styles["Normal"]
    title_style.textColor = colors.HexColor("#1a237e")

    elements.append(Paragraph("Cronograma de Pagos", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Cliente:</b> {nombre_cliente}", subtitle_style))
    elements.append(Paragraph(f"<b>Monto del préstamo:</b> S/ {monto:,.2f}", subtitle_style))
    elements.append(Paragraph(f"<b>Tasa de interés mensual:</b> {tasa_interes}%", subtitle_style))
    elements.append(Paragraph(f"<b>Número de cuotas:</b> {cuotas}", subtitle_style))
    elements.append(Spacer(1, 20))

    # --- TABLA DEL CRONOGRAMA ---
    data = [["N°", "Fecha de Pago", "Monto (S/)", "Saldo Restante (S/)"]]
    
    monto_cuota = round((monto * (1 + (tasa_interes / 100))) / cuotas, 2)
    fecha_pago = datetime.now()
    saldo = round(monto * (1 + (tasa_interes / 100)), 2)

    for i in range(cuotas):
        saldo -= monto_cuota
        data.append([
            str(i + 1),
            (fecha_pago + timedelta(days=30 * i)).strftime("%d/%m/%Y"),
            f"{monto_cuota:,.2f}",
            f"{max(saldo, 0):,.2f}"
        ])

    table = Table(data, colWidths=[0.8*inch, 1.6*inch, 1.4*inch, 1.6*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # --- PIE ---
    footer_text = Paragraph(
        "Este documento ha sido generado automáticamente por el sistema Gota a Gota. "
        "Por favor, conserve este cronograma como comprobante de su préstamo.",
        styles["Italic"]
    )
    elements.append(footer_text)

    doc.build(elements)
    buffer.seek(0)
    return buffer
