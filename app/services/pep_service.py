"""
PEP Service
Maneja la validación de Personas Expuestas Políticamente (PEP).
Centraliza la lógica de carga y consulta del dataset PEP.
"""

import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class PEPService:
    """Servicio para validación de clientes PEP"""
    
    # Cache del dataset PEP en memoria
    _dataset_pep = None
    _dataset_cargado = False
    
    @classmethod
    def cargar_dataset_pep(cls):
        """
        Carga el dataset PEP desde el archivo Excel.
        Mantiene el dataset en memoria para consultas rápidas.
        
        Returns:
            bool: True si se cargó exitosamente, False en caso contrario
        """
        if cls._dataset_cargado:
            return True
        
        try:
            BASE_DIR = Path(__file__).resolve().parent.parent.parent
            DATASET_PEP_PATH = BASE_DIR / "dataset-pep" / "Autoridades_Electas.xls"
            
            if not DATASET_PEP_PATH.exists():
                logger.error(f"Archivo PEP no encontrado: {DATASET_PEP_PATH}")
                return False
            
            # Cargar Excel
            df = pd.read_excel(DATASET_PEP_PATH)
            
            # Buscar columna de DNI
            columnas_posibles = ['DNI', 'DOCUMENTO', 'NRO_DOCUMENTO', 'NUMERO_DOCUMENTO', 'DOCUMENTOIDENTIDAD']
            col_dni = None
            
            for columna in columnas_posibles:
                if columna in df.columns:
                    col_dni = columna
                    break
            
            if not col_dni:
                logger.error(f"No se encontró columna DNI. Columnas disponibles: {df.columns.tolist()}")
                return False
            
            # Limpiar y normalizar DNIs
            df[col_dni] = df[col_dni].astype(str).str.strip()
            
            # Guardar en cache
            cls._dataset_pep = set(df[col_dni].tolist())
            cls._dataset_cargado = True
            
            logger.info(f"Dataset PEP cargado: {len(cls._dataset_pep)} registros")
            return True
            
        except Exception as e:
            logger.error(f"Error al cargar dataset PEP: {e}")
            return False
    
    @classmethod
    def validar_pep(cls, dni):
        """
        Valida si un DNI está en el dataset PEP.
        
        Args:
            dni: DNI del cliente (string)
            
        Returns:
            bool: True si el DNI está en el dataset PEP, False en caso contrario
        """
        # Cargar dataset si no está cargado
        if not cls._dataset_cargado:
            cls.cargar_dataset_pep()
        
        if not cls._dataset_cargado or cls._dataset_pep is None:
            logger.warning("Dataset PEP no disponible, asumiendo no-PEP")
            return False
        
        try:
            dni_limpio = str(dni).strip()
            es_pep = dni_limpio in cls._dataset_pep
            
            if es_pep:
                logger.info(f"DNI {dni} encontrado en dataset PEP")
            
            return es_pep
            
        except Exception as e:
            logger.error(f"Error al validar PEP para DNI {dni}: {e}")
            return False
    
    @classmethod
    def get_estadisticas(cls):
        """
        Obtiene estadísticas del dataset PEP.
        
        Returns:
            dict: Diccionario con estadísticas del dataset
        """
        if not cls._dataset_cargado:
            cls.cargar_dataset_pep()
        
        return {
            'cargado': cls._dataset_cargado,
            'total_registros': len(cls._dataset_pep) if cls._dataset_pep else 0
        }


# Cargar dataset al importar el módulo
PEPService.cargar_dataset_pep()
