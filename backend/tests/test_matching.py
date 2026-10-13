import json

import pytest

from app.services.matching_service import MatchingService


CANDIDATE = {
    "cargo_objetivo": "Desarrolladora Backend",
    "anios_experiencia": "2 años",
    "habilidades": ["Python"],
    "nivel_estudios": "Profesional universitario",
    "idiomas": ["Inglés B1"],
}

VACANCY = {
    "cargo": "Desarrolladora Backend",
    "anios_experiencia_requeridos": 3,
    "habilidades_clave": ["Python", "Docker"],
    "nivel_estudios": "Profesional universitario",
    "idiomas": ["Inglés B2"],
}

MODEL_RESULT = {
    "justification": (
        "El perfil incluye Python y formación profesional universitaria. "
        "Registra dos años de experiencia e inglés B1."
    ),
    "requirements_met": [
        {
            "category": "habilidades",
            "requirement": "Python",
            "evidence": "Python",
        },
        {
            "category": "experiencia",
            "requirement": "Cargo: Desarrolladora Backend",
            "evidence": "Desarrolladora Backend",
        },
        {
            "category": "educacion",
            "requirement": "Profesional universitario",
            "evidence": "Profesional universitario",
        },
    ],
    "requirements_partial": [
        {
            "category": "experiencia",
            "requirement": "3 años de experiencia",
            "evidence": "2 años",
        },
        {
            "category": "idiomas",
            "requirement": "Inglés B2",
            "evidence": "Inglés B1",
        },
    ],
    "requirements_missing": [
        {
            "category": "habilidades",
            "requirement": "Docker",
            "evidence": "Sin evidencia en el CV.",
        }
    ],
}


class FakeModels:
    def __init__(self, response_text):
        self.response_text = response_text

    def generate_content(self, **kwargs):
        return type("Response", (), {"text": self.response_text})()


class FakeClient:
    def __init__(self, response_text):
        self.models = FakeModels(response_text)


def service_with_result(result):
    service = MatchingService()
    service.max_attempts = 1
    service.client = FakeClient(json.dumps(result, ensure_ascii=False))
    return service


def test_calculate_fit_score_returns_category_breakdown_and_requirement_statuses():
    result = service_with_result(MODEL_RESULT).calculate_fit_score(CANDIDATE, VACANCY)

    assert result.score == 65
    assert result.breakdown.model_dump() == {
        "habilidades": {"score": 20, "max_score": 40},
        "experiencia": {"score": 30, "max_score": 40},
        "educacion": {"score": 10, "max_score": 10},
        "idiomas": {"score": 5, "max_score": 10},
    }
    assert [item.requirement for item in result.requirements_met] == [
        "Python",
        "Cargo: Desarrolladora Backend",
        "Profesional universitario",
    ]
    assert [item.requirement for item in result.requirements_partial] == [
        "3 años de experiencia",
        "Inglés B2",
    ]
    assert [item.requirement for item in result.requirements_missing] == ["Docker"]


def test_calculate_fit_score_rejects_evidence_not_present_in_candidate_profile():
    result = json.loads(json.dumps(MODEL_RESULT))
    result["requirements_met"][0]["evidence"] = "Kubernetes"

    with pytest.raises(RuntimeError, match="no aparece literalmente"):
        service_with_result(result).calculate_fit_score(CANDIDATE, VACANCY)


def test_calculate_fit_score_rejects_omitted_vacancy_requirements():
    result = json.loads(json.dumps(MODEL_RESULT))
    result["requirements_missing"] = []

    with pytest.raises(RuntimeError, match="omitió requisitos"):
        service_with_result(result).calculate_fit_score(CANDIDATE, VACANCY)


def test_match_response_rejects_justification_over_five_lines():
    from app.schemas.matching import MatchResponse

    with pytest.raises(ValueError, match="cinco líneas"):
        MatchResponse(
            score=0,
            justification="uno\ndos\ntres\ncuatro\ncinco\nseis",
            breakdown={
                "habilidades": {"score": 0, "max_score": 40},
                "experiencia": {"score": 0, "max_score": 40},
                "educacion": {"score": 0, "max_score": 10},
                "idiomas": {"score": 0, "max_score": 10},
            },
        )
