from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.schemas.matching import MatchBreakdown


class CandidateExplanation(BaseModel):
    puntos_fuertes: List[str] = Field(default_factory=list)
    brechas_detectadas: List[str] = Field(default_factory=list)
    justificacion_resumida: str


class CandidateDetailResponse(BaseModel):
    candidate_id: str
    candidate_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    experience_years: int = Field(..., ge=0)
    skills: List[str] = Field(default_factory=list)
    education_level: str
    languages: List[str] = Field(default_factory=list)
    score: int = Field(..., ge=0, le=100)
    breakdown: Optional[MatchBreakdown] = None
    explanation: CandidateExplanation
    vacancy_title: str
    cargo: str
    experience: List[dict[str, Any]] = Field(default_factory=list)
    education: List[dict[str, Any]] = Field(default_factory=list)
