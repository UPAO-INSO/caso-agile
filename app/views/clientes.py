"""
Views - Endpoints de Clientes
Endpoints que renderizan templates HTML
"""
from flask import Blueprint, render_template, redirect, url_for, flash
import logging

from app.clients.crud import (
    listar_clientes,
    obtener_cliente_por_id
)
from app.common.error_handler import ErrorHandler

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)

# Blueprint para las vistas de clientes
clientes_view_bp = Blueprint('clientes_view', __name__)


@clientes_view_bp.route('/clientes')
def listar_clientes_view():
    """Vista: Lista todos los clientes en una página HTML"""
    try:
        clientes = listar_clientes()
        return render_template('pages/clientes/lista.html', clientes=clientes)
    except Exception as e:
        logger.error(f"Error al listar clientes: {str(e)}")
        flash('Error al cargar la lista de clientes', 'error')
        return redirect(url_for('main.home'))


@clientes_view_bp.route('/clientes/<int:cliente_id>')
def ver_cliente_view(cliente_id):
    """Vista: Muestra el detalle de un cliente"""
    try:
        cliente = obtener_cliente_por_id(cliente_id)
        
        if not cliente:
            flash('Cliente no encontrado', 'error')
            return redirect(url_for('clientes_view.listar_clientes_view'))
        
        return render_template('pages/clientes/detalle.html', cliente=cliente)
    except Exception as e:
        logger.error(f"Error al obtener cliente {cliente_id}: {str(e)}")
        flash('Error al cargar el detalle del cliente', 'error')
        return redirect(url_for('clientes_view.listar_clientes_view'))
