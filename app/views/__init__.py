"""
Views Module
Contiene endpoints que renderizan templates HTML
"""
from .clientes import clientes_view_bp
from .prestamos import prestamos_view_bp

__all__ = ['clientes_view_bp', 'prestamos_view_bp']
