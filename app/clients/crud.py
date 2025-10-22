from app import db
from app.clients.model.clients import Cliente
from app.prestamos.model.prestamos import Prestamo
from pathlib import Path
from datetime import date, datetime
import requests
import os
import pandas as pd

''' ESTA ES LA LÓGICA DEL CLIENTE
TENER EN CUENTA:
   templates : Vistas dinámicas 
   crud.py   : LÓGICA DE NEGOCIO ←------ ESTAMOS AQUÍ 
   routes.py : Rutas URL - endpoints
Te preguntarás: ¿Qué hace esta lógica? xd
   - Gestión de Clientes
       - Verifica si ya es un cliente registrado 
       - En caso que no: Se crea al cliente 
           - Valida que la fecha ingresada en pantalla sea mayor de edad
           - Se valida con la API → Se valida con la dataset si es PEP
               - El cliente debe declarar si es PEP o no para proceder con validaciones (En caso que no aparezca en la dataset)
           - No se guarda hasta que se registre un préstamo
   - Listamientos, Eliminación, Actualización, Enpaginamientos, etc etc etc LEE EL CÓDIGO '''

API_KEY = os.environ.get('DNI_API_KEY')
API_URL = os.environ.get('DNI_API_URL')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATASET_PEP_PATH = BASE_DIR / "dataset-pep" / "Autoridades_Electas.xls"

def validar_mayor_edad(fecha_nacimiento_str, edad_minima = 18):
    try:
        fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d").date()
    except ValueError:
        return None, "Formato Incorrecto - escribe bien"

    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

    if edad < edad_minima:
        return False, f"El cliente tiene que ser mayor de edad. Edad actual: {edad}."

    return True, None

def cargar_lista_pep():
    try:
        df = pd.read_excel(DATASET_PEP_PATH)  # -> Usamos pandas para leer datos
        col_dni = 'DOCUMENTOIDENTIDAD'  # -> Definimos el nombre de la columna
        # Verificamos que la columna exista - Respaldo en caso de cambio de dataset
        if col_dni not in df.columns:
            print(f"Error: La columna '{col_dni}' no se encontró en el dataset PEP.")
            print(f"Columnas disponibles: {list(df.columns)}")  # Muestra las posibles columnas
            return set()

        # Convertir DNIs a strings de 8 digitos y crear set
        dnis_pep = set(
            df[col_dni]
            .astype(str)  # Convierte todos los valores en String
            .str.strip()  # Elimina espacios en blanco
            .str.zfill(8)  # Rellenar con ceros a la izquierda si es necesario
        )

        print(f"Dataset PEP cargado: {len(dnis_pep)} registros")
        return dnis_pep

    except FileNotFoundError:
        print(f"Archivo PEP no encontrado: {DATASET_PEP_PATH}")
        return set()
    except Exception as e:
        print(f"Error al cargar dataset PEP: {e}")
        return set()

# Cargar lista PEP al iniciar el módulo (cache en memoria)
LISTA_PEP = cargar_lista_pep()

def validar_pep_en_dataset(dni): # → Validar si un DNI está en el dataset PEP
    dni_normalizado = str(dni).strip().zfill(8)
    return dni_normalizado in LISTA_PEP

def consultar_dni_api(dni): # → Consulta la API externa para obtener datos del DNI
    try:
        # Construir URL con parametro de consulta
        url_completa = f"{API_URL}/{dni}"

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        # Se realiza la solicitud GET a la API usando requests
        respuesta = requests.get(url_completa, headers=headers, timeout=10)
        
        # Verificar que la respuesta sea JSON
        content_type = respuesta.headers.get('Content-Type', '')
        if 'application/json' not in content_type: # Si no es JSON -
            return None, "Error de formato - no es JSON"
        
        respuesta.raise_for_status() # → 404 o 500
        api_data = respuesta.json()  # → Se convierte el JSON al diccionario Python (dict)
        # Verificar si la consulta fue exitosa
        if not api_data.get("success", False):
            mensaje = api_data.get("message", "DNI no encontrado en RENIEC")
            return None, mensaje
        # Se accede al campo data del JSON
        data = api_data.get('data', {}) # → {} diccionario vacío para evitar errores
        # Se crea un nuevo diccionario con los datos importantes del cliente
        datos_normalizados = {
            'nombres': data.get('nombres', ''),
            'apellido_paterno': data.get('apellido_paterno', ''),
            'apellido_materno': data.get('apellido_materno', ''),
            'nombre_completo': data.get('nombre_completo', ''),
            'numero': data.get('numero', dni)
        }
        # Si fue bien se devuelve los datos del cliente y None en el campo de error
        return datos_normalizados, None
        
    except requests.exceptions.Timeout: # Si cumple con el tiempo de 10 seg. (timeout)
        return None, "Tiempo de espera agotado al consultar RENIEC"
    except requests.exceptions.RequestException as e: # Cualquier error relacionado con la solicitud
        return None, f"Error de conexion con RENIEC: {str(e)}"
    except Exception as e: # Cualquier otro error que no sea por conexión
        return None, f"Error al consultar DNI: {str(e)}"

def crear_cliente(dni, pep_declarado, fecha_nacimiento): # → Crea un nuevo cliente consultando la API de DNI
    es_valido, mensaje_error = validar_mayor_edad(fecha_nacimiento)
    if not es_valido:
        return None, mensaje_error
    # info_cliente recepciona los datos Json que encuentren en la API, en caso de estar vacío retorna un None
    info_cliente, error = consultar_dni_api(dni)
    if error:
        return None, error # → retorna un mensaje de "DNI no encontrado"
    # Crear cliente
    try:
        # Lógica de validación de PEP
        es_pep_validado = validar_pep_en_dataset(dni)
        pep_final = es_pep_validado or pep_declarado
        # Creamos cliente en memoria (Temporal hasta proceder con el préstamo)
        nuevo_cliente = Cliente(
            dni=dni,
            nombre_completo=info_cliente.get('nombres', ''),
            apellido_paterno=info_cliente.get('apellido_paterno', ''),
            apellido_materno=info_cliente.get('apellido_materno', ''),
            pep=pep_final
        )
        # Preparación de metadatos
        pep_data ={
        'pep_declarado' : pep_declarado,           # ¿Es o no es PEP?
        'pep_validado_dataset' : es_pep_validado,  # Que se visualizó en el dataset
        'pep_final' : pep_final                    # Resultado declarado por el cliente
        }
        # Retorna el objeto ORM y los metadatos PEP - guardados temporalmente hasta el préstamo
        return nuevo_cliente, pep_data
        
    except Exception as e: # Captura errores que se puedan presentar en la inicialización del objeto cliente
        return None, f"Error en la preparación de los datos del cliente: {str(e)}"

def listar_clientes(): # → Lista todos los clientes
    return Cliente.query.all()

def obtener_cliente_por_id(cliente_id): # → Obtiene un cliente por su ID
    return Cliente.query.get(cliente_id)

def obtener_cliente_por_dni(dni): # → Obtener cliente por DNI
    return Cliente.query.filter_by(dni=dni).first()

def prestamo_activo_cliente(cliente_id, estado): #→ Verifica si un cliente tiene un préstamo en X estado
    return db.session.execute(
        db.select(Prestamo)
        .filter_by(cliente_id=cliente_id, estado=estado)
    ).scalar_one_or_none()
    
def obtener_clientes_por_estado_prestamo(): # Clientes con al menos un préstamo registrado
    return db.session.execute(
        db.select(Cliente)
        .join(Prestamo)
        .distinct()
        .order_by(Cliente.nombre_completo.asc())
    ).scalars().all()

def actualizar_cliente(cliente_id, pep=None): # → Actualizar los datos de un cliente
    cliente = Cliente.query.get(cliente_id) # Se hace la consulta con query mediante ID en la BD
    if not cliente: # Si no se encuentra el cliente a actualizar arroja el mensaje que no fue encontrado
        return None, "Cliente no encontrado"
    try:
        if pep is not None: # Si pep no es None
            cliente.pep = pep # Pues, la variable local ´pep´ se le asigna al atributo pep de cliente
        db.session.commit() # Guarda todas las sesiones pendientes permanentemente en la BD
        return cliente, None # Si el commit tiene éxito, la función retorna el objeto cliente y el valor None
    except Exception as e: # la variable e guarda guarda cualquier error de tipo Exception
        db.session.rollback() # Revierte todos los posibles cambios
        return None, f"Error al actualizar: {str(e)}"

def eliminar_cliente(cliente_id): # -> Eliminar un cliente por su ID
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return False, "Cliente no encontrado"
    try:
        db.session.delete(cliente) # En la misma sesión activa se ejecuta la eliminación de este cliente (por ID)
        db.session.commit() # Guarda los cambios realizados en la BD
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, f"Error al eliminar: {str(e)}"

def gestion_cliente(dni, fecha_nacimiento):
    # Se busca obtener el cliente en la BD mediante DNI
    cliente_existente = obtener_cliente_por_dni(dni)
    if cliente_existente:
        # Cliente ya existe en BD - retornar con metadata None
        return cliente_existente, None
    
    # Cliente no existe - crear en memoria
    # crear_cliente retorna: (cliente_obj, pep_data) si OK, (None, error_msg) si falla
    cliente_nuevo, resultado = crear_cliente(dni, pep_declarado=False, fecha_nacimiento=fecha_nacimiento)
    
    # Si cliente_nuevo es None, entonces resultado es un mensaje de error
    if cliente_nuevo is None:
        error_msg = resultado
        # Errores que indican problemas de servicio o API
        errores_servidor = ["Tiempo de espera agotado", "Error de conexion", "Error al consultar DNI", "Error en la preparación"]

        # Revisar si el error es de servidor/conexión
        if any(err in error_msg for err in errores_servidor):
            return None, "El servidor de identificación está caído. Intente de nuevo más tarde o contacte a soporte."
        # Retornar el mensaje original (ej: "DNI no encontrado")
        return None, error_msg
    # Cliente creado exitosamente en memoria
    # resultado contiene el diccionario pep_data
    return cliente_nuevo, resultado

def obtener_clientes_paginados(page=1, per_page=10, dni=None): # No está siendo usado por el momento
    # Consulta base usando el ORM
    query = Cliente.query
    if dni:
        # Busquedas parciales, si solo colocamos, por ejemplo: 7230 y buscamos
        # En teoría nos debería de aparecer todos los DNI que comiencen con 7230
        query = query.filter(Cliente.dni.ilike(f'%{dni}%'))
    # Ordena el conjunto de forma descendente
    return query.order_by(Cliente.fecha_registro.desc()).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )

def obtener_clientes_con_prestamos_info(page=1, per_page=10, dni=None): # Información de Prétamos
    from sqlalchemy import func, case
    from app.cuotas.model.cuotas import Cuota
    from app.prestamos.model.prestamos import EstadoPrestamoEnum

    query = db.session.query(
        Cliente,
        # En caso de no haber prestamos "coalesce" obliga a utilizar el segundo arguemento que es 0 (evitar el NULL)
        func.coalesce(func.sum(Prestamo.monto_total), 0).label('monto_total_prestado'),
        func.count(func.distinct(Prestamo.prestamo_id)).label('total_prestamos'),
        func.count(Cuota.cuota_id).label('total_cuotas'),
        func.coalesce(func.count(func.distinct(
            case((Prestamo.estado == EstadoPrestamoEnum.VIGENTE, Prestamo.prestamo_id))
        )), 0).label('prestamos_vigentes')
    ).outerjoin( # Une la tabla clientes con la tabla préstamo - OuterJoin incluye a los que NO tiene préstamos
        Prestamo, Cliente.cliente_id == Prestamo.cliente_id
    ).outerjoin( # Une el resultado anterior con la cuota
        Cuota, Prestamo.prestamo_id == Cuota.prestamo_id
    ).group_by(Cliente.cliente_id) # Agrupa por cada ID del cliente
    
    if dni:
        query = query.filter(Cliente.dni.ilike(f'%{dni}%'))
    # Ordena la consulta para agregar a los clientes más recientes primero
    query = query.order_by(Cliente.fecha_registro.desc())
    # Devuelve un objeto de paginación que contiene los resultados los resultados solicitados
    return query.paginate(page=page, per_page=per_page, error_out=False)