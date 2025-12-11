# Modelo de la aplicación - Centraliza todos los modelos de BD
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamoEnum
from app.models.cuota import Cuota
from app.models.declaracion import DeclaracionJurada, TipoDeclaracionEnum
from app.models.pago import Pago, MedioPagoEnum
from app.models.usuario import Usuario
from app.models.egreso import Egreso
from app.models.apertura_caja import AperturaCaja

__all__ = [
    'Cliente',
    'Prestamo',
    'EstadoPrestamoEnum',
    'Cuota',
    'DeclaracionJurada',
    'TipoDeclaracionEnum',
    'Pago',
    'MedioPagoEnum',
    'Usuario',
    'Egreso',
    'AperturaCaja'
]
