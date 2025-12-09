"""
Views - Endpoints de Préstamos
Endpoints que renderizan templates HTML
"""
from flask import render_template, redirect, url_for, flash
import logging
from datetime import datetime, date
from decimal import Decimal

from app.routes import prestamos_view_bp
from app.crud import (
    listar_prestamos_por_cliente_id,
    obtener_prestamo_por_id,
    obtener_cliente_por_id,
    listar_cuotas_por_prestamo,
    obtener_resumen_cuotas
)
from app.common.error_handler import ErrorHandler

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)


@prestamos_view_bp.route('/')
def index_view():
    """Vista principal - Landing page"""
    return render_template('index.html')


@prestamos_view_bp.route('/prestamos')
def listar_prestamos_view():
    """Vista: Lista todos los préstamos"""
    try:
        # Aquí puedes agregar lógica para listar todos los préstamos
        # Por ahora redirige al index
        return redirect(url_for('prestamos_view.index_view'))
    except Exception as e:
        logger.error(f"Error al listar préstamos: {str(e)}")
        flash('Error al cargar la lista de préstamos', 'error')
        return redirect(url_for('prestamos_view.index_view'))


@prestamos_view_bp.route('/clientes/<int:cliente_id>/prestamos')
def ver_prestamos_cliente_view(cliente_id):
    """Vista: Muestra los préstamos de un cliente"""
    try:
        cliente = obtener_cliente_por_id(cliente_id)
        
        if not cliente:
            flash('Cliente no encontrado', 'error')
            return redirect(url_for('prestamos_view.index_view'))
        
        prestamos = listar_prestamos_por_cliente_id(cliente_id)
        
        return render_template(
            'pages/prestamos/cliente_prestamos.html',
            cliente=cliente,
            prestamos=prestamos
        )
    except Exception as e:
        logger.error(f"Error al obtener préstamos del cliente {cliente_id}: {str(e)}")
        flash('Error al cargar los préstamos del cliente', 'error')
        return redirect(url_for('prestamos_view.index_view'))

@prestamos_view_bp.route('/prestamos/<int:prestamo_id>')
def ver_prestamo_view(prestamo_id):
    """Vista: Muestra el detalle de un préstamo con su cronograma"""
    try:
        prestamo = obtener_prestamo_por_id(prestamo_id)
        
        if not prestamo:
            flash('Préstamo no encontrado', 'error')
            return redirect(url_for('prestamos_view.index_view'))
        
        # Actualizar moras antes de mostrar
        from app.services.mora_service import MoraService
        MoraService.actualizar_mora_prestamo(prestamo_id)
        
        cuotas = listar_cuotas_por_prestamo(prestamo_id)
        resumen = obtener_resumen_cuotas(prestamo_id)
        
        return render_template(
            'pages/prestamos/detalle.html',
            prestamo=prestamo,
            cuotas=cuotas,
            resumen=resumen,
            hoy=datetime.now().date()
        )
    except Exception as e:
        logger.error(f"Error al obtener préstamo {prestamo_id}: {str(e)}")
        flash('Error al cargar el detalle del préstamo', 'error')
        return redirect(url_for('prestamos_view.index_view'))

from flask import request # <--- ¡Asegúrate de tener esta importación arriba!

@prestamos_view_bp.route('/prestamos/<int:prestamo_id>/pago', methods=['GET', 'POST'])
def pagar_prestamo(prestamo_id):
    try:
        prestamo = obtener_prestamo_por_id(prestamo_id)
        if not prestamo:
            flash('Préstamo no encontrado', 'error')
            return redirect(url_for('prestamos_view.index_view'))

        # Actualizar moras antes de mostrar o procesar
        from app.services.mora_service import MoraService
        MoraService.actualizar_mora_prestamo(prestamo_id)

            # LÓGICA POST: RECIBIR DATOS DEL FORMULARIO (Cuando el usuario presiona el botón)
        if request.method == 'POST':
            try:
                # 1. Recuperar los datos del formulario
                numero_cuota = request.form.get('numero_cuota')
                monto_pagado = request.form.get('monto_pagado')
                fecha_pago_str = request.form.get('fecha_pago')
                metodo_pago = request.form.get('metodo_pago', 'EFECTIVO')
                
                # Validar datos
                if not numero_cuota or not monto_pagado:
                    flash('Debe seleccionar una cuota y especificar el monto', 'error')
                    return redirect(url_for('prestamos_view.pagar_prestamo', prestamo_id=prestamo_id))
                
                # Convertir datos
                numero_cuota_int = int(numero_cuota)
                monto_pagado_decimal = Decimal(monto_pagado)
                
                # Convertir fecha
                from datetime import datetime as dt
                fecha_pago = dt.strptime(fecha_pago_str, '%Y-%m-%d').date() if fecha_pago_str else date.today()
                
                # Buscar la cuota
                from app.crud.cuota_crud import listar_cuotas_por_prestamo as listar_cuotas
                cuotas = listar_cuotas(prestamo_id)
                cuota = next((c for c in cuotas if c.numero_cuota == numero_cuota_int), None)
                
                if not cuota:
                    flash(f'Cuota #{numero_cuota_int} no encontrada', 'error')
                    return redirect(url_for('prestamos_view.pagar_prestamo', prestamo_id=prestamo_id))
                
                # 2. Procesar el pago usando el servicio
                from app.services.pago_service import PagoService
                respuesta, error, status_code = PagoService.registrar_pago_cuota(
                    prestamo_id=prestamo_id,
                    cuota_id=cuota.cuota_id,
                    monto_pagado=monto_pagado_decimal,
                    medio_pago=metodo_pago,
                    fecha_pago=fecha_pago,
                    observaciones=f"Pago registrado desde interfaz web"
                )
                
                if error:
                    flash(f'Error al procesar el pago: {error}', 'error')
                    logger.error(f"Error procesando pago: {error}")
                    return redirect(url_for('prestamos_view.pagar_prestamo', prestamo_id=prestamo_id))
                
                # 3. Respuesta exitosa
                logger.info(f"PAGO PROCESADO: Prestamo {prestamo_id}, Cuota {numero_cuota}, Monto {monto_pagado}")
                
                # Recargamos los datos actualizados
                cuotas = listar_cuotas_por_prestamo(prestamo_id)
                resumen = obtener_resumen_cuotas(prestamo_id)
                
                return render_template(
                    'pages/prestamos/registro_pago.html',
                    prestamo=prestamo,
                    cuotas=cuotas,
                    resumen=resumen,
                    hoy=datetime.now().date(),
                    success=True,
                    datos_pago={
                        'monto': monto_pagado,
                        'cuota': numero_cuota,
                        'fecha': fecha_pago,
                        'metodo': metodo_pago
                    }
                )
            except ValueError as ve:
                flash(f'Datos inválidos: {str(ve)}', 'error')
                logger.error(f"Error de validación: {ve}")
                return redirect(url_for('prestamos_view.pagar_prestamo', prestamo_id=prestamo_id))
            except Exception as e:
                flash(f'Error al procesar el pago: {str(e)}', 'error')
                logger.error(f"Error procesando pago: {e}", exc_info=True)
                return redirect(url_for('prestamos_view.pagar_prestamo', prestamo_id=prestamo_id))

        # LÓGICA GET: MOSTRAR EL FORMULARIO (Cuando la página carga por primera vez)
        cuotas = listar_cuotas_por_prestamo(prestamo_id)
        resumen = obtener_resumen_cuotas(prestamo_id)
        
        return render_template(
            'pages/prestamos/registro_pago.html',
            prestamo=prestamo,
            cuotas=cuotas,
            resumen=resumen,
            hoy=datetime.now().date(),
            success=False # Vista normal del formulario
        )

    except Exception as e:
        logger.error(f"Error al procesar el pago del préstamo {prestamo_id}: {str(e)}")
        flash('Error interno al procesar la solicitud', 'error')
        return redirect(url_for('prestamos_view.index_view'))