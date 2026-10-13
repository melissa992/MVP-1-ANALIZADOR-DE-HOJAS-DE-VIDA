from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.vacancy import (
    VacancyCreate,
    VacancyRequirements,
    VacancyResponse,
)
from app.services.vacancy_service import VacancyService, vacancy_service


client = TestClient(app)


def test_vacancy_create_schema_valid():
    data = {
        "title": "Backend Python Developer",
        "raw_description": "Experiencia en FastAPI, Docker y arquitectura de microservicios."
    }
    vacancy_in = VacancyCreate(**data)
    assert vacancy_in.title == data["title"]
    assert vacancy_in.raw_description == data["raw_description"]


def test_vacancy_create_schema_validation_error():
    with pytest.raises(ValidationError):
        VacancyCreate(title="", raw_description="")

    with pytest.raises(ValidationError):
        VacancyCreate(title="Solo titulo")


def test_vacancy_requirements_schema():
    req_data = {
        "cargo": "Desarrollador Python",
        "anios_experiencia_requeridos": 3,
        "habilidades_clave": ["Python", "FastAPI", "Docker"],
        "idiomas": ["Inglés"],
        "nivel_estudios": "Ingeniería de Sistemas",
    }
    reqs = VacancyRequirements(**req_data)
    assert reqs.cargo == "Desarrollador Python"
    assert reqs.anios_experiencia_requeridos == 3
    assert "FastAPI" in reqs.habilidades_clave
    assert reqs.idiomas == ["Inglés"]
    assert reqs.nivel_estudios == "Ingeniería de Sistemas"


def test_vacancy_service_creation():
    service = VacancyService()
    vacancy_in = VacancyCreate(
        title="Frontend Specialist",
        raw_description="Dominio de React, TypeScript y Tailwind CSS."
    )
    result = service.create_vacancy(vacancy_in)

    assert isinstance(result, VacancyResponse)
    assert result.id is not None
    assert result.title == "Frontend Specialist"
    assert result.raw_description == "Dominio de React, TypeScript y Tailwind CSS."
    assert result.status == "pending_processing"
    assert result.created_at is not None


def test_vacancy_persists_to_disk_and_reloads(tmp_path):
    storage_dir = str(tmp_path)
    service = VacancyService(storage_dir=storage_dir)

    vacancy_in = VacancyCreate(
        title="MLOps Engineer",
        raw_description="Manejo de MLflow, Kubernetes y pipelines CI/CD de modelos."
    )
    created = service.create_vacancy(vacancy_in)

    file_path = tmp_path / f"vacancy_{created.id}.json"
    assert file_path.exists()

    new_service = VacancyService(storage_dir=storage_dir)
    loaded = new_service.get_vacancy(created.id)
    assert loaded is not None
    assert loaded.title == "MLOps Engineer"
    assert loaded.status == "pending_processing"


def test_process_vacancy_requirements_with_mocked_gemini():
    service = VacancyService()
    fake_json = (
        '{"cargo": "Tech Lead", "anios_experiencia_requeridos": 5, '
        '"habilidades_clave": ["Python", "Arquitectura"], "idiomas": ["Inglés B2"], '
        '"nivel_estudios": "Pregrado"}'
    )

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = fake_json
    mock_client.models.generate_content.return_value = mock_response

    service.client = mock_client

    result = service.process_vacancy_requirements("Buscamos Tech Lead con 5 años de experiencia...")
    assert isinstance(result, VacancyRequirements)
    assert result.cargo == "Tech Lead"
    assert result.anios_experiencia_requeridos == 5
    assert "Python" in result.habilidades_clave


def test_endpoint_create_vacancy_success_hu06(monkeypatch):
    mock_requirements = VacancyRequirements(
        cargo="Tech Lead AI",
        anios_experiencia_requeridos=4,
        habilidades_clave=["Python", "FastAPI", "LLMs"],
        idiomas=["Inglés"],
        nivel_estudios="Universitario",
    )

    monkeypatch.setattr(
        vacancy_service,
        "process_vacancy_requirements",
        lambda _: mock_requirements
    )

    payload = {
        "title": "Tech Lead AI",
        "raw_description": "Liderazgo de proyectos con LLMs, LangChain y FastAPI."
    }
    response = client.post("/vacancies/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == payload["title"]
    assert data["raw_description"] == payload["raw_description"]
    assert data["status"] == "processed"
    assert data["structured_requirements"] is not None
    assert data["structured_requirements"]["cargo"] == "Tech Lead AI"
    assert data["structured_requirements"]["anios_experiencia_requeridos"] == 4
    assert "LLMs" in data["structured_requirements"]["habilidades_clave"]


def test_endpoint_create_vacancy_gemini_failure(monkeypatch):
    def fake_process_failure(_):
        raise RuntimeError("Error simulado al invocar Google Gemini")

    monkeypatch.setattr(
        vacancy_service,
        "process_vacancy_requirements",
        fake_process_failure
    )

    payload = {
        "title": "Data Scientist",
        "raw_description": "Experiencia en Machine Learning y Pandas."
    }
    response = client.post("/vacancies/", json=payload)

    assert response.status_code == 500
    assert "Error al estructurar los requisitos de la vacante con LLM" in response.json()["detail"]


def test_endpoint_create_vacancy_invalid_payload():
    response = client.post("/vacancies/", json={"title": ""})
    assert response.status_code == 422
