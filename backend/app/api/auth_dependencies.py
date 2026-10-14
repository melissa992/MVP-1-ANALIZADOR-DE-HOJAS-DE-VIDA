from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_service import ActiveUser, auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_active_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> ActiveUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes iniciar sesión para acceder a este recurso.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = auth_service.get_session_user(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida o ha expirado. Inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_resource_owner(resource_type: str, resource_id: str, user: ActiveUser) -> None:
    if not auth_service.owns_resource(resource_type, resource_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el recurso solicitado.",
        )
