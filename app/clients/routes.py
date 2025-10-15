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
    pep_declarado = data.get('pep', False)  # Lo que el cajero preguntó al cliente
    
    cliente_dict, error = crud.crear_cliente(dni, pep_declarado)
    
    if error:
        if "ya existe" in error:
            return jsonify({'error': error}), 409
        elif "no encontrado" in error:
            return jsonify({'error': error}), 404
        else:
            return jsonify({'error': error}), 503
    
    # Retornar información completa incluyendo validación PEP
    return jsonify(cliente_dict), 201


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


# ------------------ ENDPOINTS DE PRUEBA - Para POSTMAN ----------------------

@clientes_bp.route('/test/dni/<string:dni>', methods=['GET'])
def test_consultar_dni(dni): # → Endpoint de prueba para consultar DNI en la API de Factiliza
                             # → Usar en Postman: GET http://127.0.0.1:5000/api/v1/clientes/test/dni/12345678
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    
    info, error = crud.consultar_dni_api(dni)
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({'success': True, 'data': info}), 200


@clientes_bp.route('/test/pep/<string:dni>', methods=['GET'])
def test_validar_pep(dni): # → Endpoint de prueba para validar si un DNI está en el dataset PEP
                           # → Usar: GET http://127.0.0.1:5000/api/v1/clientes/test/pep/12345678
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    
    es_pep = crud.validar_pep_en_dataset(dni)
    
    return jsonify({
        'dni': dni,
        'es_pep': es_pep,
        'mensaje': 'Este DNI está en la lista PEP' if es_pep else 'Este DNI NO está en la lista PEP'
    }), 200