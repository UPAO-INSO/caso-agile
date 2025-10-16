from app import db
from app.declaraciones.model.declaraciones import DeclaracionJurada, TipoDeclaracionEnum
from app.prestamos.model.prestamos import Prestamo 
from app.clients.model.clients import Cliente 
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import joinedload
from babel.dates import format_date

# Aquí usamos el valor de ejemplo para que la función sea autónoma en el CRUD.
VALOR_UIT = Decimal(5150) 
# Importa tu función de utilidad para convertir números a letras
# from app.common.utils import numero_a_letras # Asume que existe

def crear_declaracion(declaracion):
    """
    Guarda una nueva DeclaracionJurada en la base de datos.
    Nota: La función original tenía un error: db.session.add no devuelve el modelo.
    Se corrige devolviendo el objeto que se añade.
    """
    try:
        db.session.add(declaracion)
        db.session.commit()
        # Devuelve el objeto declarado
        return declaracion, None
    
    except Exception as e:
        db.session.rollback()
        # Usamos el mensaje más general de tu borrador
        return None, f"Error al guardar la declaración: {str(e)}"
    
# Función de ejemplo simple para convertir número a letras
def numero_a_letras(numero):
    """
    Convierte Decimal a texto en letras (es). Devuelve texto en mayúsculas.
    Maneja parte entera y céntimos.
    """
    try:
        from num2words import num2words
    except ImportError:
        def _num2words(n): return str(n)
    else:
        def _num2words(n): return num2words(n, lang='es')

    # Asegurar Decimal
    if not isinstance(numero, Decimal):
        numero = Decimal(str(numero))
    entero = int(numero.quantize(Decimal('1'), rounding='ROUND_FLOOR'))
    centavos = int((numero - Decimal(entero)) * 100)
    letras_entero = _num2words(entero).upper()
    return f"{letras_entero} {centavos:02d}/100"

# --- FUNCIÓN MEJORADA PARA GENERAR DATOS DE LA DJ (UNIFICADA) ---

def obtener_datos_dj_por_prestamo(prestamo_id):
    """
    Obtiene el Prestamo, Cliente y genera el contenido unificado 
    para la Declaración Jurada, según el tipo (USO_PROPIO, PEP, o AMBOS).
    """
    # Usamos db.session.execute para consultas eficientes si es necesario, 
    # pero Prestamo.query.get es simple y directo si se tiene la relación eager-loaded.
    # Asumimos que las relaciones están configuradas para cargar cliente.
    prestamo = Prestamo.query.get(prestamo_id) 
    
    if not prestamo:
        # Aquí se realiza la consulta a la DB (permitido en el CRUD)
        prestamo = db.session.execute(
            db.select(Prestamo)
            .where(Prestamo.prestamo_id == prestamo_id)
            .options(db.joinedload(Prestamo.cliente))
        ).scalar_one_or_none()
        
        if not prestamo:
            return None, "Préstamo no encontrado."


    cliente = prestamo.cliente
    # Asume que UIT_VALOR se obtiene de app.common.utils o se define aquí (como VALOR_UIT)
    
    # 1. Determinar el Tipo de Declaración
    requiere_uso_propio = prestamo.monto_total > VALOR_UIT
    requiere_pep = cliente.pep

    if not requiere_uso_propio and not requiere_pep:
        return None, "El préstamo no requiere Declaración Jurada."
    
    tipo_declaracion_enum = TipoDeclaracionEnum.AMBOS
    if requiere_uso_propio and not requiere_pep:
        tipo_declaracion_enum = TipoDeclaracionEnum.USO_PROPIO
    elif requiere_pep and not requiere_uso_propio:
        tipo_declaracion_enum = TipoDeclaracionEnum.PEP
        
    # 2. Construir el Título y Subtítulo
    
    titulo = "DECLARACIÓN JURADA"
    subtitulo = ""
    if tipo_declaracion_enum == TipoDeclaracionEnum.USO_PROPIO:
        subtitulo = "Por Monto Superior a la UIT y Uso de Fondos"
    elif tipo_declaracion_enum == TipoDeclaracionEnum.PEP:
        subtitulo = "Por Condición de Persona Expuesta Políticamente (PEP)"
    elif tipo_declaracion_enum == TipoDeclaracionEnum.AMBOS:
        subtitulo = "Por Monto Superior a la UIT y Condición PEP (Uso de Fondos Lícitos)"
        
    # 3. Construir el Contenido de la Declaración (texto unificado)
    
    monto_q = prestamo.monto_total.quantize(Decimal('0.01'))
    monto_soles_str = f"S/ {monto_q:,} ({numero_a_letras(monto_q)} SOLES)"

    try:
        fecha_str = format_date(date.today(), "d 'de' MMMM 'de' y", locale='es')
    except Exception:
        fecha_str = date.today().strftime('%d de %B de %Y')
    
    # PÁRRAFO 1: Declaración de veracidad (Común)
    parrafo1 = f"""
Yo, **{cliente.nombre_completo} {cliente.apellido_paterno} {cliente.apellido_materno or ''}**, 
identificado(a) con Documento Nacional de Identidad (DNI) N.º {cliente.dni}, 
declaro bajo juramento que la información proporcionada en la presente solicitud de préstamo 
es veraz y completa.
"""
    
    # PÁRRAFO 2: Uso de Fondos (siempre incluido si se requiere DJ por UIT o AMBOS)
    if requiere_uso_propio or tipo_declaracion_enum == TipoDeclaracionEnum.AMBOS:
        parrafo2 = f"""
Declaro que el préstamo solicitado, por un monto total de **{monto_soles_str}**, 
será destinado exclusivamente para **uso propio y fines lícitos**, 
comprometiéndome a no emplear dichos fondos en actividades ilícitas, fraudulentas o contrarias a la ley.
"""
    else:
        parrafo2 = "" # No aplica si es solo por PEP
        
    # PÁRRAFO 3: Condición PEP (siempre incluido si se requiere DJ por PEP o AMBOS)
    if requiere_pep or tipo_declaracion_enum == TipoDeclaracionEnum.AMBOS:
        parrafo3 = """
Manifiesto bajo juramento que soy **Persona Expuesta Políticamente (PEP)**, 
de conformidad con la Ley N.º 30424 y las disposiciones legales vigentes. 
Me comprometo a informar oportunamente cualquier cambio en dicha condición 
a la entidad que otorga el préstamo.
"""
    else:
        parrafo3 = "" # No aplica si es solo por UIT

    # PÁRRAFO FINAL: Responsabilidad (Común)
    parrafo_final = """
Declaro bajo juramento que toda la información consignada es cierta y asumo plena 
responsabilidad administrativa, civil y/o penal en caso de falsedad o inexactitud.
"""

    # Unimos los párrafos relevantes
    contenido_completo = "\n".join(filter(None, [parrafo1.strip(), parrafo2.strip(), parrafo3.strip(), parrafo_final.strip()]))
    
    # Devolver todos los datos necesarios para la vista (render_template)
    return {
        'titulo': titulo,
        'subtitulo': subtitulo,
        'tipo': tipo_declaracion_enum,
        'cliente': cliente,
        'prestamo': prestamo,
        'fecha_documento': date.today().strftime('%d de %B de %Y'),
        'contenido_cuerpo': contenido_completo,
    }, None