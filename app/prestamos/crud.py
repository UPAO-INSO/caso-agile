from app import db
from app.prestamos.model.prestamos import Prestamo


def crear_prestamo(prestamo):
    try:
        modelo_prestamo = db.session.add(prestamo)
        db.session.commit()
        return modelo_prestamo
    except Exception as e:
        db.session.rollback()
        return None, f"Error al guardar el cliente: {str(e)}"
    
def listar_prestamos():
    Prestamo.query.all()
    return    

def listar_prestamos_por_cliente_id(cliente_id):
    return db.session.execute(
        db.select(Prestamo)
        .where(Prestamo.cliente_id == cliente_id)
        .order_by(Prestamo.f_registro.desc())
    ).scalars().all()
    
def obtener_prestamo_por_id(prestamo_id):
    return Prestamo.query.get(id=prestamo_id)
    
    
def actualizar_prestamo():
    return
    
    
def eliminar_prestamo():
    return
    