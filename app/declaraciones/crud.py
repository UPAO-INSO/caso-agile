from app import db

def crear_declaracion(declaracion):
    try:
        db.session.add(declaracion)
        db.session.commit()
        # Devolver el objeto declaracion (no el resultado de add)
        return declaracion, None
    
    except Exception as e:
        db.session.rollback()
        return None, f"Error al guardar la declaracion: {str(e)}"