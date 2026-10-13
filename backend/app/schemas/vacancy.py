from datetime import datetime, timezone
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VacancyCreate(BaseModel):
    """
    Esquema de entrada para el registro de una nueva vacante (HU-05).
    """
    title: str = Field(
        ...,
        min_length=1,
        description="Título o cargo de la vacante",
        examples=["Desarrollador Backend Senior"]
    )
    raw_description: str = Field(
        ...,
        min_length=1,
        description="Descripción textual detallada del puesto y requerimientos",
        examples=["Buscamos desarrollador con experiencia en Python, FastAPI y bases de datos relacionales..."]
    )


class VacancyRequirements(BaseModel):
    """
    Esquema de requisitos estructurados extraídos por el LLM (HU-06).
    """
    cargo: str = Field(
        ...,
        description="Nombre o título estandarizado del cargo requerido"
    )
    anios_experiencia_requeridos: int = Field(
        default=0,
        ge=0,
        description="Años mínimos de experiencia laboral requeridos"
    )
    habilidades_clave: List[str] = Field(
        default_factory=list,
        description="Lista de habilidades técnicas y competencias principales"
    )
    idiomas: List[str] = Field(
        default_factory=list,
        description="Lista de idiomas requeridos o deseables"
    )
    nivel_estudios: str = Field(
        default="No especificado",
        description="Nivel educativo o titulación requerida"
    )


class VacancyResponse(BaseModel):
    """
    Esquema de salida tras registrar o procesar una vacante (HU-05 / HU-06).
    """
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, str] = Field(..., description="Identificador único de la vacante")
    title: str = Field(..., description="Título o cargo de la vacante")
    raw_description: str = Field(..., description="Descripción original del puesto")
    status: str = Field(default="pending_processing", description="Estado de procesamiento de la vacante")
    structured_requirements: Optional[VacancyRequirements] = Field(
        default=None,
        description="Requisitos estructurados extraídos mediante IA (HU-06)"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha y hora de creación de la vacante en formato UTC"
    )
