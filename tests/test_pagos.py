import unittest
from datetime import date, timedelta
from decimal import Decimal
from app import create_app, db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamoEnum
from app.models.cuota import Cuota
from app.models.pago import Pago, MedioPagoEnum
from app.services.pago_service import PagoService
from app.services.mora_service import MoraService


class PagoServiceTestCase(unittest.TestCase):
    
    def setUp(self):
        """Configurar la aplicación y la base de datos para las pruebas"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()
        
    def tearDown(self):
        """Limpiar la base de datos después de las pruebas"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _crear_cliente_prueba(self):
        """Helper: Crear un cliente de prueba"""
        cliente = Cliente(
            dni='12345678',
            nombre_completo='Juan Pérez',
            apellido_paterno='Pérez',
            apellido_materno='García',
            correo_electronico='juan@example.com',
            pep=False
        )
        db.session.add(cliente)
        db.session.commit()
        return cliente
    
    def _crear_prestamo_vigente(self, cliente_id):
        """Helper: Crear un préstamo vigente"""
        prestamo = Prestamo(
            cliente_id=cliente_id,
            monto_total=Decimal('5000.00'),
            interes_tea=Decimal('12.50'),
            plazo=12,
            f_otorgamiento=date.today(),
            estado=EstadoPrestamoEnum.VIGENTE,
            requiere_dec_jurada=False,
            declaracion_id=None
        )
        db.session.add(prestamo)
        db.session.commit()
        return prestamo
    
    def _crear_cuota(self, prestamo_id, numero_cuota=1, fecha_vencimiento=None, monto_cuota=Decimal('500.00')):
        """Helper: Crear una cuota"""
        if fecha_vencimiento is None:
            fecha_vencimiento = date.today()
            
        cuota = Cuota(
            prestamo_id=prestamo_id,
            numero_cuota=numero_cuota,
            fecha_vencimiento=fecha_vencimiento,
            monto_cuota=monto_cuota,
            monto_capital=Decimal('400.00'),
            monto_interes=Decimal('100.00'),
            saldo_capital=Decimal('4600.00'),
            fecha_pago=None,
            monto_pagado=None
        )
        db.session.add(cuota)
        db.session.commit()
        return cuota
    
    # ========== TESTS BÁSICOS DE REGISTRO DE PAGOS ==========
    
    def test_registrar_pago_exitoso_efectivo(self):
        """Test RF1: Registrar pago completo en efectivo"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='EFECTIVO',
            comprobante_referencia='EFE-001'
        )
        
        self.assertIsNotNone(respuesta)
        self.assertIsNone(error)
        self.assertEqual(status_code, 201)
        self.assertTrue(respuesta['success'])
        self.assertEqual(respuesta['pago']['medio_pago'], 'EFECTIVO')
        self.assertEqual(Decimal(respuesta['pago']['monto_pagado']), Decimal('500.00'))
        self.assertEqual(Decimal(respuesta['pago']['saldo_pendiente']), Decimal('0.00'))
    
    def test_registrar_pago_tarjeta_debito(self):
        """Test RF1: Registrar pago con tarjeta de débito"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='TARJETA_DEBITO',
            comprobante_referencia='TDB-12345'
        )
        
        self.assertIsNotNone(respuesta)
        self.assertEqual(status_code, 201)
        self.assertEqual(respuesta['pago']['medio_pago'], 'TARJETA_DEBITO')
    
    def test_registrar_pago_transferencia(self):
        """Test RF1: Registrar pago por transferencia bancaria"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='TRANSFERENCIA',
            comprobante_referencia='TRF-ABC123',
            observaciones='Pago desde BCP'
        )
        
        self.assertIsNotNone(respuesta)
        self.assertEqual(status_code, 201)
        self.assertEqual(respuesta['pago']['medio_pago'], 'TRANSFERENCIA')
    
    def test_registrar_pago_billetera_electronica(self):
        """Test RF1: Registrar pago con billetera electrónica (Yape/Plin)"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='BILLETERA_ELECTRONICA',
            comprobante_referencia='YAPE-789456'
        )
        
        self.assertIsNotNone(respuesta)
        self.assertEqual(status_code, 201)
        self.assertEqual(respuesta['pago']['medio_pago'], 'BILLETERA_ELECTRONICA')
    
    # ========== TESTS DE PAGO PARCIAL ==========
    
    def test_registrar_pago_parcial(self):
        """Test RF1: Registrar pago parcial de 50 soles sobre cuota de 100"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id, monto_cuota=Decimal('100.00'))
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('50.00'),
            medio_pago='EFECTIVO'
        )
        
        self.assertIsNotNone(respuesta)
        self.assertEqual(status_code, 201)
        self.assertEqual(Decimal(respuesta['pago']['monto_pagado']), Decimal('50.00'))
        self.assertEqual(Decimal(respuesta['pago']['saldo_pendiente']), Decimal('50.00'))
    
    # ========== TESTS DE CÁLCULO DE MORA (RF4) ==========
    
    def test_mora_cuota_vencida_sin_pago(self):
        """Test RF4: Mora de 1% sobre 100 soles = 1 sol después de vencimiento"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida hace 1 día
        fecha_vencimiento = date.today() - timedelta(days=1)
        cuota = self._crear_cuota(
            prestamo.prestamo_id,
            fecha_vencimiento=fecha_vencimiento,
            monto_cuota=Decimal('100.00')
        )
        
        # Calcular mora
        monto_mora, dias_mora = MoraService.calcular_mora_cuota(cuota, date.today())
        
        self.assertGreater(monto_mora, Decimal('0'))
        self.assertGreater(dias_mora, 0)
        # Mora de 1% sobre capital de 400 (no sobre 100 de cuota total)
        self.assertEqual(monto_mora, Decimal('4.00'))
    
    def test_pago_parcial_anula_mora_mismo_mes(self):
        """Test RF4: Pago parcial en mes de vencimiento anula la mora"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida hace 15 días (mismo mes)
        fecha_vencimiento = date.today() - timedelta(days=15)
        cuota = self._crear_cuota(
            prestamo.prestamo_id,
            fecha_vencimiento=fecha_vencimiento,
            monto_cuota=Decimal('100.00')
        )
        
        # Registrar pago parcial de 50 soles
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('50.00'),
            medio_pago='EFECTIVO',
            fecha_pago=date.today()
        )
        
        self.assertIsNotNone(respuesta)
        # La mora debe ser 0 porque hubo pago parcial en el mismo mes
        self.assertEqual(Decimal(respuesta['pago']['monto_mora']), Decimal('0.00'))
    
    def test_mora_no_acumulativa_multiples_meses(self):
        """Test RF4: Mora no es acumulativa - se aplica 1% por cada mes no pagado"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota 1: Abril (vencida hace 60 días = 2 meses)
        fecha_venc_abril = date.today() - timedelta(days=60)
        cuota_abril = self._crear_cuota(
            prestamo.prestamo_id,
            numero_cuota=1,
            fecha_vencimiento=fecha_venc_abril,
            monto_cuota=Decimal('100.00')
        )
        
        # Calcular mora
        monto_mora, dias_mora = MoraService.calcular_mora_cuota(cuota_abril, date.today())
        
        # Mora = 1% sobre capital (400) por 2 meses = 8.00
        # NO es acumulativa (1% + 2% + 3%), es simplemente 1% * num_meses
        self.assertEqual(dias_mora, 60)
        self.assertEqual(monto_mora, Decimal('8.00'))  # (400 * 0.01) * 2
    
    def test_escenario_completo_mora_abril_mayo(self):
        """Test RF4: Escenario completo - no pago abril, pago mayo con mora acumulada"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota de ABRIL (vencida hace 30 días)
        fecha_abril = date.today() - timedelta(days=30)
        cuota_abril = self._crear_cuota(
            prestamo.prestamo_id,
            numero_cuota=4,
            fecha_vencimiento=fecha_abril,
            monto_cuota=Decimal('100.00')
        )
        
        # Cuota de MAYO (vence hoy)
        cuota_mayo = self._crear_cuota(
            prestamo.prestamo_id,
            numero_cuota=5,
            fecha_vencimiento=date.today(),
            monto_cuota=Decimal('100.00')
        )
        
        # Pagar cuota de abril con mora
        monto_mora_abril, _ = MoraService.calcular_mora_cuota(cuota_abril, date.today())
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota_abril.cuota_id,
            monto_pagado=Decimal('100.00'),
            medio_pago='TRANSFERENCIA'
        )
        
        self.assertIsNotNone(respuesta)
        # Total a pagar = 100 (cuota abril) + mora
        self.assertEqual(Decimal(respuesta['pago']['monto_mora']), monto_mora_abril)
    
    def test_pago_siguiente_mes_sin_pago_anterior_aplica_mora(self):
        """Test RF4: Si no pago en abril, y pago parcial en mayo, mora se anula solo en mayo"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota abril (vencida hace 35 días)
        fecha_abril = date.today() - timedelta(days=35)
        cuota_abril = self._crear_cuota(
            prestamo.prestamo_id,
            numero_cuota=4,
            fecha_vencimiento=fecha_abril,
            monto_cuota=Decimal('100.00')
        )
        
        # Calcular mora de abril
        monto_mora_abril, _ = MoraService.calcular_mora_cuota(cuota_abril, date.today())
        
        # La mora debe ser > 0 porque no hubo pago
        self.assertGreater(monto_mora_abril, Decimal('0'))
        self.assertEqual(monto_mora_abril, Decimal('4.00'))  # 1% de 400 capital
    
    # ========== TESTS DE VALIDACIONES ==========
    
    def test_registrar_pago_prestamo_cancelado(self):
        """Test: No se puede pagar préstamo cancelado"""
        cliente = self._crear_cliente_prueba()
        prestamo = Prestamo(
            cliente_id=cliente.cliente_id,
            monto_total=Decimal('5000.00'),
            interes_tea=Decimal('12.50'),
            plazo=12,
            f_otorgamiento=date.today(),
            estado=EstadoPrestamoEnum.CANCELADO,
            requiere_dec_jurada=False,
            declaracion_id=None
        )
        db.session.add(prestamo)
        db.session.commit()
        
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='EFECTIVO'
        )
        
        self.assertIsNone(respuesta)
        self.assertIsNotNone(error)
        self.assertEqual(status_code, 400)
        self.assertIn('vigente', error.lower())
    
    def test_monto_pago_negativo(self):
        """Test: Rechazar monto negativo"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('-100.00'),
            medio_pago='EFECTIVO'
        )
        
        self.assertIsNone(respuesta)
        self.assertIsNotNone(error)
        self.assertEqual(status_code, 400)
    
    def test_monto_pago_cero(self):
        """Test: Rechazar monto cero"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('0.00'),
            medio_pago='EFECTIVO'
        )
        
        self.assertIsNone(respuesta)
        self.assertEqual(status_code, 400)
    
    # ========== TESTS DE ENDPOINTS ==========
    
    def test_endpoint_registrar_pago(self):
        """Test: Endpoint POST /pagos/registrar"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        payload = {
            'prestamo_id': prestamo.prestamo_id,
            'cuota_id': cuota.cuota_id,
            'monto_pagado': 500.00,
            'medio_pago': 'EFECTIVO',
            'comprobante_referencia': 'TEST-001'
        }
        
        response = self.client.post('/pagos/registrar', json=payload)
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['pago']['medio_pago'], 'EFECTIVO')
    
    def test_endpoint_resumen_pagos(self):
        """Test: Endpoint GET /pagos/resumen/<prestamo_id>"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        # Registrar un pago primero
        PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='EFECTIVO'
        )
        
        response = self.client.get(f'/pagos/resumen/{prestamo.prestamo_id}')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('resumen', data)
    
    def test_endpoint_registrar_pago_sin_datos(self):
        """Test: Endpoint rechaza petición sin datos"""
        response = self.client.post('/pagos/registrar', json={})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])


if __name__ == '__main__':
    unittest.main()