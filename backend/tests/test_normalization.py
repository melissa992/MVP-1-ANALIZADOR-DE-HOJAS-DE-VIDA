import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.cv_schema import CandidateProfileSchema
from app.services import normalization_service as normalization_module


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def extract_raw_cv_data(self, raw_text):
        self.calls += 1
        return self.payload


def test_normalization_returns_strict_nested_profile(monkeypatch):
    fake_llm = FakeLLM(
        {
            "nombre_completo": "Ana Perez",
            "experiencia": [
                {
                    "cargo": "Ingeniera de datos",
                    "empresa": "Acme",
                    "fecha_inicio": "2022-01",
                    "fecha_fin": "actualidad",
                    "funciones": ["Construcción de pipelines"],
                }
            ],
        }
    )
    monkeypatch.setattr(normalization_module, "llm_extraction_service", fake_llm)

    profile = normalization_module.NormalizationService().process_and_normalize("CV de Ana")

    assert isinstance(profile, CandidateProfileSchema)
    assert isinstance(profile.experiencia, list)
    assert isinstance(profile.experiencia[0].model_dump(), dict)
    assert profile.experiencia[0].empresa == "Acme"
    assert fake_llm.calls == 1


def test_normalization_uses_null_and_empty_lists_for_missing_fields(monkeypatch):
    monkeypatch.setattr(normalization_module, "llm_extraction_service", FakeLLM({}))

    profile = normalization_module.NormalizationService().process_and_normalize("CV sin datos opcionales")
    data = profile.model_dump()

    assert data["nombre_completo"] is None
    assert data["correo"] is None
    assert data["telefono"] is None
    assert data["ubicacion"] is None
    assert data["experiencia"] == []
    assert data["educacion"] == []
    assert data["habilidades"] == []
    assert data["idiomas"] == []


def test_normalization_rejects_experience_as_string(monkeypatch):
    fake_llm = FakeLLM({"experiencia": "Ingeniera en Acme"})
    monkeypatch.setattr(normalization_module, "llm_extraction_service", fake_llm)

    with pytest.raises(ValueError, match="No se pudo normalizar"):
        normalization_module.NormalizationService().process_and_normalize("CV mal estructurado")

    assert fake_llm.calls == 3


def test_normalization_maps_gemini_aliases(monkeypatch):
    monkeypatch.setattr(
        normalization_module,
        "llm_extraction_service",
        FakeLLM(
            {
                "ubicacion": {
                    "direccion": "Calle 10",
                    "municipio": "Popayán",
                    "departamento": "Cauca",
                },
                "experiencia": [
                    {
                        "cargo": "Analista",
                        "empresa": "Acme",
                        "periodo": "08/2021 - 08/2022",
                        "tareas": "Brindar soporte técnico.",
                        "ubicacion": "Jamundí",
                    }
                ],
            }
        ),
    )

    profile = normalization_module.NormalizationService().process_and_normalize("CV")

    assert profile.ubicacion == "Calle 10, Popayán, Cauca"
    assert profile.experiencia[0].fecha_inicio == "08/2021"
    assert profile.experiencia[0].fecha_fin == "08/2022"
    assert profile.experiencia[0].funciones == ["Brindar soporte técnico."]
    assert profile.experiencia[0].ubicacion == "Jamundí"


def test_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CandidateProfileSchema(campo_inventado="no permitido")


def test_swagger_exposes_candidate_profile_schema():
    openapi = app.openapi()
    response_schema = openapi["paths"]["/analyze-cv/{file_id}"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    candidate_schema = openapi["components"]["schemas"]["CandidateProfileSchema"]

    assert response_schema["$ref"] == "#/components/schemas/CandidateProfileSchema"
    assert candidate_schema["properties"]["experiencia"]["type"] == "array"
    assert candidate_schema["properties"]["experiencia"]["items"]["$ref"] == "#/components/schemas/ExperienceItem"
    assert candidate_schema["properties"]["educacion"]["type"] == "array"


def test_analyze_endpoint_returns_schema_validated_json(monkeypatch):
    from app.api import endpoints
    from app.services.auth_service import auth_service

    monkeypatch.setattr(
        endpoints,
        "extract_text_from_pdf_service",
        lambda file_id: {"status": "success", "extracted_text": "Nombre: Ana Perez"},
    )
    monkeypatch.setattr(
        endpoints.normalization_service,
        "process_and_normalize",
        lambda raw_text: CandidateProfileSchema(nombre_completo="Ana Perez"),
    )
    auth_service.assign_resource("cv", "demo", auth_service.bootstrap_user_id)

    response = TestClient(app).post("/analyze-cv/demo")

    assert response.status_code == 200
    assert response.json()["experiencia"] == []
    assert response.json()["nombre_completo"] == "Ana Perez"
