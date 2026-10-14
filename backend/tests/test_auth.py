import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.auth_dependencies import get_current_active_user
from app.main import app
from app.services.auth_service import ActiveUser, auth_service
from app.services.vacancy_service import vacancy_service
from app.schemas.vacancy import VacancyResponse


client = TestClient(app)


@pytest.fixture
def real_auth_dependency():
    test_override = app.dependency_overrides.pop(get_current_active_user, None)
    try:
        yield
    finally:
        if test_override is not None:
            app.dependency_overrides[get_current_active_user] = test_override


def test_login_returns_token_and_password_is_stored_as_bcrypt_hash(real_auth_dependency):
    response = client.post(
        "/login",
        json={
            "email": auth_service.bootstrap_email,
            "password": os.environ["INITIAL_RECRUITER_PASSWORD"],
        },
    )

    assert response.status_code == 200
    token_data = response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]
    assert token_data["expires_at"] > 0
    with auth_service._connection() as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE email = ?",
            (auth_service.bootstrap_email,),
        ).fetchone()
    assert row["password_hash"].startswith("$2")


def test_invalid_login_and_protected_route_without_token_are_rejected(real_auth_dependency):
    login_response = client.post(
        "/login",
        json={"email": auth_service.bootstrap_email, "password": "incorrect"},
    )

    assert login_response.status_code == 401
    assert client.get("/vacancies/").status_code == 401


def test_logout_revokes_session(real_auth_dependency):
    login_response = client.post(
        "/login",
        json={
            "email": auth_service.bootstrap_email,
            "password": os.environ["INITIAL_RECRUITER_PASSWORD"],
        },
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/me", headers=headers).status_code == 200
    assert client.post("/logout", headers=headers).status_code == 204
    assert client.get("/me", headers=headers).status_code == 401


def test_user_cannot_read_another_users_data(real_auth_dependency, monkeypatch):
    file_id = str(uuid4())
    auth_service.assign_resource("cv", file_id, auth_service.bootstrap_user_id)
    other_user = ActiveUser(id=str(uuid4()), email="other@example.test")
    with auth_service._connection() as connection:
        connection.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (
                other_user.id,
                other_user.email,
                auth_service.hash_password("Other-User-Password-2026!"),
            ),
        )
    other_token, _, _ = auth_service.create_access_token(other_user)
    private_vacancy = VacancyResponse(
        id="private-to-initial-user",
        title="Vacante privada",
        raw_description="No debe aparecer para el otro reclutador.",
    )
    other_vacancy = VacancyResponse(
        id="owned-by-other-user",
        title="Vacante propia",
        raw_description="Solo visible para su propietario.",
    )
    auth_service.assign_resource(
        "vacancy", str(private_vacancy.id), auth_service.bootstrap_user_id
    )
    auth_service.assign_resource("vacancy", str(other_vacancy.id), other_user.id)
    monkeypatch.setattr(
        vacancy_service,
        "list_vacancies",
        lambda: [private_vacancy, other_vacancy],
    )
    headers = {"Authorization": f"Bearer {other_token}"}

    response = client.get(f"/status/{file_id}", headers=headers)
    vacancies_response = client.get("/vacancies/", headers=headers)

    assert response.status_code == 404
    assert vacancies_response.status_code == 200
    assert [vacancy["id"] for vacancy in vacancies_response.json()] == [
        str(other_vacancy.id)
    ]
