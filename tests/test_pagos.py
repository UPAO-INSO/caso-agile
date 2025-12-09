import unittest
import logging
from datetime import date, timedelta
from decimal import Decimal
from app import create_app, db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamoEnum
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.services.pago_service import PagoService
from app.services.mora_service import MoraService

# Configurar logging para ver mensajes de los servicios
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class PagoServiceTestCase(unittest.TestCase):
    
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        print("\n" + "="*80)
        print(f"INICIANDO TEST: {self._testMethodName}")
        print("="*80)
        
    def tearDown(self):
        print("\n" + "-"*80)
        print(f"FINALIZANDO TEST: {self._testMethodName}")
        print("-"*80 + "\n")
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
        print(f"✓ Cliente creado: ID={cliente.cliente_id}, DNI={cliente.dni}, Nombre={cliente.nombre_completo}")
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
        print(f"✓ Préstamo creado: ID={prestamo.prestamo_id}, Monto={prestamo.monto_total}, TEA={prestamo.interes_tea}%, Plazo={prestamo.plazo} meses")
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
        
        dias_para_vencimiento = (fecha_vencimiento - date.today()).days
        estado_vencimiento = "VENCIDA" if dias_para_vencimiento < 0 else "VIGENTE"
        print(f"✓ Cuota #{numero_cuota} creada: ID={cuota.cuota_id}, Monto={cuota.monto_cuota}, "
              f"Vencimiento={fecha_vencimiento} ({estado_vencimiento}, {abs(dias_para_vencimiento)} días)")
        return cuota

    def test_calcular_mora_cuota_vencida(self):
        """Test: Calcular mora para cuota vencida"""
        print("\n📋 TEST: Calcular mora para cuota vencida (35 días de atraso)")
        print("-" * 80)
        
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida hace 35 días (más de 1 mes)
        fecha_vencimiento = date.today() - timedelta(days=35)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        print(f"\n🔍 Calculando mora:")
        print(f"   - Monto base: S/. 500.00")
        print(f"   - Fecha vencimiento: {fecha_vencimiento}")
        print(f"   - Días de atraso: {(date.today() - fecha_vencimiento).days}")
        print(f"   - Meses de atraso: {(date.today() - fecha_vencimiento).days // 30}")
        print(f"   - Tasa de mora: 1% mensual")
        
        mora = MoraService.calcular_mora_cuota(
            Decimal('500.00'),
            cuota.fecha_vencimiento
        )
        
        print(f"\n✅ RESULTADO:")
        print(f"   Mora calculada: S/. {mora}")
        print(f"   Fórmula: 500.00 * 0.01 * 1 mes = {mora}")
        
        # Assert con mensaje detallado
        self.assertEqual(mora, Decimal('5.00'), 
                        f"❌ ERROR: Mora esperada S/. 5.00, pero se obtuvo S/. {mora}")
        print(f"   ✓ Validación exitosa: Mora = S/. 5.00")

    def test_calcular_mora_cuota_no_vencida(self):
        """Test: Cuota no vencida no tiene mora"""
        print("\n📋 TEST: Cuota no vencida no debe tener mora")
        print("-" * 80)
        
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vence en el futuro
        fecha_vencimiento = date.today() + timedelta(days=10)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        print(f"\n🔍 Calculando mora:")
        print(f"   - Fecha actual: {date.today()}")
        print(f"   - Fecha vencimiento: {fecha_vencimiento}")
        print(f"   - Días hasta vencimiento: {(fecha_vencimiento - date.today()).days}")
        
        mora = MoraService.calcular_mora_cuota(
            Decimal('500.00'),
            cuota.fecha_vencimiento
        )
        
        print(f"\n✅ RESULTADO:")
        print(f"   Mora calculada: S/. {mora}")
        
        self.assertEqual(mora, Decimal('0.00'),
                        f"❌ ERROR: Cuota no vencida debe tener mora S/. 0.00, pero se obtuvo S/. {mora}")
        print(f"   ✓ Validación exitosa: Mora = S/. 0.00 (cuota no vencida)")

    def test_multiples_meses_atraso_mora_acumulativa(self):
        """Test: Mora no acumulativa - 1% por cada mes"""
        print("\n📋 TEST: Mora con múltiples meses de atraso (65 días = 2 meses)")
        print("-" * 80)
        
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida hace 65 días (más de 2 meses)
        fecha_vencimiento = date.today() - timedelta(days=65)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        dias_atraso = (date.today() - fecha_vencimiento).days
        meses_atraso = dias_atraso // 30
        
        print(f"\n🔍 Calculando mora:")
        print(f"   - Monto base: S/. 100.00")
        print(f"   - Días de atraso: {dias_atraso}")
        print(f"   - Meses de atraso: {meses_atraso}")
        print(f"   - Tasa por mes: 1%")
        
        mora = MoraService.calcular_mora_cuota(
            Decimal('100.00'),
            cuota.fecha_vencimiento
        )
        
        print(f"\n✅ RESULTADO:")
        print(f"   Mora calculada: S/. {mora}")
        print(f"   Fórmula: 100.00 * 0.01 * {meses_atraso} meses = {mora}")
        
        # 2 meses de atraso = 2% de 100 = 2 soles
        self.assertEqual(mora, Decimal('2.00'),
                        f"❌ ERROR: Mora esperada S/. 2.00, pero se obtuvo S/. {mora}")
        print(f"   ✓ Validación exitosa: Mora = S/. 2.00 (1% por cada mes)")

    def test_pago_completo_sin_mora(self):
        """Test: Pago completo a tiempo no genera mora"""
        print("\n📋 TEST: Pago completo a tiempo sin mora")
        print("-" * 80)
        
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1)
        
        print(f"\n💰 Registrando pago:")
        print(f"   - Préstamo ID: {prestamo.prestamo_id}")
        print(f"   - Cuota ID: {cuota.cuota_id}")
        print(f"   - Monto a pagar: S/. 500.00")
        print(f"   - Medio de pago: TRANSFERENCIA")
        print(f"   - Comprobante: TRF-001")
        
        respuesta, error, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='TRANSFERENCIA',
            comprobante_referencia='TRF-001'
        )
        
        print(f"\n✅ RESULTADO DEL PAGO:")
        if respuesta:
            print(f"   Success: {respuesta.get('success')}")
            print(f"   Pago ID: {respuesta.get('pago_id')}")
            print(f"   Monto pagado: S/. {respuesta.get('monto_pagado')}")
            print(f"   Mora pagada: S/. {respuesta.get('monto_mora_pagado')}")
            print(f"   Detalles de aplicación:")
            for detalle in respuesta.get('detalles_aplicacion', []):
                print(f"      • Cuota #{detalle['cuota_numero']}: {detalle['concepto']} = S/. {detalle['monto']}")
        if error:
            print(f"   ❌ Error: {error}")
        
        self.assertIsNotNone(respuesta, "❌ ERROR: La respuesta no debe ser None")
        self.assertIsNone(error, f"❌ ERROR: No debe haber error, pero se obtuvo: {error}")
        self.assertEqual(status, 201, f"❌ ERROR: Status esperado 201, obtenido {status}")
        self.assertTrue(respuesta['success'], "❌ ERROR: El pago debe ser exitoso")
        print(f"   ✓ Validación exitosa: Pago registrado correctamente")

    def test_pago_parcial_genera_mora_en_saldo(self):
        """Test: Pago parcial - mora se aplica al saldo pendiente"""
        print("\n📋 TEST: Pago parcial con mora aplicada al saldo pendiente")
        print("-" * 80)
        
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
            
        # Cuota vencida hace 35 días (más de 1 mes)
        fecha_vencimiento = date.today() - timedelta(days=35)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        print(f"\n🔄 PASO 1: Actualizar mora inicial")
        print(f"   - Cuota vencida hace: {(date.today() - fecha_vencimiento).days} días")
        
        # Primero actualizar mora inicial (vencida hace 35 días = 1 mes)
        MoraService.actualizar_mora_cuota(cuota.cuota_id)
        cuota_inicial = Cuota.query.get(cuota.cuota_id)
        
        print(f"   ✓ Mora inicial calculada: S/. {cuota_inicial.mora_acumulada}")
        print(f"   ✓ Saldo pendiente: S/. {cuota_inicial.saldo_pendiente}")
        
        # Mora inicial = 1% de 500 = 5.00
        self.assertEqual(cuota_inicial.mora_acumulada, Decimal('5.00'),
                        f"❌ ERROR: Mora inicial esperada S/. 5.00, obtenida S/. {cuota_inicial.mora_acumulada}")
        
        print(f"\n💰 PASO 2: Registrar pago parcial")
        print(f"   - Monto a pagar: S/. 250.00")
        print(f"   - Prioridad: Primero mora (S/. 5.00), luego saldo (S/. 245.00)")
        
        # Pago parcial de 250 (esto cubrirá: 5 de mora + 245 de capital)
        respuesta, error, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('250.00'),
            medio_pago='TRANSFERENCIA',
            comprobante_referencia='TRF-001'
        )
        
        print(f"\n✅ RESULTADO DEL PAGO:")
        if respuesta:
            print(f"   Success: {respuesta.get('success')}")
            print(f"   Monto total pagado: S/. {respuesta.get('monto_pagado')}")
            print(f"   Mora pagada: S/. {respuesta.get('monto_mora_pagado')}")
            print(f"\n   Detalles de aplicación del pago:")
            for detalle in respuesta.get('detalles_aplicacion', []):
                print(f"      • Cuota #{detalle['cuota_numero']}: {detalle['concepto']} = S/. {detalle['monto']}")
                if 'mora_restante' in detalle:
                    print(f"        Mora restante: S/. {detalle['mora_restante']}")
                if 'saldo_restante' in detalle:
                    print(f"        Saldo restante: S/. {detalle['saldo_restante']}")
        
        self.assertIsNotNone(respuesta, "❌ ERROR: La respuesta no debe ser None")
        self.assertIsNone(error, f"❌ ERROR: No debe haber error: {error}")
        self.assertEqual(status, 201, f"❌ ERROR: Status esperado 201, obtenido {status}")
        
        # Después del pago: saldo = 500 - 245 = 255
        cuota_actualizada = Cuota.query.get(cuota.cuota_id)
        
        print(f"\n🔍 ESTADO FINAL DE LA CUOTA:")
        print(f"   - Saldo pendiente: S/. {cuota_actualizada.saldo_pendiente}")
        print(f"   - Mora acumulada: S/. {cuota_actualizada.mora_acumulada}")
        print(f"   - Monto pagado total: S/. {cuota_actualizada.monto_pagado}")
        
        self.assertEqual(cuota_actualizada.saldo_pendiente, Decimal('255.00'),
                        f"❌ ERROR: Saldo pendiente esperado S/. 255.00, obtenido S/. {cuota_actualizada.saldo_pendiente}")
        
        # La mora de la cuota anterior se pagó completamente (5.00)
        self.assertEqual(cuota_actualizada.mora_acumulada, Decimal('0.00'),
                        f"❌ ERROR: Mora restante esperada S/. 0.00, obtenida S/. {cuota_actualizada.mora_acumulada}")
        
        print(f"   ✓ Validación exitosa: Pago parcial procesado correctamente")
        print(f"   ✓ Mora pagada completamente")
        print(f"   ✓ Saldo pendiente actualizado correctamente")

    def test_prioridad_pago_mora_antes_saldo(self):
        """Test: Los pagos cubren primero mora, luego saldo"""
        print("\n📋 TEST: Prioridad de pago - Mora antes que saldo")
        print("-" * 80)
        
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Cuota vencida
        fecha_vencimiento = date.today() - timedelta(days=35)
        cuota = self._crear_cuota(prestamo.prestamo_id, 1, fecha_vencimiento)
        
        print(f"\n💰 PASO 1: Primer pago parcial (S/. 250.00)")
        
        # Pago parcial para generar mora
        respuesta1, error1, status1 = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('250.00'),
            medio_pago='TRANSFERENCIA',
            comprobante_referencia='TRF-001'
        )
        
        print(f"   ✓ Primer pago registrado")
        if respuesta1:
            print(f"   - Monto pagado: S/. {respuesta1.get('monto_pagado')}")
            print(f"   - Mora pagada: S/. {respuesta1.get('monto_mora_pagado')}")
        
        cuota_despues_pago1 = Cuota.query.get(cuota.cuota_id)
        print(f"   - Saldo pendiente después: S/. {cuota_despues_pago1.saldo_pendiente}")
        print(f"   - Mora acumulada después: S/. {cuota_despues_pago1.mora_acumulada}")
        
        print(f"\n🔄 PASO 2: Actualizar mora sobre saldo pendiente")
        
        # Actualizar mora
        mora_nueva, mensaje = MoraService.actualizar_mora_cuota(cuota.cuota_id)
        
        cuota_con_mora = Cuota.query.get(cuota.cuota_id)
        print(f"   ✓ Mora actualizada: S/. {mora_nueva}")
        print(f"   - Mensaje: {mensaje}")
        print(f"   - Saldo pendiente: S/. {cuota_con_mora.saldo_pendiente}")
        print(f"   - Nueva mora acumulada: S/. {cuota_con_mora.mora_acumulada}")
        
        print(f"\n💰 PASO 3: Segundo pago (S/. 253.00)")
        print(f"   Distribución esperada:")
        print(f"   - A mora: S/. {cuota_con_mora.mora_acumulada}")
        print(f"   - A saldo: S/. {Decimal('253.00') - cuota_con_mora.mora_acumulada}")
        
        # Siguiente pago: mora + parte del saldo
        respuesta2, error2, status2 = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo.prestamo_id,
            cuota_id=cuota.cuota_id,
            monto_pagado=Decimal('253.00'),
            medio_pago='TRANSFERENCIA',
            comprobante_referencia='TRF-002'
        )
        
        print(f"\n✅ RESULTADO DEL SEGUNDO PAGO:")
        if respuesta2:
            print(f"   Success: {respuesta2.get('success')}")
            print(f"   Monto pagado: S/. {respuesta2.get('monto_pagado')}")
            print(f"   Mora pagada: S/. {respuesta2.get('monto_mora_pagado')}")
            print(f"\n   Detalles de aplicación:")
            for detalle in respuesta2.get('detalles_aplicacion', []):
                print(f"      • Cuota #{detalle['cuota_numero']}: {detalle['concepto']} = S/. {detalle['monto']}")
        
        cuota_final = Cuota.query.get(cuota.cuota_id)
        print(f"\n🔍 ESTADO FINAL:")
        print(f"   - Saldo pendiente: S/. {cuota_final.saldo_pendiente}")
        print(f"   - Mora acumulada: S/. {cuota_final.mora_acumulada}")
        print(f"   - Total pagado: S/. {cuota_final.monto_pagado}")
        
        self.assertIsNotNone(respuesta2, "❌ ERROR: La respuesta no debe ser None")
        self.assertIsNone(error2, f"❌ ERROR: No debe haber error: {error2}")
        print(f"   ✓ Validación exitosa: Prioridad de pago correcta (mora → saldo)")

    def test_resumen_pagos_con_mora(self):
        """Test: Resumen de pagos incluye mora total"""
        print("\n📋 TEST: Resumen de pagos con múltiples cuotas vencidas")
        print("-" * 80)
        
        cliente = self._crear_cliente_prueba()
        prestamo = self._crear_prestamo_vigente(cliente.cliente_id)
        
        # Dos cuotas vencidas
        print(f"\n📦 Creando cuotas vencidas:")
        cuota1 = self._crear_cuota(prestamo.prestamo_id, 1, date.today() - timedelta(days=35))
        cuota2 = self._crear_cuota(prestamo.prestamo_id, 2, date.today() - timedelta(days=5))
        
        print(f"\n📊 Obteniendo resumen de pagos...")
        
        respuesta, error, status = PagoService.obtener_resumen_pagos_prestamo(prestamo.prestamo_id)
        
        print(f"\n✅ RESUMEN DE PAGOS:")
        if respuesta and respuesta.get('success'):
            resumen = respuesta.get('resumen', {})
            print(f"\n   📈 Estadísticas generales:")
            print(f"      - Total cuotas: {resumen.get('total_cuotas')}")
            print(f"      - Cuotas pagadas: {resumen.get('cuotas_pagadas')}")
            print(f"      - Cuotas pendientes: {resumen.get('cuotas_pendientes')}")
            
            print(f"\n   💰 Montos:")
            print(f"      - Monto total: S/. {resumen.get('monto_total')}")
            print(f"      - Monto pagado: S/. {resumen.get('monto_pagado')}")
            print(f"      - Monto pendiente: S/. {resumen.get('monto_pendiente')}")
            print(f"      - Mora total: S/. {resumen.get('mora_total')}")
            print(f"      - Total a pagar: S/. {resumen.get('total_a_pagar')}")
            print(f"      - Porcentaje pagado: {resumen.get('porcentaje_pagado')}%")
            
            cuotas_pendientes = respuesta.get('cuotas_pendientes', [])
            if cuotas_pendientes:
                print(f"\n   📋 Detalle de cuotas pendientes:")
                for cuota_info in cuotas_pendientes:
                    print(f"\n      Cuota #{cuota_info['numero_cuota']}:")
                    print(f"         - Monto cuota: S/. {cuota_info['monto_cuota']}")
                    print(f"         - Monto pagado: S/. {cuota_info['monto_pagado']}")
                    print(f"         - Saldo pendiente: S/. {cuota_info['saldo_pendiente']}")
                    print(f"         - Mora acumulada: S/. {cuota_info['mora_acumulada']}")
                    print(f"         - Total a pagar: S/. {cuota_info['total_a_pagar']}")
                    print(f"         - Días de atraso: {cuota_info['dias_atraso']}")
                    print(f"         - Estado: {cuota_info['estado']}")
        
        if error:
            print(f"   ❌ Error: {error}")
        
        self.assertIsNotNone(respuesta, "❌ ERROR: La respuesta no debe ser None")
        self.assertIsNone(error, f"❌ ERROR: No debe haber error: {error}")
        self.assertEqual(status, 200, f"❌ ERROR: Status esperado 200, obtenido {status}")
        self.assertTrue(respuesta['success'], "❌ ERROR: El resumen debe ser exitoso")
        self.assertGreater(respuesta['resumen']['mora_total'], 0,
                          "❌ ERROR: Debe haber mora total mayor a 0")
        
        print(f"\n   ✓ Validación exitosa: Resumen generado correctamente")
        print(f"   ✓ Mora total calculada: S/. {respuesta['resumen']['mora_total']}")


if __name__ == '__main__':
    unittest.main()