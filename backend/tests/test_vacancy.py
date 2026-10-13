import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.vacancy import VacancyCreate, VacancyResponse
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
        VacancyCreate(title="Solo titulo")  # Falta raw_description


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

    # Verificar que process_vacancy_requirements existe y corre sin fallos (placeholder HU-06)
    service.process_vacancy_requirements(result.id)


def test_vacancy_persists_to_disk_and_reloads(tmp_path):
    storage_dir = str(tmp_path)
    service = VacancyService(storage_dir=storage_dir)

    vacancy_in = VacancyCreate(
        title="MLOps Engineer",
        raw_description="Manejo de MLflow, Kubernetes y pipelines CI/CD de modelos."
    )
    created = service.create_vacancy(vacancy_in)

    # Verificar que el archivo JSON fue creado en el disco
    file_path = tmp_path / f"vacancy_{created.id}.json"
    assert file_path.exists()

    # Verificar que una nueva instancia del servicio recarga las vacantes del disco
    new_service = VacancyService(storage_dir=storage_dir)
    loaded = new_service.get_vacancy(created.id)
    assert loaded is not None
    assert loaded.title == "MLOps Engineer"
    assert loaded.status == "pending_processing"



def test_endpoint_create_vacancy_success():
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
    assert data["status"] == "pending_processing"
    assert "created_at" in data


def test_endpoint_create_vacancy_invalid_payload():
    # Enviar payload incompleto
    response = client.post("/vacancies/", json={"title": ""})
    assert response.status_code == 422


def test_endpoint_create_vacancy_server_error(monkeypatch):
    def fake_create_vacancy(_):
        raise RuntimeError("Error de base de datos simulado")

    monkeypatch.setattr(vacancy_service, "create_vacancy", fake_create_vacancy)

    response = client.post("/vacancies/", json={
        "title": "Data Engineer",
        "raw_description": "Experiencia con Spark y Airflow."
    })
    assert response.status_code == 500
    assert "Error interno al registrar la vacante" in response.json()["detail"]
