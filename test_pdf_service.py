import os
from datetime import datetime
from app.services.pdf_service import PDFService

class Dummy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

def test_pdf_boleta_factura():
    # Cliente con DNI (boleta)
    cliente_boleta = Dummy(
        nombre_completo="Juan",
        apellido_paterno="Perez",
        apellido_materno="Gomez",
        dni="12345678",
        direccion="Calle Falsa 123"
    )
    # Cliente con RUC (factura)
    cliente_factura = Dummy(
        nombre_completo="Empresa SAC",
        apellido_paterno="",
        apellido_materno="",
        dni="20123456789",
        direccion="Av. Empresa 456"
    )
    prestamo = Dummy(
        prestamo_id=1
    )
    cuota = Dummy(
        numero_cuota=1
    )
    pago = Dummy(
        pago_id=1,
        monto_pagado=118.0,
        ajuste_redondeo=0.0,
        fecha_registro=datetime.now(),
        metodo_pago="EFECTIVO"
    )
    # Boleta
    buffer_boleta = PDFService.generar_voucher_pago(cliente_boleta, prestamo, cuota, pago)
    with open("boleta_test.pdf", "wb") as f:
        f.write(buffer_boleta.getvalue())
    print("Boleta generada: boleta_test.pdf")
    # Factura
    buffer_factura = PDFService.generar_voucher_pago(cliente_factura, prestamo, cuota, pago)
    with open("factura_test.pdf", "wb") as f:
        f.write(buffer_factura.getvalue())
    print("Factura generada: factura_test.pdf")

if __name__ == "__main__":
    test_pdf_boleta_factura()
