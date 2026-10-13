from datetime import datetime, timezone
from typing import Union
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


class VacancyResponse(BaseModel):
    """
    Esquema de salida tras registrar una vacante (HU-05).
    """
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, str] = Field(..., description="Identificador único de la vacante")
    title: str = Field(..., description="Título o cargo de la vacante")
    raw_description: str = Field(..., description="Descripción original del puesto")
    status: str = Field(default="pending_processing", description="Estado de procesamiento de la vacante")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha y hora de creación de la vacante en formato UTC"
    )
