from app import db
from app.clients.model.clients import Cliente
import requests
import os

# Configuración de API externa
API_KEY = os.environ.get('DNI_API_KEY')
API_URL = "https://api.factiliza.com/v1/dni/info/"


def consultar_dni_api(dni): # → Consulta la API externa para obtener datos del DNI
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json"
        }
        respuesta = requests.get(f"{API_URL}{dni}", headers=headers)
        respuesta.raise_for_status()
        
        api_data = respuesta.json()
        
        if not api_data.get("success"):
            return None, "DNI no encontrado por la API"
        
        return api_data.get('data', {}), None
        
    except requests.exceptions.RequestException as e:
        return None, f"Error al consultar el servicio de DNI: {str(e)}"


def crear_cliente(dni, pep=False): # → Crea un nuevo cliente consultando la API de DNI
    # Validar si ya existe
    cliente_existente = Cliente.query.filter_by(dni=dni).first()
    if cliente_existente:
        return None, "El cliente ya existe"
    
    # Consultar API
    info_cliente, error = consultar_dni_api(dni)
    if error:
        return None, error
    
    # Crear cliente
    try:
        nuevo_cliente = Cliente(
            dni=dni,
            nombre_completo=info_cliente.get('nombres', ''),
            apellido_paterno=info_cliente.get('apellido_paterno', ''),
            apellido_materno=info_cliente.get('apellido_materno', ''),
            pep=pep
        )
        
        db.session.add(nuevo_cliente)
        db.session.commit()
        
        return nuevo_cliente, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error al guardar el cliente: {str(e)}"


def listar_clientes(): # → Lista todos los clientes
    return Cliente.query.all()


def obtener_cliente_por_id(cliente_id): # → Obtiene un cliente por su ID
    return Cliente.query.get(cliente_id)


def obtener_cliente_por_dni(dni): # → Obtener cliente por DNI
    return Cliente.query.filter_by(dni=dni).first()


def actualizar_cliente(cliente_id, pep=None): # → Actualizar los datos de un cliente
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return None, "Cliente no encontrado"
    
    try:
        if pep is not None:
            cliente.pep = pep
        
        db.session.commit()
        return cliente, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error al actualizar: {str(e)}"


def eliminar_cliente(cliente_id): # -> Eliminar un cliente por su ID
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return False, "Cliente no encontrado"
    
    try:
        db.session.delete(cliente)
        db.session.commit()
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error al eliminar: {str(e)}"