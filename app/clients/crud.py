"""
CRUD de Clientes
Operaciones de base de datos para el modelo Cliente
"""
from app.extensions import db
from app.clients.model.clients import Cliente
from app.prestamos.model.prestamos import Prestamo
from app.services.cliente_service import ClienteService
from app.services.pep_service import PEPService

# ==================== FUNCIONES LEGACY (backward compatibility) ====================

def cargar_lista_pep():
    """Función legacy - ahora usa PEPService"""
    PEPService.cargar_dataset_pep()
    return set()  # Mantener compatibilidad con código existente


LISTA_PEP = set()  # Ya no se usa, PEPService maneja esto internamente


def validar_pep_en_dataset(dni):
    """Función legacy - ahora usa PEPService"""
    return PEPService.validar_pep(dni)


def consultar_dni_api(dni, correo_electronico=None):
    """Función legacy - ahora usa ClienteService"""
    datos, error = ClienteService.consultar_dni_reniec(dni)
    if datos and correo_electronico:
        datos['correo_electronico'] = correo_electronico
    return datos, error


def crear_cliente(dni, correo_electronico, pep_declarado=False):
    """Función legacy - ahora usa ClienteService"""
    return ClienteService.crear_cliente_completo(dni, correo_electronico, pep_declarado)


def crear_o_obtener_cliente(dni):
    """Función legacy - ahora usa ClienteService"""
    return ClienteService.obtener_o_crear_cliente(dni)


def actualizar_cliente(cliente_id, pep=None):
    """Función legacy - ahora usa ClienteService"""
    return ClienteService.actualizar_cliente(cliente_id, pep=pep)


# ==================== FUNCIONES CRUD SIMPLES ====================

# ==================== FUNCIONES CRUD SIMPLES ====================

def listar_clientes():
    """Lista todos los clientes"""
    return Cliente.query.all()


def obtener_cliente_por_id(cliente_id):
    """Obtiene un cliente por su ID"""
    return Cliente.query.get(cliente_id)


def obtener_cliente_por_dni(dni):
    """Obtiene un cliente por DNI"""
    return Cliente.query.filter_by(dni=dni).first()


def eliminar_cliente(cliente_id):
    """Elimina un cliente por su ID"""
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return False, "Cliente no encontrado"
    
    try:
        db.session.delete(cliente)
        db.session.commit()
        return True, None
    except Exception as exc:
        db.session.rollback()
        return False, f"Error al eliminar: {str(exc)}"


# ==================== QUERIES CON JOINS ====================

def prestamo_activo_cliente(cliente_id, estado):
    """Obtiene préstamo activo de un cliente por estado"""
    return db.session.execute(
        db.select(Prestamo)
        .filter_by(cliente_id=cliente_id, estado=estado)
    ).scalar_one_or_none()


def obtener_clientes_por_estado_prestamo():
    """Obtiene clientes que tienen préstamos"""
    return db.session.execute(
        db.select(Cliente)
        .join(Prestamo)
        .distinct()
        .order_by(Cliente.nombre_completo.asc())
    ).scalars().all()


# ==================== PAGINACIÓN ====================

def paginar_clientes(page=1, per_page=5, dni=None):
    """
    Pagina clientes con búsqueda opcional por DNI.
    
    Args:
        page: Número de página
        per_page: Elementos por página
        dni: DNI para filtrar (opcional)
        
    Returns:
        Pagination: Objeto de paginación de Flask-SQLAlchemy
    """
    query = Cliente.query
    
    if dni:
        query = query.filter(Cliente.dni.ilike(f'%{dni}%'))
    
    return query.order_by(Cliente.fecha_registro.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )


def obtener_clientes_con_prestamos_info(page=1, per_page=5, dni=None):
    """
    Obtiene clientes con información agregada de sus préstamos.
    
    Incluye:
    - Monto total prestado
    - Total de préstamos
    - Total de cuotas
    - Préstamos vigentes
    
    Args:
        page: Número de página
        per_page: Elementos por página
        dni: DNI para filtrar (opcional)
        
    Returns:
        Pagination: Objeto de paginación con datos agregados
    """
    from sqlalchemy import func, case
    from app.cuotas.model.cuotas import Cuota
    from app.prestamos.model.prestamos import EstadoPrestamoEnum
    
    query = db.session.query(
        Cliente,
        func.coalesce(func.sum(Prestamo.monto_total), 0).label('monto_total_prestado'),
        func.count(func.distinct(Prestamo.prestamo_id)).label('total_prestamos'),
        func.count(Cuota.cuota_id).label('total_cuotas'),
        func.coalesce(func.count(func.distinct(
            case((Prestamo.estado == EstadoPrestamoEnum.VIGENTE, Prestamo.prestamo_id))
        )), 0).label('prestamos_vigentes')
    ).outerjoin(
        Prestamo, Cliente.cliente_id == Prestamo.cliente_id
    ).outerjoin(
        Cuota, Prestamo.prestamo_id == Cuota.prestamo_id
    ).group_by(Cliente.cliente_id)
    
    if dni:
        query = query.filter(Cliente.dni.ilike(f'%{dni}%'))
    
    query = query.order_by(Cliente.fecha_registro.desc())
    
    return query.paginate(page=page, per_page=per_page, error_out=False)