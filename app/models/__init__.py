"""
Modelos de la aplicación
Centraliza todos los modelos de base de datos
"""
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamoEnum
from app.models.cuota import Cuota
from app.models.declaracion import DeclaracionJurada, TipoDeclaracionEnum
from app.models.pago import Pago, EstadoPagoEnum, MetodoPagoEnum

__all__ = [
    'Cliente',
    'Prestamo',
    'EstadoPrestamoEnum',
    'Cuota',
    'DeclaracionJurada',
    'TipoDeclaracionEnum',
    'Pago',
    'EstadoPagoEnum',
    'MetodoPagoEnum'
]
