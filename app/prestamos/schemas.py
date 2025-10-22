from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, FieldValidationInfo, field_validator

''' ESTA ES LA LÓGICA DEL CLIENTE
TENER EN CUENTA:
   templates : Vistas dinámicas 
   crud.py   : LÓGICA DE NEGOCIO
   routes.py : Rutas URL - endpoints
   schemas.py: Define la estructura y validación  ←------ ESTAMOS AQUÍ                            
q hay de nuevo?
    - SOLO SE HA AGREGADO el str de fecha_nacimiento'''

class PrestamoCreateDTO(BaseModel):
    dni: str = Field(..., description="Documento nacional de identidad del cliente")
    fecha_nacimiento: str = Field(..., description="Fecha de nacimiento del cliente")
    monto: Decimal = Field(..., description="Monto total del préstamo")
    interes_tea: Decimal = Field(..., description="Tasa Efectiva Anual en porcentaje")
    plazo: int = Field(..., description="Número de meses del crédito")
    f_otorgamiento: date = Field(..., description="Fecha de otorgamiento del préstamo")

    model_config = ConfigDict(anystr_strip_whitespace=True)

    @field_validator("dni")
    @classmethod
    def validar_dni(cls, value: str) -> str:
        if len(value) != 8 or not value.isdigit():
            raise ValueError("El DNI debe tener exactamente 8 dígitos numéricos")
        return value

    @field_validator("monto", "interes_tea")
    @classmethod
    def validar_decimales_positivos(cls, value: Decimal, info: FieldValidationInfo) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError(f"{info.field_name} debe ser mayor que cero")
        return value

    @field_validator("plazo")
    @classmethod
    def validar_plazo(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("plazo debe ser mayor a cero")
        return value

    @field_validator("f_otorgamiento")
    @classmethod
    def validar_fecha(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("La fecha de otorgamiento no puede ser futura")
        return value