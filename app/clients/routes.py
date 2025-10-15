from flask import request, jsonify
from app.clients import crud
from . import clientes_bp

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

@clientes_bp.route('/consultar_dni/<string:cliente_dni>', methods=['GET'])
def probar_api_dni(cliente_dni): # → Función para probar la API de DNI
    print(cliente_dni)
    
    if len(cliente_dni) != 8 or not cliente_dni.isdigit():
        print("DNI inválido. Debe tener 8 dígitos.")
        return
    
    from app.clients.crud import consultar_dni_api
    info, error = consultar_dni_api(cliente_dni)
    
    if error:
        return jsonify(error), 400
    
    return jsonify(info), 200
    