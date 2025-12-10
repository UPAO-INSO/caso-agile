"""
Script Interactivo para Simular Pagos
=====================================

Permite:
1. Crear un cliente de prueba (no PEP)
2. Crear un préstamo con parámetros personalizados
3. Ver el cronograma de cuotas
4. Registrar pagos a cuotas específicas

Ejecutar con:
    python simular_pagos.py
    
    O con Docker:
    docker-compose exec -it web python simular_pagos.py
"""

import sys
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation

from app import create_app
from app.common.extensions import db
from app.models import Cliente, Prestamo, Cuota, Pago, MedioPagoEnum, EstadoPrestamoEnum
from app.services.prestamo_service import PrestamoService
from app.services.pago_service import PagoService
from app.services.mora_service import MoraService


# ==================== UTILIDADES ====================

def limpiar_pantalla():
    print("\n" * 2)


def print_header(titulo):
    print("\n" + "=" * 70)
    print(f"  {titulo}")
    print("=" * 70)


def print_separator():
    print("-" * 70)


def input_decimal(mensaje, default=None):
    """Solicita un número decimal al usuario"""
    while True:
        try:
            valor = input(mensaje).strip()
            if not valor and default is not None:
                return Decimal(str(default))
            return Decimal(valor)
        except InvalidOperation:
            print("   ❌ Por favor ingresa un número válido")


def input_int(mensaje, default=None):
    """Solicita un número entero al usuario"""
    while True:
        try:
            valor = input(mensaje).strip()
            if not valor and default is not None:
                return default
            return int(valor)
        except ValueError:
            print("   ❌ Por favor ingresa un número entero válido")


def input_fecha(mensaje, default=None):
    """Solicita una fecha al usuario (formato: YYYY-MM-DD o DD/MM/YYYY)"""
    while True:
        valor = input(mensaje).strip()
        if not valor and default is not None:
            return default
        
        # Intentar varios formatos
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(valor, fmt).date()
            except ValueError:
                continue
        
        print("   ❌ Formato inválido. Usa: YYYY-MM-DD o DD/MM/YYYY")


def input_opcion(mensaje, opciones):
    """Solicita una opción de una lista"""
    while True:
        valor = input(mensaje).strip().upper()
        if valor in opciones:
            return valor
        print(f"   ❌ Opción inválida. Opciones: {', '.join(opciones)}")


# ==================== FUNCIONES PRINCIPALES ====================

def crear_cliente_prueba(app_context):
    """Crea un cliente de prueba no PEP"""
    print_header("CREAR CLIENTE DE PRUEBA")
    
    # Generar DNI único para pruebas
    timestamp = datetime.now().strftime("%H%M%S")
    dni_prueba = f"99{timestamp}"
    
    print(f"\n📝 Datos del cliente de prueba:")
    print(f"   DNI: {dni_prueba} (generado automáticamente)")
    
    correo = input("   Correo electrónico [test@prueba.com]: ").strip()
    if not correo:
        correo = "test@prueba.com"
    
    # Verificar si ya existe
    cliente_existente = Cliente.query.filter_by(dni=dni_prueba).first()
    if cliente_existente:
        print(f"\n   ⚠️ Cliente con DNI {dni_prueba} ya existe")
        return cliente_existente
    
    # Crear cliente manualmente (sin consultar RENIEC)
    try:
        nuevo_cliente = Cliente(
            dni=dni_prueba,
            nombre_completo=f"CLIENTE PRUEBA {timestamp}",
            apellido_paterno="PRUEBA",
            apellido_materno="TEST",
            correo_electronico=correo,
            pep=False  # No PEP
        )
        
        db.session.add(nuevo_cliente)
        db.session.commit()
        
        print(f"\n   ✅ Cliente creado exitosamente:")
        print(f"      ID: {nuevo_cliente.cliente_id}")
        print(f"      DNI: {nuevo_cliente.dni}")
        print(f"      Nombre: {nuevo_cliente.nombre_completo}")
        print(f"      PEP: No")
        
        return nuevo_cliente
        
    except Exception as e:
        db.session.rollback()
        print(f"\n   ❌ Error al crear cliente: {e}")
        return None


def crear_prestamo_personalizado(cliente):
    """Crea un préstamo con parámetros personalizados"""
    print_header("CREAR PRÉSTAMO")
    
    print(f"\n📋 Cliente: {cliente.nombre_completo} (DNI: {cliente.dni})")
    print("\n   Ingresa los datos del préstamo:")
    
    monto = input_decimal("   Monto del préstamo [10000]: ", 10000)
    tea = input_decimal("   TEA en % [10]: ", 10)
    plazo = input_int("   Número de cuotas [12]: ", 12)
    
    print(f"\n   Fecha de otorgamiento:")
    print(f"   (Presiona Enter para usar fecha actual: {date.today()})")
    fecha_otorgamiento = input_fecha("   Fecha [hoy]: ", date.today())
    
    print(f"\n📊 Resumen del préstamo:")
    print(f"   • Monto: S/ {monto:,.2f}")
    print(f"   • TEA: {tea}%")
    print(f"   • Plazo: {plazo} cuotas")
    print(f"   • Fecha otorgamiento: {fecha_otorgamiento}")
    
    confirmar = input("\n   ¿Crear préstamo? (S/N) [S]: ").strip().upper()
    if confirmar == 'N':
        print("   ❌ Operación cancelada")
        return None
    
    try:
        respuesta, error, status = PrestamoService.registrar_prestamo_completo(
            dni=cliente.dni,
            correo_electronico=cliente.correo_electronico,
            monto_total=monto,
            interes_tea=tea,
            plazo=plazo,
            f_otorgamiento=fecha_otorgamiento
        )
        
        if error:
            print(f"\n   ❌ Error: {error}")
            return None
        
        prestamo_id = respuesta['prestamo']['prestamo_id']
        prestamo = Prestamo.query.get(prestamo_id)
        
        print(f"\n   ✅ Préstamo creado exitosamente!")
        print(f"      ID: {prestamo_id}")
        
        # Mostrar cronograma
        mostrar_cronograma(prestamo)
        
        return prestamo
        
    except Exception as e:
        print(f"\n   ❌ Error al crear préstamo: {e}")
        return None


def mostrar_cronograma(prestamo):
    """Muestra el cronograma de cuotas de un préstamo"""
    print_header(f"CRONOGRAMA DE CUOTAS - Préstamo #{prestamo.prestamo_id}")
    
    cuotas = Cuota.query.filter_by(prestamo_id=prestamo.prestamo_id).order_by(Cuota.numero_cuota).all()
    
    if not cuotas:
        print("\n   ⚠️ No hay cuotas para este préstamo")
        return
    
    # Actualizar moras
    MoraService.actualizar_mora_prestamo(prestamo.prestamo_id)
    db.session.refresh(prestamo)
    
    print(f"\n{'#':>3} | {'Vencimiento':>12} | {'Monto':>10} | {'Pagado':>10} | {'Pendiente':>10} | {'Mora':>8} | {'Estado':>10}")
    print_separator()
    
    total_pendiente = Decimal('0')
    total_mora = Decimal('0')
    
    for cuota in cuotas:
        # Determinar estado
        if cuota.saldo_pendiente <= 0:
            estado = "✅ PAGADA"
        elif cuota.fecha_vencimiento < date.today():
            estado = "⚠️ VENCIDA"
        else:
            estado = "⏳ Pendiente"
        
        mora = cuota.mora_acumulada or Decimal('0')
        pagado = cuota.monto_pagado or Decimal('0')
        
        print(
            f"{cuota.numero_cuota:>3} | "
            f"{cuota.fecha_vencimiento.strftime('%d/%m/%Y'):>12} | "
            f"S/{cuota.monto_cuota:>8.2f} | "
            f"S/{pagado:>8.2f} | "
            f"S/{cuota.saldo_pendiente:>8.2f} | "
            f"S/{mora:>6.2f} | "
            f"{estado:>10}"
        )
        
        total_pendiente += cuota.saldo_pendiente
        total_mora += mora
    
    print_separator()
    print(f"\n📊 Resumen:")
    print(f"   Total pendiente: S/ {total_pendiente:,.2f}")
    print(f"   Total mora:      S/ {total_mora:,.2f}")
    print(f"   TOTAL A PAGAR:   S/ {(total_pendiente + total_mora):,.2f}")


def registrar_pago_interactivo():
    """Registra un pago de forma interactiva"""
    print_header("REGISTRAR PAGO")
    
    # Listar préstamos vigentes
    prestamos = Prestamo.query.filter_by(estado=EstadoPrestamoEnum.VIGENTE).all()
    
    if not prestamos:
        print("\n   ⚠️ No hay préstamos vigentes")
        return
    
    print("\n📋 Préstamos vigentes:")
    for p in prestamos:
        print(f"   [{p.prestamo_id}] Cliente: {p.cliente.nombre_completo} - Monto: S/ {p.monto_total:,.2f}")
    
    prestamo_id = input_int("\n   ID del préstamo: ")
    
    prestamo = Prestamo.query.get(prestamo_id)
    if not prestamo:
        print(f"   ❌ Préstamo #{prestamo_id} no encontrado")
        return
    
    # Mostrar cuotas pendientes
    cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).filter(
        Cuota.saldo_pendiente > 0
    ).order_by(Cuota.numero_cuota).all()
    
    if not cuotas:
        print(f"\n   ✅ El préstamo #{prestamo_id} no tiene cuotas pendientes")
        return
    
    # Actualizar moras
    MoraService.actualizar_mora_prestamo(prestamo_id)
    
    print(f"\n📋 Cuotas pendientes del préstamo #{prestamo_id}:")
    print(f"\n{'#':>3} | {'ID Cuota':>8} | {'Vencimiento':>12} | {'Pendiente':>10} | {'Mora':>8} | {'Total':>10}")
    print_separator()
    
    for cuota in cuotas:
        mora = cuota.mora_acumulada or Decimal('0')
        total = cuota.saldo_pendiente + mora
        print(
            f"{cuota.numero_cuota:>3} | "
            f"{cuota.cuota_id:>8} | "
            f"{cuota.fecha_vencimiento.strftime('%d/%m/%Y'):>12} | "
            f"S/{cuota.saldo_pendiente:>8.2f} | "
            f"S/{mora:>6.2f} | "
            f"S/{total:>8.2f}"
        )
    
    # Solicitar datos del pago
    cuota_id = input_int("\n   ID de la cuota a pagar: ")
    
    cuota = Cuota.query.get(cuota_id)
    if not cuota or cuota.prestamo_id != prestamo_id:
        print(f"   ❌ Cuota #{cuota_id} no válida para este préstamo")
        return
    
    mora = cuota.mora_acumulada or Decimal('0')
    total_cuota = cuota.saldo_pendiente + mora
    
    print(f"\n   💰 Monto sugerido (cuota + mora): S/ {total_cuota:.2f}")
    monto = input_decimal(f"   Monto a pagar [S/ {total_cuota:.2f}]: ", total_cuota)
    
    # Método de pago
    print("\n   Métodos de pago disponibles:")
    print("   [1] EFECTIVO")
    print("   [2] TRANSFERENCIA")
    print("   [3] TARJETA")
    print("   [4] YAPE")
    print("   [5] PLIN")
    
    metodo_map = {
        '1': 'EFECTIVO',
        '2': 'TRANSFERENCIA',
        '3': 'TARJETA',
        '4': 'YAPE',
        '5': 'PLIN'
    }
    
    opcion_metodo = input_opcion("   Selecciona método [1-5]: ", ['1', '2', '3', '4', '5'])
    medio_pago = metodo_map[opcion_metodo]
    
    # Fecha del pago
    print(f"\n   Fecha del pago (Enter para hoy: {date.today()}):")
    fecha_pago = input_fecha("   Fecha: ", date.today())
    
    # Confirmar
    print(f"\n📊 Resumen del pago:")
    print(f"   • Préstamo: #{prestamo_id}")
    print(f"   • Cuota: #{cuota.numero_cuota} (ID: {cuota_id})")
    print(f"   • Monto: S/ {monto:,.2f}")
    print(f"   • Método: {medio_pago}")
    print(f"   • Fecha: {fecha_pago}")
    
    confirmar = input("\n   ¿Confirmar pago? (S/N) [S]: ").strip().upper()
    if confirmar == 'N':
        print("   ❌ Pago cancelado")
        return
    
    # Registrar el pago
    try:
        respuesta, error, status = PagoService.registrar_pago_cuota(
            prestamo_id=prestamo_id,
            cuota_id=cuota_id,
            monto_pagado=monto,
            medio_pago=medio_pago,
            fecha_pago=fecha_pago,
            comprobante_referencia=f"SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            observaciones="Pago simulado desde script de pruebas"
        )
        
        if error:
            print(f"\n   ❌ Error: {error}")
            return
        
        print(f"\n   ✅ Pago registrado exitosamente!")
        print(f"      ID Pago: {respuesta['pago_id']}")
        print(f"      Monto pagado: S/ {respuesta['monto_pagado']:,.2f}")
        print(f"      Mora pagada: S/ {respuesta['monto_mora_pagado']:,.2f}")
        
        # Mostrar info de redondeo si aplica
        if 'redondeo' in respuesta and respuesta['redondeo']['aplicado']:
            red = respuesta['redondeo']
            print(f"\n   💰 Redondeo aplicado (Ley N° 29571):")
            print(f"      Monto contable: S/ {red['monto_contable']:,.2f}")
            print(f"      Cliente pagó:   S/ {red['monto_pagado_cliente']:,.2f}")
            print(f"      Ahorro:         S/ {red['ahorro_cliente']:,.2f}")
        
        # Mostrar detalles de aplicación
        print(f"\n   📝 Detalle de aplicación:")
        for detalle in respuesta['detalles_aplicacion']:
            print(f"      Cuota {detalle['cuota_numero']}: {detalle['concepto']} - S/ {detalle['monto']:,.2f}")
        
    except Exception as e:
        print(f"\n   ❌ Error al registrar pago: {e}")


def listar_prestamos():
    """Lista todos los préstamos"""
    print_header("LISTA DE PRÉSTAMOS")
    
    prestamos = Prestamo.query.order_by(Prestamo.prestamo_id.desc()).all()
    
    if not prestamos:
        print("\n   ⚠️ No hay préstamos registrados")
        return
    
    print(f"\n{'ID':>4} | {'Cliente':>25} | {'Monto':>12} | {'TEA':>6} | {'Cuotas':>6} | {'Estado':>10}")
    print_separator()
    
    for p in prestamos:
        print(
            f"{p.prestamo_id:>4} | "
            f"{p.cliente.nombre_completo[:25]:>25} | "
            f"S/{p.monto_total:>10,.2f} | "
            f"{p.interes_tea:>5.1f}% | "
            f"{p.plazo:>6} | "
            f"{p.estado.value:>10}"
        )


def ver_detalle_prestamo():
    """Ver detalle de un préstamo específico"""
    prestamo_id = input_int("\n   ID del préstamo: ")
    
    prestamo = Prestamo.query.get(prestamo_id)
    if not prestamo:
        print(f"   ❌ Préstamo #{prestamo_id} no encontrado")
        return
    
    print_header(f"DETALLE DEL PRÉSTAMO #{prestamo_id}")
    
    print(f"\n📋 Información del préstamo:")
    print(f"   Cliente: {prestamo.cliente.nombre_completo}")
    print(f"   DNI: {prestamo.cliente.dni}")
    print(f"   Monto: S/ {prestamo.monto_total:,.2f}")
    print(f"   TEA: {prestamo.interes_tea}%")
    print(f"   Plazo: {prestamo.plazo} cuotas")
    print(f"   Fecha otorgamiento: {prestamo.f_otorgamiento}")
    print(f"   Estado: {prestamo.estado.value}")
    
    mostrar_cronograma(prestamo)


def menu_principal():
    """Menú principal del script"""
    app = create_app()
    
    with app.app_context():
        cliente_actual = None
        prestamo_actual = None
        
        while True:
            print_header("SIMULADOR DE PAGOS - MENÚ PRINCIPAL")
            
            if cliente_actual:
                print(f"\n   👤 Cliente actual: {cliente_actual.nombre_completo} (DNI: {cliente_actual.dni})")
            if prestamo_actual:
                print(f"   📋 Préstamo actual: #{prestamo_actual.prestamo_id}")
            
            print("\n   Opciones:")
            print("   [1] Crear cliente de prueba")
            print("   [2] Crear préstamo")
            print("   [3] Ver cronograma de préstamo actual")
            print("   [4] Registrar pago")
            print("   [5] Listar todos los préstamos")
            print("   [6] Ver detalle de préstamo")
            print("   [7] Simular cuotas vencidas (cambiar fechas)")
            print("   [8] Atrasar una cuota específica (cambiar solo 1 cuota)")
            print("   [0] Salir")
            
            opcion = input("\n   Selecciona una opción: ").strip()
            
            if opcion == '1':
                cliente_actual = crear_cliente_prueba(app)
            
            elif opcion == '2':
                if not cliente_actual:
                    print("\n   ⚠️ Primero crea un cliente (opción 1)")
                    continue
                prestamo_actual = crear_prestamo_personalizado(cliente_actual)
            
            elif opcion == '3':
                if not prestamo_actual:
                    print("\n   ⚠️ Primero crea un préstamo (opción 2)")
                    continue
                mostrar_cronograma(prestamo_actual)
            
            elif opcion == '4':
                registrar_pago_interactivo()
            
            elif opcion == '5':
                listar_prestamos()
            
            elif opcion == '6':
                ver_detalle_prestamo()
            
            elif opcion == '7':
                simular_cuotas_vencidas()
            
            elif opcion == '8':
                atrasar_cuota_especifica()
            
            elif opcion == '0':
                print("\n   👋 ¡Hasta luego!\n")
                break
            
            else:
                print("\n   ❌ Opción no válida")
            
            input("\n   Presiona Enter para continuar...")

def simular_cuotas_vencidas():
    """Simula cuotas vencidas cambiando fechas"""
    print_header("SIMULAR CUOTAS VENCIDAS")
    
    prestamo_id = input_int("\n   ID del préstamo: ")
    
    prestamo = Prestamo.query.get(prestamo_id)
    if not prestamo:
        print(f"   ❌ Préstamo #{prestamo_id} no encontrado")
        return
    
    num_cuotas = input_int("   ¿Cuántas cuotas quieres que estén vencidas? [2]: ", 2)
    dias_atraso = input_int("   ¿Cuántos días de atraso por cuota? [35]: ", 35)
    
    cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota).limit(num_cuotas).all()
    
    print(f"\n   Se modificarán las fechas de {len(cuotas)} cuotas:")
    
    for i, cuota in enumerate(cuotas, 1):
        dias = dias_atraso * (num_cuotas - i + 1)
        nueva_fecha = date.today() - timedelta(days=dias)
        print(f"   • Cuota {cuota.numero_cuota}: {cuota.fecha_vencimiento} → {nueva_fecha}")
    
    confirmar = input("\n   ¿Confirmar cambios? (S/N) [N]: ").strip().upper()
    
    if confirmar != 'S':
        print("   ❌ Operación cancelada")
        return
    
    try:
        for i, cuota in enumerate(cuotas, 1):
            dias = dias_atraso * (num_cuotas - i + 1)
            cuota.fecha_vencimiento = date.today() - timedelta(days=dias)
        
        db.session.commit()
        print(f"\n   ✅ Fechas modificadas exitosamente")
        print(f"   Ahora las cuotas generarán mora al consultarlas")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n   ❌ Error: {e}")


def atrasar_cuota_especifica():
    """Permite seleccionar una cuota específica y atrasar su fecha de vencimiento"""
    print_header("ATRASAR FECHA DE VENCIMIENTO DE UNA CUOTA")
    
    prestamo_id = input_int("\n   ID del préstamo: ")
    prestamo = Prestamo.query.get(prestamo_id)
    if not prestamo:
        print(f"   ❌ Préstamo #{prestamo_id} no encontrado")
        return
    
    cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota).all()
    if not cuotas:
        print("   ⚠️ No hay cuotas para este préstamo")
        return
    
    print(f"\n   Cuotas del préstamo #{prestamo_id}:")
    print(f"\n{'#':>3} | {'ID Cuota':>8} | {'Vencimiento':>12} | {'Pendiente':>10} | {'Mora':>8}")
    print_separator()
    for cuota in cuotas:
        mora = cuota.mora_acumulada or Decimal('0')
        print(
            f"{cuota.numero_cuota:>3} | "
            f"{cuota.cuota_id:>8} | "
            f"{cuota.fecha_vencimiento.strftime('%d/%m/%Y'):>12} | "
            f"S/{cuota.saldo_pendiente:>8.2f} | "
            f"S/{mora:>6.2f}"
        )
    
    cuota_id = input_int("\n   ID de la cuota a atrasar: ")
    cuota = Cuota.query.get(cuota_id)
    if not cuota or cuota.prestamo_id != prestamo_id:
        print(f"   ❌ Cuota #{cuota_id} no válida para este préstamo")
        return
    
    print(f"\n   Fecha actual de vencimiento de la cuota #{cuota.numero_cuota}: {cuota.fecha_vencimiento}")
    dias = input_int("   ¿Cuántos días deseas atrasar la cuota? (Ej: 1 → se hace vencida ayer) [1]: ", 1)
    if dias < 1:
        print("   ❌ Debes especificar al menos 1 día para atrasar")
        return
    
    nueva_fecha = cuota.fecha_vencimiento - timedelta(days=dias)
    print(f"\n   Nueva fecha de vencimiento: {nueva_fecha} (antes: {cuota.fecha_vencimiento})")
    
    confirmar = input("\n   ¿Confirmar cambio? (S/N) [N]: ").strip().upper()
    if confirmar != 'S':
        print("   ❌ Operación cancelada")
        return
    
    try:
        cuota.fecha_vencimiento = nueva_fecha
        db.session.commit()
        print(f"\n   ✅ Fecha de vencimiento actualizada exitosamente")
        print(f"   Cuota #{cuota.numero_cuota} → nueva fecha: {nueva_fecha}")
    except Exception as e:
        db.session.rollback()
        print(f"\n   ❌ Error al actualizar la cuota: {e}")


# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n   👋 Operación cancelada por el usuario\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n   ❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)