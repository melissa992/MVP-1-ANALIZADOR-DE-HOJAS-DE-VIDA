import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.schemas.matching import MatchResponse
from app.schemas.candidate import (
    CandidateDetailResponse,
    CandidateExplanation,
)
from app.schemas.ranking import CandidateRankingItem, VacancyRankingResponse
from app.schemas.vacancy import VacancyResponse
from app.storage import STORAGE_DIR

SortField = Literal["candidate_name", "score", "experience_years"]
SortOrder = Literal["asc", "desc"]


class RankingService:
    """Lee y persiste resultados de matching junto a las vacantes de temp_storage."""

    def __init__(self, storage_dir: str = str(STORAGE_DIR)) -> None:
        self.storage_dir = Path(storage_dir)

    def get_vacancy_ranking(
        self,
        vacancy_id: str,
        min_score: int = 0,
        max_score: int = 100,
        skill: str | None = None,
        sort_by: SortField = "score",
        order: SortOrder = "desc",
        vacancy: VacancyResponse | None = None,
    ) -> VacancyRankingResponse:
        if not 0 <= min_score <= max_score <= 100:
            raise ValueError("El rango de score debe estar entre 0 y 100.")
        if sort_by not in {"candidate_name", "score", "experience_years"}:
            raise ValueError(f"Columna de ordenamiento no válida: {sort_by}.")
        if order not in {"asc", "desc"}:
            raise ValueError(f"Dirección de ordenamiento no válida: {order}.")

        vacancy = vacancy or self._load_vacancy(vacancy_id)
        if vacancy is None:
            raise FileNotFoundError(f"No se encontró la vacante {vacancy_id}.")

        normalized_skill = skill.strip().casefold() if skill and skill.strip() else None
        candidates = []
        vacancy_key = hashlib.sha256(vacancy_id.encode("utf-8")).hexdigest()
        for record_path in self.storage_dir.glob(f"ranking_{vacancy_key}_*.json"):
            with record_path.open(encoding="utf-8") as record_file:
                data = json.load(record_file)
            if str(data.get("vacancy_id")) != vacancy_id:
                continue

            candidate = CandidateRankingItem(**data["candidate"])
            if not min_score <= candidate.score <= max_score:
                continue
            if normalized_skill and not any(
                normalized_skill == matching_skill.casefold()
                for matching_skill in candidate.matching_skills
            ):
                continue
            candidates.append(candidate)

        candidates.sort(
            key=lambda candidate: (
                getattr(candidate, sort_by).casefold()
                if sort_by == "candidate_name"
                else getattr(candidate, sort_by)
            ),
            reverse=order == "desc",
        )
        return VacancyRankingResponse(
            vacancy_id=vacancy_id,
            vacancy_title=vacancy.title,
            total_candidates=len(candidates),
            candidates=candidates,
        )

    def save_match_result(
        self,
        vacancy: VacancyResponse,
        candidate_data: dict,
        match_result: MatchResponse,
    ) -> CandidateRankingItem:
        candidate_json = json.dumps(
            candidate_data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        candidate_id = hashlib.sha256(candidate_json.encode("utf-8")).hexdigest()
        candidate_name = (
            candidate_data.get("nombre_completo")
            or candidate_data.get("candidate_name")
            or "Candidato sin nombre"
        )
        candidate = CandidateRankingItem(
            candidate_id=candidate_id,
            candidate_name=str(candidate_name).strip() or "Candidato sin nombre",
            score=match_result.score,
            experience_years=self._experience_years(candidate_data),
            matching_skills=self._matching_skills(match_result),
            match_level=self._match_level(match_result.score),
        )

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        vacancy_key = hashlib.sha256(str(vacancy.id).encode("utf-8")).hexdigest()
        record_path = self.storage_dir / f"ranking_{vacancy_key}_{candidate_id}.json"
        temporary_path = record_path.with_suffix(".tmp")
        record = {
            "vacancy_id": str(vacancy.id),
            "candidate": candidate.model_dump(),
            "candidate_data": candidate_data,
            "match_result": match_result.model_dump(mode="json"),
        }
        temporary_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(record_path)
        return candidate

    def get_candidate_detail(
        self,
        candidate_id: str,
        vacancy_id: str,
        vacancy: VacancyResponse | None = None,
    ) -> CandidateDetailResponse | None:
        if not re.fullmatch(r"[a-f0-9]{64}", candidate_id):
            return None
        vacancy = vacancy or self._load_vacancy(vacancy_id)
        if vacancy is None:
            return None

        vacancy_key = hashlib.sha256(vacancy_id.encode("utf-8")).hexdigest()
        detail_path = self.storage_dir / f"ranking_{vacancy_key}_{candidate_id}.json"
        if not detail_path.is_file():
            return None
        with detail_path.open(encoding="utf-8") as detail_file:
            record = json.load(detail_file)
        if (
            str(record.get("vacancy_id")) != vacancy_id
            or not isinstance(record.get("candidate_data"), dict)
            or not isinstance(record.get("match_result"), dict)
        ):
            return None

        profile = record["candidate_data"]
        match_result = MatchResponse(**record["match_result"])
        name = (
            profile.get("nombre_completo")
            or profile.get("candidate_name")
            or record.get("candidate", {}).get("candidate_name")
            or "Candidato sin nombre"
        )
        experience = profile.get("experiencia")
        if not isinstance(experience, list):
            experience = []
        education = profile.get("educacion")
        if not isinstance(education, list):
            education = []
        skills = profile.get("habilidades")
        if not isinstance(skills, list):
            skills = []
        languages = profile.get("idiomas")
        if not isinstance(languages, list):
            languages = []

        strengths = [
            self._format_requirement(item, "Cumplido")
            for item in match_result.requirements_met
        ]
        gaps = [
            self._format_requirement(item, "Parcial")
            for item in match_result.requirements_partial
        ] + [
            self._format_requirement(item, "Faltante")
            for item in match_result.requirements_missing
        ]
        first_experience = next(
            (item for item in experience if isinstance(item, dict)), {}
        )
        cargo = (
            profile.get("cargo_objetivo")
            or first_experience.get("cargo")
            or vacancy.title
        )
        education_level = (
            profile.get("nivel_estudios")
            or profile.get("education_level")
            or ", ".join(
                str(item.get("titulo"))
                for item in education
                if isinstance(item, dict) and item.get("titulo")
            )
            or "No especificado"
        )

        return CandidateDetailResponse(
            candidate_id=candidate_id,
            candidate_name=str(name),
            email=profile.get("correo") or profile.get("email"),
            phone=profile.get("telefono") or profile.get("phone"),
            experience_years=self._experience_years(profile),
            skills=[str(value) for value in skills if value],
            education_level=str(education_level),
            languages=[str(value) for value in languages if value],
            score=match_result.score,
            breakdown=match_result.breakdown.model_dump(),
            explanation=CandidateExplanation(
                puntos_fuertes=strengths,
                brechas_detectadas=gaps,
                justificacion_resumida=match_result.justification,
            ),
            vacancy_title=vacancy.title,
            cargo=str(cargo),
            experience=experience,
            education=education,
        )

    @staticmethod
    def _format_requirement(requirement, status: str) -> str:
        return (
            f"{status}: {requirement.requirement} "
            f"(evidencia: {requirement.evidence})"
        )

    def _load_vacancy(self, vacancy_id: str) -> VacancyResponse | None:
        if not re.fullmatch(r"[A-Za-z0-9-]+", vacancy_id):
            return None
        vacancy_path = self.storage_dir / f"vacancy_{vacancy_id}.json"
        if not vacancy_path.is_file():
            return None
        with vacancy_path.open(encoding="utf-8") as vacancy_file:
            return VacancyResponse(**json.load(vacancy_file))

    @staticmethod
    def _experience_years(candidate_data: dict) -> int:
        raw_years = candidate_data.get("anios_experiencia")
        if raw_years is not None:
            match = re.search(r"\d+(?:[.,]\d+)?", str(raw_years))
            if match:
                return max(0, int(float(match.group().replace(",", "."))))

        periods = []
        for experience in candidate_data.get("experiencia", []):
            if not isinstance(experience, dict):
                continue
            start = re.match(r"(\d{4})-(\d{2})", str(experience.get("fecha_inicio", "")))
            end_value = str(experience.get("fecha_fin", ""))
            end = re.match(r"(\d{4})-(\d{2})", end_value)
            if start:
                start_year, start_month_number = map(int, start.groups())
                if not 1 <= start_month_number <= 12:
                    continue
                start_month = start_year * 12 + start_month_number
                end_month = (
                    int(end.group(1)) * 12 + int(end.group(2))
                    if end
                    else datetime.now().year * 12 + datetime.now().month
                )
                if end_month >= start_month:
                    periods.append((start_month, end_month))

        total_months = 0
        current_end: int | None = None
        for start_month, end_month in sorted(periods):
            if current_end is None or start_month > current_end:
                total_months += end_month - start_month
                current_end = end_month
            elif end_month > current_end:
                total_months += end_month - current_end
                current_end = end_month
        return total_months // 12

    @staticmethod
    def _matching_skills(match_result: MatchResponse) -> list[str]:
        skills = []
        seen = set()
        for requirement in (
            *match_result.requirements_met,
            *match_result.requirements_partial,
        ):
            if requirement.category != "habilidades":
                continue
            normalized = requirement.requirement.casefold()
            if normalized not in seen:
                skills.append(requirement.requirement)
                seen.add(normalized)
        return skills

    @staticmethod
    def _match_level(score: int) -> Literal["high", "medium", "low"]:
        if score >= 80:
            return "high"
        if score >= 50:
            return "medium"
        return "low"


ranking_service = RankingService()
