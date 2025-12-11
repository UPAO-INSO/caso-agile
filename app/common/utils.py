"""
Common Utilities
Funciones de utilidad compartidas.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Importar servicio financiero para reutilizar lógica
from app.services.financial_service import FinancialService

# Valor de la UIT (Unidad Impositiva Tributaria) - Perú 2025
UIT_VALOR = Decimal('5350.00')

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)