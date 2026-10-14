import json

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.candidate import CandidateDetailResponse, CandidateExplanation
from app.schemas.interview import InterviewGuideResponse
from app.schemas.vacancy import VacancyRequirements, VacancyResponse
from app.services.auth_service import auth_service
from app.services.interview_service import InterviewService
from app.services.ranking_service import ranking_service
from app.services.vacancy_service import vacancy_service


client = TestClient(app)
CANDIDATE_ID = "a" * 64
VACANCY_ID = "interview-test-vacancy"

GUIDE = {
    "candidate_name": "Laura Gómez",
    "vacancy_title": "Desarrolladora backend",
    "technical_questions": [
        {
            "question": "¿Cómo diseñarías una API resiliente con FastAPI?",
            "objective": "Evaluar diseño de APIs y manejo de errores.",
            "follow_up": "¿Cómo probarías sus límites de capacidad?",
        }
    ],
    "behavioral_questions": [
        {
            "question": "Cuéntame sobre una ocasión en que resolviste un incidente técnico.",
            "objective": "Explorar toma de decisiones bajo presión.",
            "follow_up": "¿Qué cambiarías de tu respuesta?",
        }
    ],
}


def test_interview_service_validates_structured_guide():
    service = InterviewService()
    service.client = type(
        "FakeClient",
        (),
        {
            "models": type(
                "FakeModels",
                (),
                {
                    "generate_content": lambda _self, **_: type(
                        "FakeResponse",
                        (),
                        {"text": json.dumps(GUIDE, ensure_ascii=False)},
                    )()
                },
            )()
        },
    )()

    result = service.generate_guide(
        candidate={"nombre": "Laura Gómez", "habilidades": ["Python"]},
        vacancy={"titulo": "Desarrolladora backend"},
        fit_summary={"brechas": ["Docker"]},
    )

    assert isinstance(result, InterviewGuideResponse)
    assert result.candidate_name == "Laura Gómez"
    assert len(result.technical_questions) == 1
    assert result.behavioral_questions[0].follow_up


def test_generate_interview_guide_uses_owned_candidate_and_vacancy(monkeypatch):
    vacancy = VacancyResponse(
        id=VACANCY_ID,
        title="Desarrolladora backend",
        raw_description="FastAPI y bases de datos",
        status="processed",
        structured_requirements=VacancyRequirements(
            cargo="Desarrolladora backend",
            habilidades_clave=["FastAPI", "PostgreSQL"],
            idiomas=["Inglés"],
        ),
    )
    candidate = CandidateDetailResponse(
        candidate_id=CANDIDATE_ID,
        candidate_name="Laura Gómez",
        experience_years=4,
        skills=["Python", "FastAPI"],
        education_level="Profesional universitaria",
        languages=["Español", "Inglés B2"],
        score=75,
        explanation=CandidateExplanation(
            puntos_fuertes=["FastAPI"],
            brechas_detectadas=["PostgreSQL"],
            justificacion_resumida="Experiencia alineada con brechas por validar.",
        ),
        vacancy_title=vacancy.title,
        cargo="Desarrolladora backend",
    )
    auth_service.assign_resource("vacancy", VACANCY_ID, auth_service.bootstrap_user_id)
    monkeypatch.setattr(vacancy_service, "get_vacancy", lambda _vacancy_id: vacancy)
    monkeypatch.setattr(
        ranking_service,
        "get_candidate_detail",
        lambda **_: candidate,
    )

    def generate_guide(**kwargs):
        assert kwargs["candidate"]["nombre"] == candidate.candidate_name
        assert kwargs["vacancy"]["titulo"] == vacancy.title
        assert kwargs["fit_summary"]["brechas"] == ["PostgreSQL"]
        return InterviewGuideResponse(**GUIDE)

    monkeypatch.setattr("app.api.endpoints.interview_service.generate_guide", generate_guide)

    response = client.post(
        "/candidates/generate-interview-questions",
        json={"candidate_id": CANDIDATE_ID, "vacancy_id": VACANCY_ID},
    )

    assert response.status_code == 200
    assert response.json() == GUIDE
