"""
Schemas de validación para Préstamos
Usando Pydantic para validación de datos
"""
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional


class PrestamoCreateDTO(BaseModel):
    """DTO para crear un nuevo préstamo"""
    dni: str = Field(..., min_length=8, max_length=8, description="DNI del cliente")
    correo_electronico: str = Field(..., description="Email del cliente")
    monto: Decimal = Field(..., gt=0, description="Monto del préstamo")
    interes_tea: Decimal = Field(..., ge=0, le=100, description="Tasa de interés anual")
    plazo: int = Field(..., gt=0, description="Plazo en meses")
    
    @field_validator('dni')
    @classmethod
    def validar_dni(cls, v):
        """Valida que el DNI sea numérico"""
        if not v.isdigit():
            raise ValueError('El DNI debe contener solo dígitos')
        return v
    
    @field_validator('correo_electronico')
    @classmethod
    def validar_email(cls, v):
        """Valida formato básico de email"""
        if '@' not in v:
            raise ValueError('Email inválido')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "dni": "12345678",
                "correo_electronico": "cliente@example.com",
                "monto": 10000.00,
                "interes_tea": 15.5,
                "plazo": 12
            }
        }
