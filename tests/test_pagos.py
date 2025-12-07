import unittest
from datetime import date
from decimal import Decimal
from app import create_app, db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamoEnum
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.services.pago_service import PagoService

class PagoServiceTestCase(unittest.TestCase):
    
    def setUp(self):
        """Configurar la aplicación y la base de datos para las pruebas"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
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
    
    def _crear_cuota(self, prestamo_id, numero_cuota=1):
        """Helper: Crear una cuota"""
        cuota = Cuota(
            prestamo_id=prestamo_id,
            numero_cuota=numero_cuota,
            fecha_vencimiento=date.today(),
            monto_cuota=Decimal('500.00'),
            monto_capital=Decimal('400.00'),
            monto_interes=Decimal('100.00'),
            saldo_capital=Decimal('4600.00'),
            fecha_pago=None,
            monto_pagado=None
        )
        db.session.add(cuota)
        db.session.commit()
        return cuota
    
    def test_registrar_pago_exitoso(self):
        """Test: Registrar un pago exitoso"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            comprobante_referencia='TRF-001'
        )
        
        self.assertIsNotNone(respuesta)
        self.assertIsNone(error)
        self.assertEqual(status_code, 201)
        self.assertTrue(respuesta['success'])
    
    def test_registrar_pago_prestamo_no_vigente(self):
        """Test: Intentar registrar pago en préstamo no vigente"""
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
            comprobante_referencia='TRF-001'
        )
        
        self.assertIsNone(respuesta)
        self.assertIsNotNone(error)
        self.assertEqual(status_code, 400)
        self.assertIn('vigente', error.lower())
    
    def test_registrar_pago_monto_cero_o_negativo(self):
        """Test: Intentar registrar pago con monto inválido"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('-100.00'),
            comprobante_referencia='TRF-001'
        )
        
        self.assertIsNone(respuesta)
        self.assertIsNotNone(error)
        self.assertEqual(status_code, 400)
        self.assertIn('monto', error.lower())
    
    def test_registrar_pago_monto_excede_cuota(self):
        """Test: Intentar registrar pago mayor al monto de la cuota"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('1000.00'),
            comprobante_referencia='TRF-001'
        )
        
        self.assertIsNone(respuesta)
        self.assertIsNotNone(error)
        self.assertEqual(status_code, 400)
        self.assertIn('excede', error.lower())
    
    def test_registrar_pago_cuota_ya_pagada(self):
        """Test: Intentar registrar pago en cuota ya pagada"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        # Marcar como pagada
        cuota.monto_pagado = Decimal('500.00')
        cuota.fecha_pago = date.today()
        db.session.commit()
        
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            comprobante_referencia='TRF-001'
        )
        
        self.assertIsNone(respuesta)
        self.assertIsNotNone(error)
        self.assertEqual(status_code, 400)
        self.assertIn('pagada', error.lower())
    
    def test_obtener_resumen_pagos(self):
        """Test: Obtener resumen de pagos de un préstamo"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota1 = self._crear_cuota(prestamo.prestamo_id, 1)
        cuota2 = self._crear_cuota(prestamo.prestamo_id, 2)
        
        # Registrar dos pagos
        PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota1.cuota_id,
            monto_pagado=Decimal('500.00'),
            comprobante_referencia='TRF-001'
        )
        
        PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota2.cuota_id,
            monto_pagado=Decimal('500.00'),
            comprobante_referencia='TRF-002'
        )
        
        respuesta, error, status_code = PagoService.obtener_resumen_pagos_prestamo(prestamo.prestamo_id)
        
        self.assertIsNotNone(respuesta)
        self.assertIsNone(error)
        self.assertEqual(status_code, 200)
        self.assertTrue(respuesta['success'])
        self.assertEqual(respuesta['resumen']['total_cuotas'], 2)
    
    def test_campos_faltantes(self):
        """Test: Validar que los campos requeridos estén presentes"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id)
        
        # Intentar registrar pago sin comprobante (debe funcionar igual)
        respuesta, error, status_code = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            comprobante_referencia=None
        )
        
        # El comprobante es opcional, así que debe funcionar
        self.assertIsNotNone(respuesta)
        self.assertIsNone(error)
        self.assertEqual(status_code, 201)

if __name__ == '__main__':
    unittest.main()