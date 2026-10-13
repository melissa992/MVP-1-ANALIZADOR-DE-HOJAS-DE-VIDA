from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class MatchRequest(BaseModel):
    """
    HU-07 / HU-08: entrada para comparar un perfil estructurado con una vacante.
    """

    candidate_data: dict = Field(
        ...,
        description="Perfil estructurado del candidato (salida de HU-04).",
        examples=[
            {
                "nombre_completo": "Laura Gómez",
                "cargo_objetivo": "Desarrolladora Backend",
                "anios_experiencia": 4,
                "habilidades": ["Python", "FastAPI", "PostgreSQL"],
                "idiomas": ["Español", "Inglés B2"],
                "nivel_estudios": "Profesional universitario",
            }
        ],
    )
    vacancy_data: dict = Field(
        ...,
        description="Requisitos estructurados de la vacante (salida de HU-06).",
        examples=[
            {
                "cargo": "Desarrollador Backend Senior",
                "anios_experiencia_requeridos": 3,
                "habilidades_clave": ["Python", "FastAPI", "Docker"],
                "idiomas": ["Inglés"],
                "nivel_estudios": "Profesional universitario",
            }
        ],
    )


class RequirementEvidence(BaseModel):
    category: Literal["habilidades", "experiencia", "educacion", "idiomas"]
    requirement: str = Field(..., min_length=1)
    evidence: str = Field(..., min_length=1)


class CategoryScore(BaseModel):
    score: int = Field(..., ge=0)
    max_score: int = Field(..., ge=0)

    @model_validator(mode="after")
    def score_does_not_exceed_maximum(self):
        if self.score > self.max_score:
            raise ValueError("El puntaje parcial no puede superar el máximo.")
        return self


class MatchBreakdown(BaseModel):
    habilidades: CategoryScore
    experiencia: CategoryScore
    educacion: CategoryScore
    idiomas: CategoryScore

    @model_validator(mode="after")
    def validate_category_weights(self):
        expected_maxima = {
            "habilidades": 40,
            "experiencia": 40,
            "educacion": 10,
            "idiomas": 10,
        }
        for category, expected_maximum in expected_maxima.items():
            if getattr(self, category).max_score != expected_maximum:
                raise ValueError(
                    f"El máximo para {category} debe ser {expected_maximum}."
                )
        return self


class MatchResponse(BaseModel):
    """
    HU-07 / HU-08: resultado, puntajes parciales y evidencia del matching.
    """

    score: int = Field(..., ge=0, le=100)
    justification: str = Field(
        ...,
        description="Justificación factual en español de un máximo de cinco líneas.",
    )
    breakdown: MatchBreakdown
    requirements_met: list[RequirementEvidence] = Field(default_factory=list)
    requirements_partial: list[RequirementEvidence] = Field(default_factory=list)
    requirements_missing: list[RequirementEvidence] = Field(default_factory=list)

    @field_validator("justification")
    @classmethod
    def validate_justification_lines(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La justificación no puede estar vacía.")
        if len(value.splitlines()) > 5:
            raise ValueError("La justificación no puede superar cinco líneas.")
        return value

    @model_validator(mode="after")
    def validate_score_total(self):
        category_scores = (
            self.breakdown.habilidades.score,
            self.breakdown.experiencia.score,
            self.breakdown.educacion.score,
            self.breakdown.idiomas.score,
        )
        if self.score != sum(category_scores):
            raise ValueError("El score total debe coincidir con la suma del desglose.")
        return self
