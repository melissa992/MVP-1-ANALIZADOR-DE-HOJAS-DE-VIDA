import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.matching import (
    CategoryScore,
    MatchBreakdown,
    MatchResponse,
    RequirementEvidence,
)
from app.schemas.vacancy import VacancyRequirements, VacancyResponse
from app.services.matching_service import matching_service
from app.services.ranking_service import ranking_service
from app.services.vacancy_service import vacancy_service

client = TestClient(app)
VACANCY_ID = "ranking-test-vacancy"


def make_match(score, skill):
    skill_score = min(score, 40)
    experience_score = min(score - skill_score, 40)
    education_score = min(score - skill_score - experience_score, 10)
    language_score = score - skill_score - experience_score - education_score
    return MatchResponse(
        score=score,
        justification="Evaluación de prueba.",
        breakdown=MatchBreakdown(
            habilidades=CategoryScore(score=skill_score, max_score=40),
            experiencia=CategoryScore(score=experience_score, max_score=40),
            educacion=CategoryScore(score=education_score, max_score=10),
            idiomas=CategoryScore(score=language_score, max_score=10),
        ),
        requirements_met=[
            RequirementEvidence(
                category="habilidades",
                requirement=skill,
                evidence=skill,
            )
        ],
    )


@pytest.fixture
def prepared_ranking(tmp_path, monkeypatch):
    vacancy = VacancyResponse(
        id=VACANCY_ID,
        title="Desarrollador backend",
        raw_description="Vacante de prueba",
        status="processed",
    )
    monkeypatch.setattr(vacancy_service, "get_vacancy", lambda _: vacancy)
    monkeypatch.setattr(ranking_service, "storage_dir", tmp_path)

    candidates = [
        ("Zoe Arango", 85, 6, "Python"),
        ("Ana Beltrán", 65, 3, "Python"),
        ("Luis Castro", 40, 1, "React"),
    ]
    for name, score, years, skill in candidates:
        ranking_service.save_match_result(
            vacancy=vacancy,
            candidate_data={
                "nombre_completo": name,
                "anios_experiencia": years,
                "habilidades": [skill],
            },
            match_result=make_match(score, skill),
        )
    return vacancy


def test_ranking_endpoint_filters_by_score_and_skill(prepared_ranking):
    response = client.get(
        f"/ranking/{VACANCY_ID}",
        params={"min_score": 50, "max_score": 90, "skill": "pYtHoN"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["vacancy_id"] == VACANCY_ID
    assert data["vacancy_title"] == "Desarrollador backend"
    assert data["total_candidates"] == 2
    assert [candidate["candidate_name"] for candidate in data["candidates"]] == [
        "Zoe Arango",
        "Ana Beltrán",
    ]


@pytest.mark.parametrize(
    ("sort_by", "order", "expected"),
    [
        ("candidate_name", "asc", ["Ana Beltrán", "Luis Castro", "Zoe Arango"]),
        ("experience_years", "desc", ["Zoe Arango", "Ana Beltrán", "Luis Castro"]),
        ("score", "asc", ["Luis Castro", "Ana Beltrán", "Zoe Arango"]),
    ],
)
def test_ranking_endpoint_sorts_by_requested_column(
    prepared_ranking, sort_by, order, expected
):
    response = client.get(
        f"/ranking/{VACANCY_ID}",
        params={"sort_by": sort_by, "order": order},
    )

    assert response.status_code == 200
    assert [
        candidate["candidate_name"] for candidate in response.json()["candidates"]
    ] == expected


def test_ranking_endpoint_returns_validation_error_for_invalid_score_range(
    prepared_ranking,
):
    response = client.get(
        f"/ranking/{VACANCY_ID}",
        params={"min_score": 90, "max_score": 20},
    )

    assert response.status_code == 422


def test_ranking_endpoint_responds_within_three_seconds(prepared_ranking):
    started_at = time.perf_counter()
    response = client.get(f"/ranking/{VACANCY_ID}")
    elapsed = time.perf_counter() - started_at

    assert response.status_code == 200
    assert elapsed < 3


def test_match_level_thresholds_are_exact():
    assert ranking_service._match_level(80) == "high"
    assert ranking_service._match_level(79) == "medium"
    assert ranking_service._match_level(50) == "medium"
    assert ranking_service._match_level(49) == "low"


def test_match_endpoint_persists_associated_candidate_for_ranking(tmp_path, monkeypatch):
    requirements = VacancyRequirements(
        cargo="Desarrollador backend",
        anios_experiencia_requeridos=3,
        habilidades_clave=["Python"],
        idiomas=[],
    )
    vacancy = VacancyResponse(
        id=VACANCY_ID,
        title="Desarrollador backend",
        raw_description="Vacante de prueba",
        status="processed",
        structured_requirements=requirements,
    )
    monkeypatch.setattr(vacancy_service, "get_vacancy", lambda _: vacancy)
    monkeypatch.setattr(ranking_service, "storage_dir", tmp_path)
    monkeypatch.setattr(
        matching_service, "calculate_fit_score", lambda **_: make_match(85, "Python")
    )

    response = client.post(
        "/match/",
        json={
            "candidate_data": {
                "nombre_completo": "Laura Gómez",
                "anios_experiencia": 4,
                "habilidades": ["Python"],
            },
            "vacancy_data": requirements.model_dump(),
            "vacancy_id": VACANCY_ID,
        },
    )

    assert response.status_code == 200
    ranking_response = client.get(f"/ranking/{VACANCY_ID}")
    assert ranking_response.status_code == 200
    assert ranking_response.json()["total_candidates"] == 1
    candidate_id = ranking_response.json()["candidates"][0]["candidate_id"]
    assert ranking_response.json()["candidates"][0]["candidate_name"] == "Laura Gómez"

    detail_response = client.get(
        f"/candidates/{candidate_id}/detail",
        params={"vacancy_id": VACANCY_ID},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["candidate_name"] == "Laura Gómez"
