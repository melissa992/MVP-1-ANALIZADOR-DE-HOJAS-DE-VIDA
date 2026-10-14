from fastapi.testclient import TestClient

from app.main import app
from app.schemas.matching import (
    CategoryScore,
    MatchBreakdown,
    MatchResponse,
    RequirementEvidence,
)
from app.schemas.vacancy import VacancyResponse
from app.services.ranking_service import ranking_service
from app.services.auth_service import auth_service
from app.services.vacancy_service import vacancy_service

client = TestClient(app)
VACANCY_ID = "candidate-detail-test-vacancy"


def test_candidate_detail_returns_profile_and_ai_explanation(tmp_path, monkeypatch):
    vacancy = VacancyResponse(
        id=VACANCY_ID,
        title="Desarrolladora backend",
        raw_description="Vacante de prueba",
        status="processed",
    )
    monkeypatch.setattr(vacancy_service, "get_vacancy", lambda _: vacancy)
    monkeypatch.setattr(ranking_service, "storage_dir", tmp_path)
    auth_service.assign_resource(
        "vacancy", VACANCY_ID, auth_service.bootstrap_user_id
    )
    profile = {
        "nombre_completo": "Laura Gómez",
        "correo": "laura@example.test",
        "telefono": "+57 300 000 0000",
        "cargo_objetivo": "Ingeniera backend",
        "anios_experiencia": 5,
        "habilidades": ["Python", "FastAPI"],
        "nivel_estudios": "Profesional universitaria",
        "idiomas": ["Español", "Inglés B2"],
        "experiencia": [
            {
                "cargo": "Desarrolladora backend",
                "empresa": "Acme",
                "fecha_inicio": "2021-01",
                "fecha_fin": "2025-01",
                "funciones": ["Desarrollo de APIs"],
            }
        ],
        "educacion": [
            {
                "titulo": "Ingeniería de Sistemas",
                "institucion": "Universidad Nacional",
                "anio_graduacion": "2020",
            }
        ],
    }
    match_result = MatchResponse(
        score=75,
        justification="Cuenta con experiencia relevante y habilidades requeridas.",
        breakdown=MatchBreakdown(
            habilidades=CategoryScore(score=40, max_score=40),
            experiencia=CategoryScore(score=30, max_score=40),
            educacion=CategoryScore(score=5, max_score=10),
            idiomas=CategoryScore(score=0, max_score=10),
        ),
        requirements_met=[
            RequirementEvidence(
                category="habilidades",
                requirement="Python",
                evidence="Python",
            )
        ],
        requirements_partial=[
            RequirementEvidence(
                category="experiencia",
                requirement="5 años de experiencia",
                evidence="5",
            )
        ],
        requirements_missing=[
            RequirementEvidence(
                category="habilidades",
                requirement="Docker",
                evidence="Sin evidencia en el CV.",
            )
        ],
    )
    candidate = ranking_service.save_match_result(vacancy, profile, match_result)

    response = client.get(
        f"/candidates/{candidate.candidate_id}/detail",
        params={"vacancy_id": VACANCY_ID},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["candidate_name"] == "Laura Gómez"
    assert data["email"] == "laura@example.test"
    assert data["phone"] == "+57 300 000 0000"
    assert data["experience_years"] == 5
    assert data["skills"] == ["Python", "FastAPI"]
    assert data["education_level"] == "Profesional universitaria"
    assert data["languages"] == ["Español", "Inglés B2"]
    assert data["score"] == 75
    assert data["breakdown"] == {
        "habilidades": {"score": 40, "max_score": 40},
        "experiencia": {"score": 30, "max_score": 40},
        "educacion": {"score": 5, "max_score": 10},
        "idiomas": {"score": 0, "max_score": 10},
    }
    assert data["cargo"] == "Ingeniera backend"
    assert data["experience"][0]["empresa"] == "Acme"
    assert data["education"][0]["titulo"] == "Ingeniería de Sistemas"
    assert "Python" in data["explanation"]["puntos_fuertes"][0]
    assert "Docker" in data["explanation"]["brechas_detectadas"][1]
    assert "experiencia relevante" in data["explanation"]["justificacion_resumida"]


def test_candidate_detail_returns_404_for_unknown_candidate(tmp_path, monkeypatch):
    vacancy = VacancyResponse(
        id=VACANCY_ID,
        title="Desarrolladora backend",
        raw_description="Vacante de prueba",
        status="processed",
    )
    monkeypatch.setattr(vacancy_service, "get_vacancy", lambda _: vacancy)
    monkeypatch.setattr(ranking_service, "storage_dir", tmp_path)
    auth_service.assign_resource(
        "vacancy", VACANCY_ID, auth_service.bootstrap_user_id
    )

    response = client.get(
        f"/candidates/{'a' * 64}/detail",
        params={"vacancy_id": VACANCY_ID},
    )

    assert response.status_code == 404


def test_candidate_detail_returns_404_for_unknown_vacancy(monkeypatch):
    monkeypatch.setattr(vacancy_service, "get_vacancy", lambda _: None)

    response = client.get(
        f"/candidates/{'a' * 64}/detail",
        params={"vacancy_id": "unknown"},
    )

    assert response.status_code == 404
