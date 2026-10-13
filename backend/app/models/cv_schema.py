from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExperienceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cargo: Optional[str] = None
    empresa: Optional[str] = None
    fecha_inicio: Optional[str] = Field(None, description="Formato ISO 8601 (YYYY-MM)")
    fecha_fin: Optional[str] = Field(None, description="Formato ISO 8601 (YYYY-MM) o 'actualidad'")
    funciones: List[str] = Field(default_factory=list)
    ubicacion: Optional[str] = None


class EducationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: Optional[str] = None
    institucion: Optional[str] = None
    anio_graduacion: Optional[str] = None


class CandidateProfileSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre_completo: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None
    ubicacion: Optional[str] = None
    resumen_profesional: Optional[str] = None
    experiencia: List[ExperienceItem] = Field(default_factory=list)
    educacion: List[EducationItem] = Field(default_factory=list)
    habilidades: List[str] = Field(default_factory=list)
    idiomas: List[str] = Field(default_factory=list)

    @field_validator("habilidades", "idiomas", mode="after")
    def normalize_list_values(cls, v: List[str]) -> List[str]:
        """HU-04: Normaliza valores de lista en minúsculas y elimina duplicados."""
        if not v:
            return []

        normalized = {item.strip().lower() for item in v if item and item.strip()}
        return list(normalized)
