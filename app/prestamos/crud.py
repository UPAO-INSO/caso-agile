from app.extensions import db
from app.prestamos.model.prestamos import Prestamo

def crear_prestamo(prestamo): # → Crear un nuevo préstamo
    try:
        db.session.add(prestamo)
        db.session.commit()
        db.session.refresh(prestamo)  # Refrescar para obtener el ID generado
        return prestamo
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error al guardar el préstamo: {str(e)}")
    
def listar_prestamos(): # → Listar todos los préstamos
    return Prestamo.query.all()

def listar_prestamos_por_cliente_id(cliente_id): # → Listar todos los préstamos de un cliente específico
    return db.session.execute(
        db.select(Prestamo)
        .where(Prestamo.cliente_id == cliente_id)
        .order_by(Prestamo.f_registro.desc())
    ).scalars().all()

def obtener_prestamo_por_id(prestamo_id): # → Obtener un préstamo por su ID
    return Prestamo.query.get(prestamo_id)
    
def actualizar_prestamo(prestamo_id, **kwargs): # → Actualizar un préstamo existente
    try:
        prestamo = Prestamo.query.get(prestamo_id)
        if not prestamo:
            return None, "Préstamo no encontrado"
        
        for key, value in kwargs.items():
            if hasattr(prestamo, key):
                setattr(prestamo, key, value)
        
        db.session.commit()
        return prestamo, None
    except Exception as e:
        db.session.rollback()
        return None, f"Error al actualizar préstamo: {str(e)}"
    
def eliminar_prestamo(prestamo_id): # → Eliminar un préstamo (soft delete)
    try:
        prestamo = Prestamo.query.get(prestamo_id)
        if not prestamo:
            return False, "Préstamo no encontrado"
        
        # Soft delete - cambiar estado en lugar de eliminar
        from app.prestamos.model.prestamos import EstadoPrestamoEnum
        prestamo.estado = EstadoPrestamoEnum.CANCELADO
        
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, f"Error al eliminar préstamo: {str(e)}"