from app import db

def crear_declaracion(declaracion):
    try:
        modelo_declaracion = db.session.add(declaracion)
        db.session.commit()
    
        return modelo_declaracion, None
    
    except Exception as e:
        db.session.rollback()
        return None, f"Error al guardar el cliente: {str(e)}"