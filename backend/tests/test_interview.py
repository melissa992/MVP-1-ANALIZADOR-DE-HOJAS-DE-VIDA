import json

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.candidate import CandidateDetailResponse, CandidateExplanation
from app.schemas.interview import (
    InterviewEvaluationResponse,
    InterviewGuideResponse,
)
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


def test_interview_service_validates_answer_evaluation():
    evaluation = {
        "score": 82,
        "strengths": ["Explicó una decisión técnica con claridad."],
        "improvement": "Profundiza en cómo monitorearías el servicio.",
        "feedback": "Bien explicado. Sería útil conocer también cómo medirías el resultado.",
    }
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
                        {"text": json.dumps(evaluation, ensure_ascii=False)},
                    )()
                },
            )()
        },
    )()

    result = service.evaluate_answer(
        candidate={"nombre": "Laura Gómez"},
        vacancy={"titulo": "Desarrolladora backend"},
        question="¿Cómo diseñarías una API resiliente con FastAPI?",
        objective="Evaluar diseño de APIs y manejo de errores.",
        answer="Separaría responsabilidades y centralizaría el manejo de errores.",
    )

    assert isinstance(result, InterviewEvaluationResponse)
    assert result.score == 82
    assert result.feedback.startswith("Bien explicado")


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


def test_voice_interview_start_returns_personalized_questions(monkeypatch):
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
    monkeypatch.setattr(ranking_service, "get_candidate_detail", lambda **_: candidate)
    monkeypatch.setattr(
        "app.api.endpoints.interview_service.generate_guide",
        lambda **_: InterviewGuideResponse(**GUIDE),
    )

    response = client.post(
        "/interview/start",
        json={"candidate_id": CANDIDATE_ID, "vacancy_id": VACANCY_ID},
    )

    assert response.status_code == 200
    assert response.json()["candidate_name"] == "Laura Gómez"
    assert response.json()["questions"][0]["category"] == "Técnica"
    assert "Hola, Laura Gómez" in response.json()["opening_text"]


def test_voice_interview_respond_returns_gemini_evaluation(monkeypatch):
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
    evaluation = InterviewEvaluationResponse(
        score=82,
        strengths=["Explicó una decisión técnica."],
        improvement="Profundiza en el monitoreo.",
        feedback="Bien explicado; cuéntame también cómo medirías los resultados.",
    )
    auth_service.assign_resource("vacancy", VACANCY_ID, auth_service.bootstrap_user_id)
    monkeypatch.setattr(vacancy_service, "get_vacancy", lambda _vacancy_id: vacancy)
    monkeypatch.setattr(ranking_service, "get_candidate_detail", lambda **_: candidate)
    monkeypatch.setattr(
        "app.api.endpoints.interview_service.evaluate_answer",
        lambda **_: evaluation,
    )

    response = client.post(
        "/interview/respond",
        json={
            "candidate_id": CANDIDATE_ID,
            "vacancy_id": VACANCY_ID,
            "question": "¿Cómo diseñarías una API resiliente con FastAPI?",
            "objective": "Evaluar diseño de APIs y manejo de errores.",
            "answer": "Separaría responsabilidades y centralizaría el manejo de errores.",
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] == 82
    assert response.json()["feedback"] == evaluation.feedback


def test_voice_interview_tts_returns_mp3(monkeypatch):
    monkeypatch.setattr(
        "app.api.endpoints.elevenlabs_service.synthesize",
        lambda _text: b"mock-mp3-audio",
    )

    response = client.post("/interview/tts", json={"text": "Hola, bienvenida."})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"mock-mp3-audio"
