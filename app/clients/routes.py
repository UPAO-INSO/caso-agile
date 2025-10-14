from flask import Blueprint, request, jsonify
from app.clients import crud

# Blueprint para el módulo de clientes (API)
clientes_bp = Blueprint('clientes', __name__, url_prefix='/api/v1/clientes')


@clientes_bp.route('', methods=['POST'])
def crear_cliente(): # → Endpoint para crear un nuevo cliente
    data = request.get_json()
    
    if not data or not data.get('dni'):
        return jsonify({'error': 'El campo DNI es indispensable'}), 400
    
    dni = data.get('dni')
    pep = data.get('pep', False)
    
    cliente, error = crud.crear_cliente(dni, pep)
    
    if error:
        if "ya existe" in error:
            return jsonify({'error': error}), 409
        elif "no encontrado" in error:
            return jsonify({'error': error}), 404
        else:
            return jsonify({'error': error}), 503
    
    return jsonify(cliente.to_dict()), 201


@clientes_bp.route('', methods=['GET'])
def listar_clientes(): # → Endpoint para listar todos los clientes
    clientes = crud.listar_clientes()
    return jsonify([cliente.to_dict() for cliente in clientes]), 200


@clientes_bp.route('/<int:cliente_id>', methods=['GET'])
def obtener_cliente(cliente_id): # → Endpoint para obtener un cliente por ID
    cliente = crud.obtener_cliente_por_id(cliente_id)
    
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    return jsonify(cliente.to_dict()), 200


@clientes_bp.route('/<int:cliente_id>', methods=['PUT'])
def actualizar_cliente(cliente_id): # → Endpoint para actualizar un cliente
    data = request.get_json()
    pep = data.get('pep')
    
    cliente, error = crud.actualizar_cliente(cliente_id, pep)
    
    if error:
        return jsonify({'error': error}), 404
    
    return jsonify(cliente.to_dict()), 200


@clientes_bp.route('/<int:cliente_id>', methods=['DELETE'])
def eliminar_cliente(cliente_id): # → Endpoint para eliminar un cliente
    exito, error = crud.eliminar_cliente(cliente_id)
    
    if not exito:
        return jsonify({'error': error}), 404
    
    return jsonify({'mensaje': f'Cliente con ID {cliente_id} eliminado correctamente'}), 200

# FUNCIÓN DE PRUEBA - Solo para desarrollo

def probar_api_dni(): # → Función para probar la API de DNI desde consola
    dni = input("\nIngrese DNI (8 dígitos): ").strip()
    
    if len(dni) != 8 or not dni.isdigit():
        print("DNI inválido. Debe tener 8 dígitos.")
        return
    
    from app.clients.crud import consultar_dni_api
    info, error = consultar_dni_api(dni)
    
    if error:
        print(f"{error}")
    else:
        print("\nINFORMACIÓN ENCONTRADA")
        print("="*50)
        print(f"DNI: {info.get('numero')}")
        print(f"Nombres: {info.get('nombres')}")
        print(f"Apellido Paterno: {info.get('apellido_paterno')}")
        print(f"Apellido Materno: {info.get('apellido_materno')}")
        print(f"Direccion: {info.get('direccion')}")