"""
Views - Endpoints de Préstamos
Endpoints que renderizan templates HTML
"""
from flask import render_template, redirect, url_for, flash
import logging
from datetime import datetime

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

        # ---------------------------------------------------------
        # LÓGICA POST: RECIBIR DATOS DEL FORMULARIO (Cuando el usuario presiona el botón)
        # ---------------------------------------------------------
        if request.method == 'POST':
            # 1. Recuperar los datos del formulario (ejemplos)
            numero_cuota = request.form.get('numero_cuota')
            monto_pagado = request.form.get('monto_pagado')
            
            # 2. **Aquí iría tu lógica real de guardado en la base de datos**
            
            # 3. Respuesta (Muestra la pantalla de éxito)
            logger.info(f"PAGO PROCESADO: Prestamo {prestamo_id}, Cuota {numero_cuota}, Monto {monto_pagado}")
            
            # Recargamos los datos para que la pantalla de éxito tenga contexto
            cuotas = listar_cuotas_por_prestamo(prestamo_id)
            resumen = obtener_resumen_cuotas(prestamo_id)
            
            return render_template(
                'pages/prestamos/registro_pago.html',
                prestamo=prestamo,
                cuotas=cuotas,
                resumen=resumen,
                hoy=datetime.now().date(),
                success=True, # Activa la vista de éxito en el HTML
                datos_pago={'monto': monto_pagado} # Pasamos el monto para el mensaje
            )

        # ---------------------------------------------------------
        # LÓGICA GET: MOSTRAR EL FORMULARIO (Cuando la página carga por primera vez)
        # ---------------------------------------------------------
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