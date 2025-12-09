import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import unittest
from datetime import date, timedelta
from decimal import Decimal
from app import create_app, db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamoEnum
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.services.pago_service import PagoService
from app.services.mora_service import MoraService


class PagoServiceTestCase(unittest.TestCase):
    
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _crear_cliente_prueba(self):
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
    
    def _crear_cuota(self, prestamo_id, numero_cuota=1, fecha_vencimiento=None):
        if fecha_vencimiento is None:
            fecha_vencimiento = date.today()
            
        cuota = Cuota(
            prestamo_id=prestamo_id,
            numero_cuota=numero_cuota,
            fecha_vencimiento=fecha_vencimiento,
            monto_cuota=Decimal('500.00'),
            monto_capital=Decimal('400.00'),
            monto_interes=Decimal('100.00'),
            saldo_capital=Decimal('4600.00'),
            fecha_pago=None,
            monto_pagado=Decimal('0.00'),
            mora_acumulada=Decimal('0.00'),
            saldo_pendiente=Decimal('500.00')
        )
        db.session.add(cuota)
        db.session.commit()
        return cuota

    def test_calcular_mora_cuota_vencida(self):
        """Test: Calcular mora para cuota vencida"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida hace 35 días (más de 1 mes)
        fecha_vencimiento = date.today() - timedelta(days=35)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        mora = MoraService.calcular_mora_cuota(
            Decimal('500.00'),
            cuota.fecha_vencimiento
        )
        
        # 1 mes de atraso = 1% de 500 = 5 soles
        self.assertEqual(mora, Decimal('5.00'))

    def test_calcular_mora_cuota_no_vencida(self):
        """Test: Cuota no vencida no tiene mora"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida en el futuro
        fecha_vencimiento = date.today() + timedelta(days=10)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        mora = MoraService.calcular_mora_cuota(
            Decimal('500.00'),
            cuota.fecha_vencimiento
        )
        
        self.assertEqual(mora, Decimal('0.00'))

    def test_multiples_meses_atraso_mora_acumulativa(self):
        """Test: Mora no acumulativa - 1% por cada mes"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida hace 65 días (más de 2 meses)
        fecha_vencimiento = date.today() - timedelta(days=65)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        mora = MoraService.calcular_mora_cuota(
            Decimal('100.00'),
            cuota.fecha_vencimiento
        )
        
        # 2 meses de atraso = 2% de 100 = 2 soles
        self.assertEqual(mora, Decimal('2.00'))

    def test_pago_completo_sin_mora(self):
        """Test: Pago completo a tiempo no genera mora"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1)
        
        respuesta, error, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='TRANSFERENCIA',
            comprobante_referencia='TRF-001'
        )
        
        self.assertIsNotNone(respuesta)
        self.assertIsNone(error)
        self.assertEqual(status, 201)
        self.assertTrue(respuesta['success'])

        def test_pago_parcial_genera_mora_en_saldo(self):
            """Test: Pago parcial - mora se aplica al saldo pendiente"""
            cliente = self._crear_cliente_prueba()
            prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
            
            # Cuota vencida hace 35 días (más de 1 mes)
            fecha_vencimiento = date.today() - timedelta(days=35)
            cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
            
            # Primero actualizar mora inicial (vencida hace 35 días = 1 mes)
            MoraService.actualizar_mora_cuota(cuota.cuota_id)
            cuota_inicial = Cuota.query.get(cuota.cuota_id)
            
            # Mora inicial = 1% de 500 = 5.00
            self.assertEqual(cuota_inicial.mora_acumulada, Decimal('5.00'))
            
            # Pago parcial de 250 (esto cubrirá: 5 de mora + 245 de capital)
            respuesta, error, status = PagoService.registrar_pago_cuota(
                prestamo_id=prestamo.prestamo_id,
                cuota_id=cuota.cuota_id,
                monto_pagado=Decimal('250.00'),
                medio_pago='TRANSFERENCIA',
                comprobante_referencia='TRF-001'
            )
            
            self.assertIsNotNone(respuesta)
            self.assertIsNone(error)
            self.assertEqual(status, 201)
            
            # Después del pago: saldo = 500 - 245 = 255
            cuota_actualizada = Cuota.query.get(cuota.cuota_id)
            self.assertEqual(cuota_actualizada.saldo_pendiente, Decimal('255.00'))
            
            # La mora de la cuota anterior se pagó completamente (5.00)
            self.assertEqual(cuota_actualizada.mora_acumulada, Decimal('0.00'))

    def test_prioridad_pago_mora_antes_saldo(self):
        """Test: Los pagos cubren primero mora, luego saldo"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida
        fecha_vencimiento = date.today() - timedelta(days=35)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        # Pago parcial para generar mora
        PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('250.00'),
            medio_pago='TRANSFERENCIA',
            comprobante_referencia='TRF-001'
        )
        
        # Actualizar mora
        MoraService.actualizar_mora_cuota(cuota.cuota_id)
        
        # Siguiente pago: 5 soles (todo se va a mora) + 248 soles a saldo
        respuesta, error, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('253.00'),
            medio_pago='TRANSFERENCIA',
            comprobante_referencia='TRF-002'
        )
        
        self.assertIsNotNone(respuesta)
        self.assertIsNone(error)

    def test_resumen_pagos_con_mora(self):
        """Test: Resumen de pagos incluye mora total"""
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Dos cuotas vencidas
        cuota1 = self._crear_cuota(prestamo.prestamo_id, 1, date.today() - timedelta(days=35))
        cuota2 = self._crear_cuota(prestamo.prestamo_id, 2, date.today() - timedelta(days=5))
        
        respuesta, error, status = PagoService.obtener_resumen_pagos_prestamo(prestamo.prestamo_id)
        
        self.assertIsNotNone(respuesta)
        self.assertIsNone(error)
        self.assertEqual(status, 200)
        self.assertTrue(respuesta['success'])
        self.assertGreater(respuesta['resumen']['mora_total'], 0)


if __name__ == '__main__':
    unittest.main()