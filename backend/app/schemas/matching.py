from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    """
    HU-07: Esquema de entrada para el cálculo de idoneidad.
    Recibe el perfil estructurado del candidato y los requisitos estructurados de la vacante.
    """

    candidate_data: dict = Field(
        ...,
        description=(
            "Perfil estructurado del candidato (salida de HU-04). "
            "Debe incluir cargo_objetivo, anios_experiencia, habilidades, "
            "nivel_estudios e idiomas como mínimo."
        ),
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
        description=(
            "Requisitos estructurados de la vacante (salida de HU-06). "
            "Debe incluir cargo, anios_experiencia_requeridos, habilidades_clave, "
            "nivel_estudios e idiomas."
        ),
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


class MatchResponse(BaseModel):
    """
    HU-07: Esquema de salida con el resultado del Matching Engine.
    """

    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Score de idoneidad del candidato respecto a la vacante (0 a 100).",
    )
    justification: str = Field(
        ...,
        description=(
            "Justificación detallada del score otorgado, desglosada por "
            "los tres ejes de evaluación: experiencia/cargo, habilidades técnicas "
            "y nivel de estudios/idiomas."
        ),
    )
    breakdown: dict = Field(
        default_factory=dict,
        description=(
            "Desglose numérico del puntaje por eje de evaluación. "
            "Claves esperadas: 'experiencia_cargo' (0-40), "
            "'habilidades_tecnicas' (0-40), 'estudios_idiomas' (0-20)."
        ),
    )
