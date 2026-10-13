from typing import List, Literal

from pydantic import BaseModel, Field


class CandidateRankingItem(BaseModel):
    candidate_id: str
    candidate_name: str
    score: int = Field(..., ge=0, le=100)
    experience_years: int = Field(..., ge=0)
    matching_skills: List[str]
    match_level: Literal["high", "medium", "low"]


class VacancyRankingResponse(BaseModel):
    vacancy_id: str
    vacancy_title: str
    total_candidates: int
    candidates: List[CandidateRankingItem]
