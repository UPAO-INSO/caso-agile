from flask import render_template, request, jsonify
import os
from app.clients.model.clients import Cliente
from app.clients import crud
from . import clientes_bp

''' ESTA ES LA RUTA ENTRE LA LÓGICA CON LA INTERFAZ 
TENER EN CUENTA:
    templates : Vistas dinámicas
    crud.py   : Lógica de Negocio 
    routes.py : RUTAS URL - ENDPOINTS ←------ ESTAMOS AQUÍ
Te preguntarás: ¿Qué hacen las rutas? xd
    - Contiene decoradores como @clientes_bp.route(...) que mapean peticiones HTTP a funciones de Python
    - Es la capa de comunicación que recibe y envía datos JSON
    - Central: crear_cliente()
        → Espera la llegada de sus peticiones - POST: dni, pep, declarado y fecha de nacimiento
        → Realiza las validaciones de datos (DNI y Fecha de Nacimiento obligatorios)
        → Con la petición validada, delega la creación del cliente a la lógica de negocio "crud.crear_cliente()"
    '''

# → Guardamos la API Key en variables de entorno
API_KEY = os.environ.get('DNI_API_KEY')
API_URL = os.environ.get('DNI_API_URL')

# ------------- ENDPOINTS CRUD PRINCIPALES-----------------------------

@clientes_bp.route('', methods=['POST']) # Asocia la función a la ruta base de blueprint - Creación
def crear_cliente(): # → Endpoint para crear un nuevo cliente
    data = request.get_json() # Recibe y valida los datos - peticiones web - formato JSON
    # Si no se recepciona el campo DNI rebota con el siguiente mensaje crudo (JSON)
    if not data or not data.get('dni') or not data.get('fecha_nacimiento'):
        return jsonify({'error': 'Los campos DNI y fecha_nacimiento son indispensables'}), 400
    # En caso si haya data se extrae el dni y el pep
    dni = data.get('dni')
    pep_declarado = data.get('pep', False)
    fecha_nacimiento = data.get('fecha_nacimiento')
    # Llama a la función de CRUD.py para guardar al cliente en la BD
    cliente_dict, error = crud.crear_cliente(dni, pep_declarado, fecha_nacimiento)

    if error:
        if "ya existe" in error:
            return jsonify({'error': error}), 409
        elif "no encontrado" in error:
            return jsonify({'error': error}), 404
        else:
            return jsonify({'error': error}), 503
    
    return jsonify(cliente_dict), 201 # → CreadoDJ

@clientes_bp.route('', methods=['GET']) # Lectura
def listar_clientes(): # → Endpoint para listar todos los clientes
    clientes = crud.listar_clientes() # → Lista los clientes de la BD llamando a la lógica del negocio
    # Convierte la lista en un diccionario JSON y la envía con codigo HTTP 200 - OK
    return jsonify([cliente.to_dict() for cliente in clientes]), 200

@clientes_bp.route('/<int:cliente_id>', methods=['GET'])
def obtener_cliente(cliente_id): # → Endpoint para obtener un cliente por ID
    cliente = crud.obtener_cliente_por_id(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    return jsonify(cliente.to_dict()), 200

@clientes_bp.route('/<int:cliente_id>', methods=['PUT'])
def actualizar_cliente(cliente_id): # → Endpoint para actualizar un cliente
    data = request.get_json() # → Recibir y Validar las peticiones web - JSON
    pep = data.get('pep') # De esa data se extrae si es pep
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


# -------------------------- ENDPOINT DE VALIDACIÓN Y BÚSQUEDA PARA EL FRONTEND ---------------------------------------

@clientes_bp.route('/validar_y_buscar', methods=['POST'])
def validar_y_buscar_cliente():
    # Recibimos los datos DNI y fecha de nacimiento en el cuerpo de la petición POST
    data = request.get_json()
    dni = data.get('dni')
    fecha_nacimiento = data.get('fecha_nacimiento')
    # Validamos los campos obligatorios para proceder
    if not dni or not fecha_nacimiento:
        return jsonify({'error': 'DNI y Fecha de Nacimiento son obligatorios'}), 400

    # Se utiliza la función de validación que definiste en el CRUD.
    es_valido, mensaje_error = crud.validar_mayor_edad(fecha_nacimiento)

    if not es_valido:
        # Detiene el proceso y retorna el mensaje de edad insuficiente o formato incorrecto (400)
        return jsonify({'error': mensaje_error}), 400

    # Si la edad es válida, procedemos con la búsqueda en BD
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400

    cliente = Cliente.query.filter_by(dni=dni).first()

    if not cliente:
        # El cliente no existe en la BD.
        return jsonify({'error': 'Cliente no encontrado en la BD.'}), 404

    # Obtener info de préstamo activo (si aplica)
    from app.prestamos.model.prestamos import Prestamo, EstadoPrestamoEnum
    prestamo_activo = Prestamo.query.filter_by(
        cliente_id=cliente.cliente_id,
        estado=EstadoPrestamoEnum.VIGENTE
    ).first()

    cliente_dict = cliente.to_dict()
    cliente_dict['tiene_prestamo_activo'] = prestamo_activo is not None
    return jsonify(cliente_dict), 200

# -------------------------- ENDPOINTS PARA EL FRONTEND ---------------------------------------

@clientes_bp.route('/dni/<string:dni>', methods=['GET']) # LECTURA
def buscar_cliente_por_dni(dni): # → Endpoint para buscar cliente por DNI
    if len(dni) != 8 or not dni.isdigit(): # Se valida que lo ingresado tenga 8 dígitos
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    # Busca en la BD al primer cliente que coincida con el DNI
    cliente = Cliente.query.filter_by(dni=dni).first()
    # Verificamos si se encontró en la BD
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    # Verificar si tiene prestamo activo
    # Importamos el modelo de otro módulo
    from app.prestamos.model.prestamos import Prestamo, EstadoPrestamoEnum
    # Se verifica en la BD si existe un préstamo asociado en este cliente
    prestamo_activo = Prestamo.query.filter_by(
        cliente_id=cliente.cliente_id,
        estado=EstadoPrestamoEnum.VIGENTE
    ).first()
    # Agrega una nueva clave al diccionario del cliente
    cliente_dict = cliente.to_dict()
    cliente_dict['tiene_prestamo_activo'] = prestamo_activo is not None
    # Envia los datos del cliente
    return jsonify(cliente_dict), 200

@clientes_bp.route('/consultar_dni/<string:dni>', methods=['GET']) # LECTURA
def consultar_dni_reniec(dni): # -> Endpoint para consultar DNI en la API externa
    if len(dni) != 8 or not dni.isdigit(): # Validación: Tienen que ser 8 dígitos exactos
        return jsonify({'error': 'DNI inválido. Debe tener 8 dígitos'}), 400
    # Se guarda en info la petición que se hace como primer argumento
    info, error = crud.consultar_dni_api(dni)
    # En caso que no encuentrra nada se procede con el segundo argumento "error"
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
    # Listamiento de 7 por página
    clientes_paginados = crud.obtener_clientes_con_prestamos_info(page=page, per_page=10, dni=dni)
    # Renderiza/genera la página HTML y envía los datos del cliente
    return render_template('lista_clientes.html', clientes=clientes_paginados)