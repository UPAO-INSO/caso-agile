from flask import render_template, request, jsonify
import os
from app.models import Cliente, EstadoPrestamoEnum
from app.routes import clientes_bp
from app import crud

# → Guardamos la API Key en variables de entorno
API_KEY = os.environ.get('DNI_API_KEY')
API_URL = os.environ.get('DNI_API_URL')

# ------------- ENDPOINTS CRUD PRINCIPALES-----------------------------

@clientes_bp.route('', methods=['POST'])
def crear_cliente(): # → Endpoint para crear un nuevo cliente
    data = request.get_json()
    
    if not data or not data.get('dni'):
        return jsonify({'error': 'El campo DNI es indispensable'}), 400
    
    dni = data.get('dni')
    pep_declarado = data.get('pep', False)
    
    cliente_dict, error = crud.crear_cliente(dni, pep_declarado)
    
    if error:
        if "ya existe" in error:
            return jsonify({'error': error}), 409
        elif "no encontrado" in error:
            return jsonify({'error': error}), 404
        else:
            return jsonify({'error': error}), 503
    
    return jsonify(cliente_dict), 201

@clientes_bp.route('/verificar_prestamo/<int:cliente_id>', methods=['GET'])
def verificar_prestamo_cliente(cliente_id):
    prestamo = crud.prestamo_activo_cliente(cliente_id, EstadoPrestamoEnum.VIGENTE)
    
    if not prestamo:
        return jsonify({'tiene_prestamo_activo': False}), 200
    
    return jsonify({
        'tiene_prestamo_activo': True,
        'prestamo': prestamo.to_dict()
    }), 200


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


# ENDPOINTS PARA EL FRONTEND

@clientes_bp.route('/dni/<string:dni>', methods=['GET'])
def buscar_cliente_por_dni(dni): # → Endpoint para buscar cliente por DNI en la BD
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    
    # Buscar cliente en la BD
    cliente = Cliente.query.filter_by(dni=dni).first()
    
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    # Verificar si tiene prestamo activo
    from app.models.prestamo import Prestamo, EstadoPrestamoEnum
    prestamo_activo = Prestamo.query.filter_by(
        cliente_id=cliente.cliente_id,
        estado=EstadoPrestamoEnum.VIGENTE
    ).first()
    
    # Agregar info de prestamo al dict
    cliente_dict = cliente.to_dict()
    cliente_dict['tiene_prestamo_activo'] = prestamo_activo is not None
    
    return jsonify(cliente_dict), 200


@clientes_bp.route('/consultar_dni/<string:dni>', methods=['GET'])
def consultar_dni_reniec(dni): # -> Endpoint para consultar DNI en la API externa
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    
    info, error = crud.consultar_dni_api(dni)
    
    if error:
        # Retornar 404 cuando no se encuentra, no 400
        return jsonify({
            'error': error,
            'mensaje': 'DNI no encontrado en RENIEC. Verifique el número o intente más tarde.'
        }), 404
    
    # Devolver los datos tal cual vienen de la API
    return jsonify(info), 200


# ------------ ENDPOINTS DE PRUEBA---------------------------
@clientes_bp.route('/test/pep/<string:dni>', methods=['GET'])
def test_validar_pep(dni): # → Endpoint de prueba para validar PEP
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    
    es_pep = crud.validar_pep_en_dataset(dni)
    
    return jsonify({
        'dni': dni,
        'es_pep': es_pep,
        'mensaje': 'Este DNI está en la lista PEP' if es_pep else 'Este DNI NO está en la lista PEP'
    }), 200
    
@clientes_bp.route('/list', methods=['GET'])
def listar_clientes_view():
    page = request.args.get('page', 1, type=int)
    dni = request.args.get('dni', '')
    
    clientes_paginados = crud.obtener_clientes_con_prestamos_info(page=page, per_page=5, dni=dni)
    print(list(clientes_paginados))
    return render_template('pages/clientes/lista_clientes.html', clientes=clientes_paginados)