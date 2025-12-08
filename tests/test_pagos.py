import unittest
from datetime import date, timedelta
from decimal import Decimal
from app import create_app, db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamoEnum
from app.models.cuota import Cuota
from app.services.pago_service import PagoService
from app.services.mora_service import MoraService


class PagoPriorizacionMoraTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _crear_cliente(self):
        cliente = Cliente(
            dni='87654321',
            nombre_completo='Ana López',
            apellido_paterno='López',
            apellido_materno='Gómez',
            correo_electronico='ana@example.com',
            pep=False
        )
        db.session.add(cliente)
        db.session.commit()
        return cliente

    def _crear_prestamo(self, cliente_id):
        prestamo = Prestamo(
            cliente_id=cliente_id,
            monto_total=Decimal('2000.00'),
            interes_tea=Decimal('10.00'),
            plazo=12,
            f_otorgamiento=date.today(),
            estado=EstadoPrestamoEnum.VIGENTE,
            requiere_dec_jurada=False,
            declaracion_id=None
        )
        db.session.add(prestamo)
        db.session.commit()
        return prestamo

    def _crear_cuota(self, prestamo_id, numero, fecha_vencimiento, monto_cuota=Decimal('500.00')):
        cuota = Cuota(
            prestamo_id=prestamo_id,
            numero_cuota=numero,
            fecha_vencimiento=fecha_vencimiento,
            monto_cuota=monto_cuota,
            monto_capital=Decimal('400.00'),
            monto_interes=(monto_cuota - Decimal('400.00')),
            saldo_capital=Decimal('1600.00'),
            fecha_pago=None,
            monto_pagado=Decimal('0.00'),
            mora_acumulada=Decimal('0.00'),
            saldo_pendiente=monto_cuota
        )
        db.session.add(cuota)
        db.session.commit()
        return cuota

    def test_pago_parcial_menor_a_mora_paga_solo_mora(self):
        """
        Si la mora de la cuota es 5.00 y pago 3.00, se debe reducir la mora
        a 2.00; saldo_pendiente y monto_pagado (capital) no cambian.
        """
        cliente = self._crear_cliente()
        prestamo = self._crear_prestamo(cliente.cliente_id)

        # cuota vencida hace 35 días -> 1 mes => mora = 1% * 500 = 5.00
        fecha_venc = date.today() - timedelta(days=35)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_venc)

        # actualizar mora
        MoraService.actualizar_mora_cuota(cuota.cuota_id)
        cuota_db = Cuota.query.get(cuota.cuota_id)
        self.assertEqual(cuota_db.mora_acumulada, Decimal('5.00'))

        # pagar 3.00 (menor a mora)
        resp, err, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('3.00'),
            medio_pago='EFECTIVO'
        )
        self.assertIsNone(err)
        self.assertEqual(status, 201)

        cuota_after = Cuota.query.get(cuota.cuota_id)
        # mora reducida a 2.00
        self.assertEqual(cuota_after.mora_acumulada, Decimal('2.00'))
        # saldo pendiente no cambió (sigue siendo 500)
        self.assertEqual(cuota_after.saldo_pendiente, Decimal('500.00'))
        # monto_pagado por capital no cambió (solo se pagó mora)
        self.assertEqual(cuota_after.monto_pagado, Decimal('0.00'))

    def test_pago_parcial_cubre_mora_y_capital_parcial(self):
        """
        Pago de 250 sobre cuota con mora 5 debe:
        - pagar 5 de mora
        - aplicar 245 a saldo (monto_pagado)
        - dejar saldo_pendiente = 500 - 245 = 255
        """
        cliente = self._crear_cliente()
        prestamo = self._crear_prestamo(cliente.cliente_id)

        fecha_venc = date.today() - timedelta(days=35)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_venc)

        MoraService.actualizar_mora_cuota(cuota.cuota_id)
        cuota_init = Cuota.query.get(cuota.cuota_id)
        self.assertEqual(cuota_init.mora_acumulada, Decimal('5.00'))

        resp, err, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('250.00'),
        )
        self.assertIsNone(err)
        self.assertEqual(status, 201)

        cuota_after = Cuota.query.get(cuota.cuota_id)
        # mora consumida
        self.assertEqual(cuota_after.mora_acumulada, Decimal('0.00'))
        # monto_pagado capital incrementado en 245
        self.assertEqual(cuota_after.monto_pagado, Decimal('245.00'))
        # saldo pendiente actualizado
        self.assertEqual(cuota_after.saldo_pendiente, Decimal('255.00'))

    def test_pago_grande_cubre_varias_cuotas_prioridad(self):
        """
        Pago grande: cubre mora+saldo de la cuota1 y luego aplica a cuota2.
        Verificamos que la distribución respete la prioridad (mora -> saldo)
        y que los detalles_aplicacion reflejen los movimientos.
        """
        cliente = self._crear_cliente()
        prestamo = self._crear_prestamo(cliente.cliente_id)

        # Crear 2 cuotas vencidas
        fecha_venc_1 = date.today() - timedelta(days=35)  # mora 5
        fecha_venc_2 = date.today() - timedelta(days=65)  # mora 2 meses -> 10 (1%*500*2)

        cuota1 = self._crear_cuota(prestamo.prestamo_id, 1, fecha_venc_1)
        cuota2 = self._crear_cuota(prestamo.prestamo_id, 2, fecha_venc_2)

        # actualizar moras del préstamo
        MoraService.actualizar_mora_prestamo(prestamo.prestamo_id)

        c1 = Cuota.query.get(cuota1.cuota_id)
        c2 = Cuota.query.get(cuota2.cuota_id)
        self.assertEqual(c1.mora_acumulada, Decimal('5.00'))
        self.assertEqual(c2.mora_acumulada, Decimal('10.00'))

        # Pagar 600 -> debe cubrir:
        # cuota1: mora 5 + saldo 500 => total 505 (queda 95 disponible)
        # con 95 se debe aplicar a cuota2: primero su mora (10) -> queda 85
        # luego saldo de cuota2 85 -> cuota2.saldo_pendiente = 500 - 85 = 415
        resp, err, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota2.cuota_id,  # pago reportado contra cuota2, pero la lógica aplica a todas pendientes
            monto_pagado=Decimal('600.00'),
        )
        self.assertIsNone(err)
        self.assertEqual(status, 201)
        self.assertTrue(resp['success'])

        # recargar cuotas
        c1_after = Cuota.query.get(c1.cuota_id)
        c2_after = Cuota.query.get(c2.cuota_id)

        # cuota1 debe quedar pagada (mora 0, saldo 0)
        self.assertEqual(c1_after.mora_acumulada, Decimal('0.00'))
        self.assertEqual(c1_after.saldo_pendiente, Decimal('0.00'))
        self.assertTrue(c1_after.fecha_pago is not None)

        # cuota2 mora descontada y saldo reducido
        self.assertEqual(c2_after.mora_acumulada, Decimal('0.00'))
        self.assertEqual(c2_after.saldo_pendiente, Decimal('415.00'))
        # revisar que en la respuesta haya detalles para ambas cuotas
        detalles = resp.get('detalles_aplicacion', [])
        self.assertTrue(any(d['concepto'] == 'Mora' and d['cuota_numero'] == 1 for d in detalles))
        self.assertTrue(any(d['concepto'] == 'Saldo Pendiente' and d['cuota_numero'] == 2 for d in detalles))

    def test_rechaza_monto_cero_o_negativo(self):
        cliente = self._crear_cliente()
        prestamo = self._crear_prestamo(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, date.today())

        resp, err, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('0.00'),
        )
        self.assertIsNotNone(err)
        self.assertEqual(status, 400)

        resp2, err2, status2 = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('-10.00'),
        )
        self.assertIsNotNone(err2)
        self.assertEqual(status2, 400)

    def test_rechaza_pago_prestamo_no_vigente(self):
        cliente = self._crear_cliente()
        prestamo = self._crear_prestamo(cliente.cliente_id)
        # cancelar préstamo
        prestamo.estado = EstadoPrestamoEnum.CANCELADO
        db.session.commit()

        cuota = self._crear_cuota(prestamo.prestamo_id, 1, date.today())

        resp, err, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('100.00'),
        )
        self.assertIsNotNone(err)
        self.assertEqual(status, 400)

    def test_resumen_mora_coincide_con_sumatoria(self):
        cliente = self._crear_cliente()
        prestamo = self._crear_prestamo(cliente.cliente_id)
        # crear cuotas vencidas para sumar mora
        c1 = self._crear_cuota(prestamo.prestamo_id, 1, date.today() - timedelta(days=35))
        c2 = self._crear_cuota(prestamo.prestamo_id, 2, date.today() - timedelta(days=65))

        MoraService.actualizar_mora_prestamo(prestamo.prestamo_id)
        resp, err, status = PagoService.obtener_resumen_pagos_prestamo(prestamo.prestamo_id)
        self.assertIsNone(err)
        self.assertEqual(status, 200)
        mora_total_calculada = Decimal(str(resp['resumen']['mora_total']))
        # sumar directamente de la db
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo.prestamo_id).all()
        suma_moras = sum(c.mora_acumulada for c in cuotas)
        self.assertEqual(mora_total_calculada, suma_moras)


if __name__ == '__main__':
    unittest.main()
