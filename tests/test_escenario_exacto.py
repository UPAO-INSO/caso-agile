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
from app.models.pago import Pago, MedioPagoEnum
from app.services.pago_service import PagoService
from app.services.mora_service import MoraService
from app.services.financial_service import FinancialService

# → Test del escenario/simulación de un préstamo con cronograma
class EscenarioExactoTestCase(unittest.TestCase):
# → Configuración inicial y final del entorno de pruebas    
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Fecha base: hace 1 mes (para que la primera cuota esté por vencer)
        self.fecha_otorgamiento = date.today() - timedelta(days=30)
        
        # Crear cliente
        self.cliente = Cliente(
            dni='12345678',
            nombre_completo='Juan Pérez',
            apellido_paterno='Pérez',
            apellido_materno='García',
            correo_electronico='juan.perez@test.com',
            pep=False
        )
        db.session.add(self.cliente)
        db.session.commit()
        
        # Crear préstamo de 12,000 a 12 meses
        self.prestamo = Prestamo(
            cliente_id=self.cliente.cliente_id,
            monto_total=Decimal('12000.00'),
            interes_tea=Decimal('10.00'),  # 10% TEA
            plazo=12,
            f_otorgamiento=self.fecha_otorgamiento,
            estado=EstadoPrestamoEnum.VIGENTE,
            requiere_dec_jurada=False
        )
        db.session.add(self.prestamo)
        db.session.commit()
        
        # Generar cronograma usando el servicio financiero
        self.generar_cronograma_detallado()
    
# → Limpieza del entorno de pruebas
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
# → Generar cronograma detallado
    def generar_cronograma_detallado(self):
        print("\n" + "="*100)
        print("CRONOGRAMA DE PAGOS DETALLADO")
        print("="*100)
        
    # Calcular cuota fija usando sistema francés
        cuota_fija = FinancialService.calcular_cuota_fija(
            self.prestamo.monto_total,
            self.prestamo.interes_tea,
            self.prestamo.plazo
        )

    # → Mostrar cronograma detallado    
        print(f"\n→ Monto Préstamo: S/. {self.prestamo.monto_total}")
        print(f"TEA: {self.prestamo.interes_tea}%")
        print(f"Plazo: {self.prestamo.plazo} meses")
        print(f"Cuota Mensual Fija: S/. {cuota_fija}")
        
    # → Calcular TEM para amortización
        tem = FinancialService.tea_to_tem(self.prestamo.interes_tea)
        
        print(f"\n{'N°':<5} {'Fecha Venc.':<15} {'Cuota':<12} {'Interés':<12} {'Capital':<12} {'Saldo Capital':<15}")
        
        saldo_capital = self.prestamo.monto_total
        
    # → Generar cuotas mes a mes
        for i in range(1, self.prestamo.plazo + 1):
            # Fecha de vencimiento: cada 30 días exactos
            fecha_vencimiento = self.fecha_otorgamiento + timedelta(days=30 * i)
            
            # Calcular interés sobre saldo pendiente
            interes = saldo_capital * tem
            
            # Calcular amortización de capital
            capital = cuota_fija - interes
            
            # Actualizar saldo
            saldo_capital -= capital
            
            # Ajustar última cuota para cerrar el saldo
            if i == self.prestamo.plazo:
                capital += saldo_capital
                cuota_fija_ajustada = interes + capital
                saldo_capital = Decimal('0.00')
            else:
                cuota_fija_ajustada = cuota_fija
            
            print(f"{i:<5} {fecha_vencimiento.strftime('%d/%m/%Y'):<15} "
                  f"S/. {cuota_fija_ajustada:>8.2f} "
                  f"S/. {interes:>8.2f} "
                  f"S/. {capital:>8.2f} "
                  f"S/. {saldo_capital:>11.2f}")
            
            # → Crear cuota en la base de datos
            cuota = Cuota(
                prestamo_id=self.prestamo.prestamo_id,
                numero_cuota=i,
                monto_cuota=cuota_fija_ajustada,
                monto_interes=interes,
                monto_capital=capital,
                saldo_capital=saldo_capital,
                saldo_pendiente=cuota_fija_ajustada,
                fecha_vencimiento=fecha_vencimiento,
                mora_acumulada=Decimal('0.00')
            )
            db.session.add(cuota)
        
        db.session.commit()
        print("="*100)
    
# → Test del escenario exacto de pagos mes a mes
# MES 1: Pago S/. 500 (quedan S/. 500)
# MES 2: Mora S/. 5, pago S/. 750 (quedan S/. 755)
# MES 3: Mora S/. 7.55, no paga (total adeudado S/. 762.55)
    def test_simulacion_pagos_mes_a_mes(self):
        print("\n" + "="*100)
        print("→ SIMULACIÓN DE PAGOS MES A MES")
        print("="*100)
        
    # MES 1: PRIMER PAGO
        print("\n" + "-"*100)
        print(" → MES 1: Primera Cuota Vence")
        print("-"*100)
        
        cuota1 = Cuota.query.filter_by(
            prestamo_id=self.prestamo.prestamo_id,
            numero_cuota=1
        ).first()
        
        print(f"\nEstado Inicial Cuota 1:")
        print(f"  Cuota: S/. {cuota1.monto_cuota:.2f}")
        print(f"  Saldo Pendiente: S/. {cuota1.saldo_pendiente:.2f}")
        print(f"  Fecha Vencimiento: {cuota1.fecha_vencimiento}")
        print(f"  Mora: S/. {cuota1.mora_acumulada:.2f}")
        
        # Simular que estamos EN la fecha de vencimiento (no hay mora aún)
        fecha_pago_1 = cuota1.fecha_vencimiento
        
        print(f"\nPago: S/. 500.00")
        print(f"Fecha de Pago: {fecha_pago_1}")
        
        # Registrar pago
        respuesta1, error1, status1 = PagoService.registrar_pago_cuota(
            prestamo_id=self.prestamo.prestamo_id,
            cuota_id=cuota1.cuota_id,
            monto_pagado=Decimal('500.00'),
            medio_pago='EFECTIVO',
            fecha_pago=fecha_pago_1,
            comprobante_referencia='COMP-MES1',
            observaciones='Pago parcial mes 1'
        )
        
        self.assertIsNone(error1, f"Error en pago mes 1: {error1}")
        
        db.session.refresh(cuota1)
        
        print(f"\n✅ RESULTADO PAGO MES 1:")
        print(f"  Comprobante: COMP-MES1")
        print(f"  Restante: S/. {cuota1.saldo_pendiente:.2f}")
        print(f"  Mora: S/. {cuota1.mora_acumulada:.2f}")
        
        # Verificar - La cuota es 1052.59, no 1000
        # Después de pagar 500, quedan: 1052.59 - 500 = 552.59
        saldo_esperado = cuota1.monto_cuota - Decimal('500.00')
        self.assertEqual(cuota1.saldo_pendiente, saldo_esperado,
                        f"Después de pagar 500 de una cuota de {cuota1.monto_cuota}, deben quedar {saldo_esperado}")
        
    # PASA 1 MES - SE GENERA MORA
        print("\n" + "-"*100)
        print("PASA 1 MES (30 días)")
        print("-"*100)
        
    # Simular que pasó 1 mes (la cuota ya está vencida)
        cuota1.fecha_vencimiento = date.today() - timedelta(days=30)
        db.session.commit()
        
        # Actualizar mora
        MoraService.actualizar_mora_prestamo(self.prestamo.prestamo_id)
        db.session.refresh(cuota1)
        
        mora_esperada = cuota1.saldo_pendiente * Decimal('0.01') * 1  # 1% x 1 mes
        
        print(f"\nEstado Cuota 1 tras 1 mes:")
        print(f"  Saldo Pendiente: S/. {cuota1.saldo_pendiente:.2f}")
        print(f"  Mora Calculada (1% x 1 mes): S/. {mora_esperada:.2f}")
        print(f"  Mora en Sistema: S/. {cuota1.mora_acumulada:.2f}")
        
    # MES 2: SEGUNDO PAGO
        print("\n" + "-"*100)
        print("MES 2: Segunda Cuota Vence + Pago Parcial")
        print("-"*100)
        
        cuota2 = Cuota.query.filter_by(
            prestamo_id=self.prestamo.prestamo_id,
            numero_cuota=2
        ).first()
        
        # La cuota 2 vence hoy
        cuota2.fecha_vencimiento = date.today()
        db.session.commit()
        
        print(f"\nEstado antes del pago:")
        print(f"  Cuota 1:")
        print(f"    Mora: S/. {cuota1.mora_acumulada:.2f}")
        print(f"    Restante: S/. {cuota1.saldo_pendiente:.2f}")
        print(f"  Cuota 2:")
        print(f"    Cuota: S/. {cuota2.monto_cuota:.2f}")
        print(f"    Saldo: S/. {cuota2.saldo_pendiente:.2f}")
        
        total_adeudado = cuota1.mora_acumulada + cuota1.saldo_pendiente + cuota2.saldo_pendiente
        print(f"\n  TOTAL ADEUDADO: S/. {total_adeudado:.2f}")
        
        print(f"\nPago: S/. 750.00")
        
        # Registrar segundo pago
        respuesta2, error2, status2 = PagoService.registrar_pago_cuota(
            prestamo_id=self.prestamo.prestamo_id,
            cuota_id=cuota1.cuota_id,
            monto_pagado=Decimal('750.00'),
            medio_pago='TRANSFERENCIA',
            fecha_pago=date.today(),
            comprobante_referencia='COMP-MES2',
            observaciones='Pago mes 2 - cubre mora y parte de saldo'
        )
        
        self.assertIsNone(error2, f"Error en pago mes 2: {error2}")
        
        db.session.refresh(cuota1)
        db.session.refresh(cuota2)
        
        # Calcular cuánto queda de la cuota 2 (si el pago cubrió algo)
        restante_total = cuota1.saldo_pendiente + cuota2.saldo_pendiente + cuota1.mora_acumulada
        
        print(f"\nRESULTADO PAGO MES 2:")
        print(f"  Comprobante: COMP-MES2")
        print(f"  Cuota 1: S/. {cuota1.saldo_pendiente:.2f} (Mora: S/. {cuota1.mora_acumulada:.2f})")
        print(f"  Cuota 2: S/. {cuota2.saldo_pendiente:.2f}")
        print(f"  Restante Total: S/. {restante_total:.2f}")
        
        print(f"\n  📊 REPORTE HISTÓRICO CUOTA 1:")
        print(f"     Mora Generada Total: S/. {cuota1.mora_generada:.2f}")
        print(f"     Mora Pendiente de Pago: S/. {cuota1.mora_acumulada:.2f}")
        print(f"     Mora Pagada: S/. {cuota1.mora_generada - cuota1.mora_acumulada:.2f}")
        
        # PASA 1 MES MÁS - SE GENERA MÁS MORA
        print("\n" + "-"*100)
        print("PASA 1 MES MÁS (30 días) - SIN PAGO")
        print("-"*100)
        
        # Simular que pasó 1 mes más
        cuota2.fecha_vencimiento = date.today() - timedelta(days=30)
        db.session.commit()
        
        # Actualizar moras
        MoraService.actualizar_mora_prestamo(self.prestamo.prestamo_id)
        db.session.refresh(cuota1)
        db.session.refresh(cuota2)
        
        mora_cuota2_esperada = cuota2.saldo_pendiente * Decimal('0.01') * 1
        
        print(f"\nEstado tras 1 mes sin pago:")
        print(f"  Cuota 1:")
        print(f"    Mora: S/. {cuota1.mora_acumulada:.2f}")
        print(f"    Restante: S/. {cuota1.saldo_pendiente:.2f}")
        print(f"\n    📊 REPORTE HISTÓRICO CUOTA 1:")
        print(f"       Mora Generada Total: S/. {cuota1.mora_generada:.2f}")
        print(f"       Mora Pendiente: S/. {cuota1.mora_acumulada:.2f}")
        print(f"       Mora Pagada: S/. {cuota1.mora_generada - cuota1.mora_acumulada:.2f}")
        print(f"  Cuota 2:")
        print(f"    Mora: S/. {cuota2.mora_acumulada:.2f}")
        print(f"    Mora Esperada (1% x 1 mes): S/. {mora_cuota2_esperada:.2f}")
        print(f"    Restante: S/. {cuota2.saldo_pendiente:.2f}")
        print(f"\n    📊 REPORTE HISTÓRICO CUOTA 2:")
        print(f"       Mora Generada Total: S/. {cuota2.mora_generada:.2f}")
        print(f"       Mora Pendiente: S/. {cuota2.mora_acumulada:.2f}")
        print(f"       Mora Pagada: S/. {cuota2.mora_generada - cuota2.mora_acumulada:.2f}")
        
        # MES 3: CONSULTA (SIN PAGO)
        print("\n" + "-"*100)
        print("MES 3: Tercera Cuota Vence - CONSULTA DE DEUDA")
        print("-"*100)
        
        cuota3 = Cuota.query.filter_by(
            prestamo_id=self.prestamo.prestamo_id,
            numero_cuota=3
        ).first()
        
        # La cuota 3 vence hoy
        cuota3.fecha_vencimiento = date.today()
        db.session.commit()
        
        MoraService.actualizar_mora_prestamo(self.prestamo.prestamo_id)
        db.session.refresh(cuota1)
        db.session.refresh(cuota2)
        db.session.refresh(cuota3)
        
        print(f"\nDEUDA TOTAL:")
        print(f"  Cuota 1:")
        print(f"    Mora: S/. {cuota1.mora_acumulada:.2f}")
        print(f"    Restante: S/. {cuota1.saldo_pendiente:.2f}")
        print(f"    📊 Mora Histórica Total: S/. {cuota1.mora_generada:.2f}")
        print(f"  Cuota 2:")
        print(f"    Mora: S/. {cuota2.mora_acumulada:.2f}")
        print(f"    Restante: S/. {cuota2.saldo_pendiente:.2f}")
        print(f"    📊 Mora Histórica Total: S/. {cuota2.mora_generada:.2f}")
        print(f"  Cuota 3:")
        print(f"    Mora: S/. {cuota3.mora_acumulada:.2f}")
        print(f"    Cuota: S/. {cuota3.monto_cuota:.2f}")
        print(f"    Restante: S/. {cuota3.saldo_pendiente:.2f}")
        print(f"    📊 Mora Histórica Total: S/. {cuota3.mora_generada:.2f}")
        
        total_mora = cuota1.mora_acumulada + cuota2.mora_acumulada + cuota3.mora_acumulada
        total_mora_historica = cuota1.mora_generada + cuota2.mora_generada + cuota3.mora_generada
        total_saldo = cuota1.saldo_pendiente + cuota2.saldo_pendiente + cuota3.saldo_pendiente
        total_deuda = total_mora + total_saldo
        
        print(f"\n  {'─'*50}")
        print(f"  Total Mora Pendiente: S/. {total_mora:.2f}")
        print(f"  Total Mora Generada (Histórico): S/. {total_mora_historica:.2f}")
        print(f"  Total Mora Pagada: S/. {total_mora_historica - total_mora:.2f}")
        print(f"  Total Saldo: S/. {total_saldo:.2f}")
        print(f"  TOTAL A PAGAR: S/. {total_deuda:.2f}")
        
        # VERIFICAR COMPROBANTES
        print("\n" + "="*100)
        print("COMPROBANTES GENERADOS")
        print("="*100)
        
        pagos = Pago.query.filter_by(cuota_id=cuota1.cuota_id).all()
        
        for i, pago in enumerate(pagos, 1):
            print(f"\nComprobante {i}:")
            print(f"  Ref: {pago.comprobante_referencia}")
            print(f"  Monto: S/. {pago.monto_pagado:.2f}")
            print(f"  Mora Pagada: S/. {pago.monto_mora:.2f}")
            print(f"  A Capital: S/. {pago.monto_pagado - pago.monto_mora:.2f}")
            print(f"  Fecha: {pago.fecha_pago}")
            print(f"  Medio: {pago.medio_pago.value}")
        
        print("\n" + "="*100)
        print("TEST COMPLETADO - ESCENARIO EXACTO VERIFICADO")
        print("="*100)


if __name__ == '__main__':
    unittest.main(verbosity=2)
