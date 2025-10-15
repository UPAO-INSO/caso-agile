from decimal import Decimal

from flask import request, jsonify, render_template

from app.clients import crud
from app.prestamos.model.prestamos import EstadoPrestamoEnum
from . import clientes_bp


def _build_cliente_response(cliente):
    prestamo_activo = crud.prestamo_activo_cliente(
        cliente.cliente_id,
        EstadoPrestamoEnum.VIGENTE
    )

    response = {
        'id': cliente.cliente_id,
        'cliente_id': cliente.cliente_id,
        'dni': cliente.dni,
        'nombre_completo': cliente.nombre_completo,
        'apellido_paterno': cliente.apellido_paterno,
        'apellido_materno': cliente.apellido_materno,
        'pep': cliente.pep,
        'tiene_prestamo_activo': prestamo_activo is not None,
        'prestamo_activo': None,
    }

    if prestamo_activo:
        response['prestamo_activo'] = {
            'id': prestamo_activo.prestamo_id,
            'monto': str(prestamo_activo.monto_total.quantize(Decimal('0.01'))),
            'plazo': prestamo_activo.plazo,
            'interes_tea': str(prestamo_activo.interes_tea.quantize(Decimal('0.01'))),
            'fecha_otorgamiento': prestamo_activo.f_otorgamiento.isoformat(),
            'estado': prestamo_activo.estado.value,
        }

    return response

@clientes_bp.route('', methods=['POST'])
def crear_cliente():

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


@clientes_bp.route('', methods=['GET'])
def listar_clientes():
    clientes = crud.listar_clientes()
    return jsonify([cliente.to_dict() for cliente in clientes]), 200


@clientes_bp.route('/dni/<string:dni>', methods=['GET'])
def obtener_cliente_por_dni_route(dni):
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400

    cliente = crud.obtener_cliente_por_dni(dni)

    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404

    return jsonify(_build_cliente_response(cliente)), 200


@clientes_bp.route('/consultar_dni/<string:dni>', methods=['GET'])
def consultar_dni_route(dni):
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400

    data, error = crud.consultar_dni_api(dni)

    if error:
        return jsonify({'error': error}), 404

    return jsonify(data), 200


@clientes_bp.route('/<int:cliente_id>', methods=['GET'])
def obtener_cliente(cliente_id):
    cliente = crud.obtener_cliente_por_id(cliente_id)
    
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    return jsonify(cliente.to_dict()), 200


@clientes_bp.route('/<int:cliente_id>', methods=['PUT'])
def actualizar_cliente(cliente_id):
    data = request.get_json()
    pep = data.get('pep')
    
    cliente, error = crud.actualizar_cliente(cliente_id, pep)
    
    if error:
        return jsonify({'error': error}), 404
    
    return jsonify(cliente.to_dict()), 200


@clientes_bp.route('/<int:cliente_id>', methods=['DELETE'])
def eliminar_cliente(cliente_id):
    exito, error = crud.eliminar_cliente(cliente_id)
    
    if not exito:
        return jsonify({'error': error}), 404
    
    return jsonify({'mensaje': f'Cliente con ID {cliente_id} eliminado correctamente'}), 200

@clientes_bp.route('/test/dni/<string:dni>', methods=['GET'])
def test_consultar_dni(dni):
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    
    info, error = crud.consultar_dni_api(dni)
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({'success': True, 'data': info}), 200


@clientes_bp.route('/consultar_pep/<string:dni>', methods=['GET'])
def test_validar_pep(dni):
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    
    es_pep = crud.validar_pep_en_dataset(dni)
    
    return jsonify({
        'dni': dni,
        'es_pep': es_pep,
        'mensaje': 'Este DNI está en la lista PEP' if es_pep else 'Este DNI NO está en la lista PEP'
    }), 200

@clientes_bp.route('/clientes', methods=['GET'])
def listar_clientes_view():
    page = request.args.get('page', 1, type=int)
    dni = request.args.get('dni', '')
    
    clientes = crud.paginar_clientes(page=page, per_page=5, dni=dni)
    return render_template('lista_clientes.html', clientes=clientes)