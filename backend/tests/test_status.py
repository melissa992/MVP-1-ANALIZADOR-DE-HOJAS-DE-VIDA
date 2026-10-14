from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import endpoints
from app.main import app
from app.services import extraction_service
from app.services.auth_service import auth_service
from app.services.status_service import ProcessingStatus, status_service


client = TestClient(app)


def test_upload_registers_file_as_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(endpoints, "UPLOAD_DIR", str(tmp_path))

    response = client.post(
        "/upload-cv/",
        files={"files": ("candidate.pdf", b"%PDF-1.7", "application/pdf")},
    )

    assert response.status_code == 200
    file_id = response.json()["results"][0]["file_id"]
    assert client.get(f"/status/{file_id}").json() == {
        "file_id": file_id,
        "status": "PENDING",
        "error_message": None,
    }


def test_get_file_status_returns_current_status():
    file_id = str(uuid4())
    status_service.register_file(file_id)
    status_service.update_status(
        file_id,
        ProcessingStatus.FAILED,
        "No fue posible extraer el texto.",
    )
    auth_service.assign_resource("cv", file_id, auth_service.bootstrap_user_id)

    response = client.get(f"/status/{file_id}")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": file_id,
        "status": "FAILED",
        "error_message": "No fue posible extraer el texto.",
    }


def test_get_unknown_file_status_returns_404():
    response = client.get(f"/status/{uuid4()}")

    assert response.status_code == 404


def test_retry_queues_existing_file_without_upload(monkeypatch, tmp_path):
    file_id = str(uuid4())
    (tmp_path / f"{file_id}.pdf").write_bytes(b"%PDF")
    monkeypatch.setattr(extraction_service, "UPLOAD_DIR", str(tmp_path))
    status_service.update_status(
        file_id,
        ProcessingStatus.FAILED,
        "Fallo previo.",
    )
    auth_service.assign_resource("cv", file_id, auth_service.bootstrap_user_id)

    def complete_retry(retry_file_id):
        status_service.update_status(retry_file_id, ProcessingStatus.COMPLETED)

    monkeypatch.setattr(endpoints, "_run_retry_pipeline", complete_retry)

    response = client.post(f"/retry/{file_id}")

    assert response.status_code == 202
    assert response.json() == {
        "file_id": file_id,
        "status": "EXTRACTING",
        "error_message": None,
    }
    assert client.get(f"/status/{file_id}").json()["status"] == "COMPLETED"


def test_analyze_updates_status_when_processing_fails(monkeypatch):
    file_id = str(uuid4())
    status_service.register_file(file_id)
    auth_service.assign_resource("cv", file_id, auth_service.bootstrap_user_id)

    def fail_extraction(_file_id):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="PDF sin texto.")

    monkeypatch.setattr(endpoints, "extract_text_from_pdf_service", fail_extraction)

    response = client.post(f"/analyze-cv/{file_id}")

    assert response.status_code == 400
    assert client.get(f"/status/{file_id}").json() == {
        "file_id": file_id,
        "status": "FAILED",
        "error_message": "PDF sin texto.",
    }
