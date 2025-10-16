from app import db
import requests
import os
from app.clients.model.clients import Cliente
from app.prestamos.model.prestamos import Prestamo
import pandas as pd
from pathlib import Path

API_KEY = os.environ.get('DNI_API_KEY')
API_URL = os.environ.get('DNI_API_URL')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATASET_PEP_PATH = BASE_DIR / "dataset-pep" / "Autoridades_Electas.xls"

def cargar_lista_pep():
    try:
        df = pd.read_excel(DATASET_PEP_PATH)
        
        columnas_posibles = ['DNI', 'DOCUMENTO', 'NRO_DOCUMENTO', 'NUMERO_DOCUMENTO']
        col_dni = None
        
        for columna in columnas_posibles:
            if columna in df.columns:
                col_dni = columna
                break
        
        if not col_dni:
            # Si no encuentra, usar la primera columna que contenga números de 8 dígitos
            for columna in df.columns:
                if df[columna].dtype == 'object' or df[columna].dtype == 'int64':
                    # Verificar si los valores parecen DNIs (8 dígitos)
                    muestra = df[columna].astype(str).str.strip()
                    if muestra.str.len().mode()[0] == 8:
                        col_dni = columna
                        break
        
        if not col_dni:
            print(f"Advertencia: No se encontró columna de DNI en el dataset PEP")
            return set()
        
        # Convertir DNIs a strings de 8 dígitos y crear set
        dnis_pep = set(
            df[col_dni]
            .astype(str)
            .str.strip()
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


def consultar_dni_api(dni, correo_electronico=None): # → Consulta la API externa para obtener datos del DNI
    """
    Consulta API de APIPERU para obtener datos del DNI.
    Formato de respuesta esperado:
    {
        "success": true,
        "data": {
            "numero": "12345678",
            "nombre_completo": "JUAN PEREZ GARCIA",
            "nombres": "JUAN",
            "apellido_paterno": "PEREZ",
            "apellido_materno": "GARCIA",
            "codigo_verificacion": "1",
            "fecha_nacimiento": "01/01/1990",
            "ubigeo": "150101"
        }
    }
    """
    # Validar que las variables de entorno estén configuradas
    if not API_URL or not API_KEY:
        return None, "Error de configuración: Las credenciales de la API no están configuradas. Por favor, configure DNI_API_URL y DNI_API_KEY en las variables de entorno."
    
    try:
        # Construir URL con parametro de consulta
        url_completa = f"{API_URL}/{dni}"
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        respuesta = requests.get(url_completa, headers=headers, timeout=10)
        
        # Verificar que la respuesta sea JSON
        content_type = respuesta.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            return None, "DNI no encontrado en RENIEC"
        
        respuesta.raise_for_status()
        api_data = respuesta.json()
        
        # Verificar si la consulta fue exitosa
        if not api_data.get("success", False):
            mensaje = api_data.get("message", "DNI no encontrado en RENIEC")
            return None, mensaje
        
        # Obtener datos y normalizar formato
        data = api_data.get('data', {})
        
        # APIPERU devuelve los datos directamente
        datos_normalizados = {
            'nombres': data.get('nombres', ''),
            'apellido_paterno': data.get('apellido_paterno', ''),
            'apellido_materno': data.get('apellido_materno', ''),
            'nombre_completo': data.get('nombre_completo', ''),
            'numero': data.get('numero', dni)
        }
        
        # Solo agregar correo_electronico si se proporcionó
        if correo_electronico:
            datos_normalizados['correo_electronico'] = correo_electronico
        
        return datos_normalizados, None
        
    except requests.exceptions.Timeout:
        return None, "Tiempo de espera agotado al consultar RENIEC"
    except requests.exceptions.RequestException as e:
        return None, f"Error de conexion con RENIEC: {str(e)}"
    except Exception as e:
        return None, f"Error al consultar DNI: {str(e)}"

def crear_cliente(dni, correo_electronico, pep_declarado=False): # → Crea un nuevo cliente consultando la API de DNI
    # Validar si ya existe
    cliente_existente = Cliente.query.filter_by(dni=dni).first()
    if cliente_existente:
        return None, "El cliente ya existe"
    
    # Consultar API de Factiliza
    info_cliente, error = consultar_dni_api(dni, correo_electronico)
    if error:
        return None, error
    
    # Validar automáticamente contra dataset PEP
    es_pep_validado = validar_pep_en_dataset(dni)
    
    # Si el dataset dice que SÍ es PEP, prevalece la validación automática
    pep_final = es_pep_validado or pep_declarado
    
    # Crear cliente
    try:
        nuevo_cliente = Cliente(
            dni=dni,
            nombre_completo=info_cliente.get('nombre_completo', ''),
            apellido_paterno=info_cliente.get('apellido_paterno', ''),
            apellido_materno=info_cliente.get('apellido_materno', ''),
            correo_electronico=correo_electronico,
            pep=pep_final
        )
        
        db.session.add(nuevo_cliente)
        db.session.commit()
        
        # Preparar respuesta completa con información de validación
        cliente_dict = nuevo_cliente.to_dict()
        cliente_dict['pep_declarado'] = pep_declarado
        cliente_dict['pep_validado_dataset'] = es_pep_validado
        cliente_dict['pep_final'] = pep_final
        
        if pep_declarado != es_pep_validado:
            cliente_dict['advertencia'] = (
                "CUIDADO: El cliente declaró NO ser PEP pero está en el dataset oficial"
                if es_pep_validado else
                "El cliente declaró ser PEP pero no está en el dataset oficial (puede ser PEP por otros motivos)"
            )
        
        return cliente_dict, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error al guardar el cliente: {str(e)}"

def listar_clientes(): # → Lista todos los clientes
    return Cliente.query.all()

def obtener_cliente_por_id(cliente_id): # → Obtiene un cliente por su ID
    return Cliente.query.get(cliente_id)

def obtener_cliente_por_dni(dni): # → Obtener cliente por DNI
    return Cliente.query.filter_by(dni=dni).first()

def prestamo_activo_cliente(cliente_id, estado):
    return db.session.execute(
        db.select(Prestamo)
        .filter_by(cliente_id=cliente_id, estado=estado)
    ).scalar_one_or_none()
    
def obtener_clientes_por_estado_prestamo():
    return db.session.execute(
        db.select(Cliente)
        .join(Prestamo) 
        .distinct() 
        .order_by(Cliente.nombre_completo.asc())
    ).scalars().all()

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

def crear_o_obtener_cliente(dni): # → Crear o obtener un cliente por DNI
    """
    Obtiene un cliente existente o lo crea consultando RENIEC.
    Si el cliente ya fue consultado desde el frontend, usar crear_cliente_directo.
    """
    # Intentar obtener cliente existente
    cliente = Cliente.query.filter_by(dni=dni).first()
    if cliente:
        return cliente, None
    
    # Cliente no existe, intentar crear consultando RENIEC
    cliente_dict, error = crear_cliente(dni, cliente.correo_electronico, pep_declarado=False)
    
    if error:
        # Si falla la API, intentar crear con datos minimos
        if "no encontrado" in error or "Tiempo de espera" in error:
            try:
                # Crear cliente con datos basicos
                es_pep_validado = validar_pep_en_dataset(dni)
                nuevo_cliente = Cliente(
                    dni=dni,
                    nombre_completo=f"Cliente {dni}",
                    apellido_paterno="PENDIENTE",
                    apellido_materno="ACTUALIZACION",
                    pep=es_pep_validado
                )
                db.session.add(nuevo_cliente)
                db.session.commit()
                return nuevo_cliente, None
            except Exception as e:
                return None, f"Error al crear cliente: {str(e)}"
        return None, error
    
    # Obtener el cliente recién creado de la BD
    cliente = Cliente.query.filter_by(dni=dni).first()
    return cliente, None

def paginar_clientes(page=1, per_page=5, dni=None):
    query = Cliente.query
    
    if dni:
        query = query.filter(Cliente.dni.ilike(f'%{dni}%'))
        
    return query.order_by(Cliente.fecha_registro.desc()).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )

def obtener_clientes_con_prestamos_info(page=1, per_page=5, dni=None):
    """Obtiene clientes con información agregada de sus préstamos"""
    from sqlalchemy import func, case
    from app.cuotas.model.cuotas import Cuota
    from app.prestamos.model.prestamos import EstadoPrestamoEnum
    
    query = db.session.query(
        Cliente,
        func.coalesce(func.sum(Prestamo.monto_total), 0).label('monto_total_prestado'),
        func.count(func.distinct(Prestamo.prestamo_id)).label('total_prestamos'),
        func.count(Cuota.cuota_id).label('total_cuotas'),
        func.coalesce(func.count(func.distinct(
            case((Prestamo.estado == EstadoPrestamoEnum.VIGENTE, Prestamo.prestamo_id))
        )), 0).label('prestamos_vigentes')
    ).outerjoin(
        Prestamo, Cliente.cliente_id == Prestamo.cliente_id
    ).outerjoin(
        Cuota, Prestamo.prestamo_id == Cuota.prestamo_id
    ).group_by(Cliente.cliente_id)
    
    if dni:
        query = query.filter(Cliente.dni.ilike(f'%{dni}%'))
    
    query = query.order_by(Cliente.fecha_registro.desc())
    
    return query.paginate(page=page, per_page=per_page, error_out=False)