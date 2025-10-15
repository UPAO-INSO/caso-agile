from flask import Blueprint, request, jsonify
from app.clients import crud

# Blueprint para el módulo de clientes (API)
clientes_bp = Blueprint('clientes', __name__, url_prefix='/api/v1/clientes')


@clientes_bp.route('', methods=['POST'])
def crear_cliente(): 
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


@clientes_bp.route('/dni/<string:dni>', methods=['GET'])
def obtener_cliente_por_dni(dni): # → Endpoint para buscar cliente por DNI
    if not dni or len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos numéricos'}), 400
    
    cliente = crud.obtener_cliente_por_dni(dni)
    
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado', 'dni': dni}), 404
    
    # Verificar si tiene préstamo activo
    from app.prestamos.model.prestamos import Prestamo, EstadoPrestamoEnum
    prestamo_activo = Prestamo.query.filter_by(
        cliente_id=cliente.cliente_id,
        estado=EstadoPrestamoEnum.VIGENTE
    ).first()
    
    cliente_data = cliente.to_dict()
    cliente_data['tiene_prestamo_activo'] = prestamo_activo is not None
    if prestamo_activo:
        cliente_data['prestamo_activo'] = {
            'id': prestamo_activo.prestamo_id,
            'monto': float(prestamo_activo.monto_total),
            'plazo': prestamo_activo.plazo,
            'fecha_otorgamiento': prestamo_activo.f_otorgamiento.isoformat() if prestamo_activo.f_otorgamiento else None
        }
    
    return jsonify(cliente_data), 200


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
