import logging
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List
import json
import os
import uuid
from app.services.extraction_service import extract_text_from_pdf_service
from app.services.extraction_service import get_pdf_path
from app.storage import STORAGE_DIR
from app.api.auth_dependencies import get_current_active_user, require_resource_owner
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import ActiveUser, auth_service
from app.services.llm_extraction_service import LLMServiceUnavailable
from app.services.status_service import ProcessingStatus, status_service
from app.services.normalization_service import normalization_service
from app.services.vacancy_service import vacancy_service
from app.services.matching_service import matching_service
from app.models.cv_schema import CandidateProfileSchema
from app.schemas.vacancy import VacancyCreate, VacancyResponse
from app.schemas.matching import MatchRequest, MatchResponse
from app.schemas.ranking import VacancyRankingResponse
from app.schemas.candidate import CandidateDetailResponse
from app.schemas.interview import InterviewGuideRequest, InterviewGuideResponse
from app.services.interview_service import InterviewServiceUnavailable, interview_service
from app.services.ranking_service import ranking_service

router = APIRouter()
UPLOAD_DIR = str(STORAGE_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    user = auth_service.authenticate(credentials.email, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, _, expires_at = auth_service.create_access_token(user)
    return TokenResponse(access_token=token, expires_at=expires_at)


@router.get("/me", response_model=UserResponse)
def get_current_user(user: ActiveUser = Depends(get_current_active_user)):
    return UserResponse(id=user.id, email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: ActiveUser = Depends(get_current_active_user),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión.")
    token_id = auth_service.get_token_id(credentials.credentials)
    if token_id is not None:
        auth_service.revoke_session(token_id, user.id)


@router.post("/upload-cv/")
async def upload_cvs(
    files: List[UploadFile] = File(description="Selecciona los archivos PDF"),
    user: ActiveUser = Depends(get_current_active_user),
):
    if len(files) > 20:
        raise HTTPException(
            status_code=400,
            detail="Se permite un máximo de 20 archivos PDF por carga."
        )
    
    uploaded_results = []
    
    for file in files:
        # 1. Validar extensión
        if not file.filename.lower().endswith(".pdf"):
            uploaded_results.append({
                "filename": file.filename,
                "status": "error",
                "message": "El archivo debe estar en formato PDF."
            })
            continue
        
        # 2. Validar firma binaria (%PDF)
        contents = await file.read()
        if not contents.startswith(b"%PDF"):
            uploaded_results.append({
                "filename": file.filename,
                "status": "error",
                "message": "El archivo no es un PDF válido o está corrupto."
            })
            continue
        
        # 3. Validar tamaño (10 MB máximo)
        if len(contents) > 10 * 1024 * 1024:
            uploaded_results.append({
                "filename": file.filename,
                "status": "error",
                "message": "El archivo excede el tamaño máximo de 10 MB."
            })
            continue
        
        # 4. Guardar archivo con identificador único
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        with open(file_path, "wb") as f:
            f.write(contents)

        auth_service.assign_resource("cv", file_id, user.id)
        status_service.register_file(file_id)
        uploaded_results.append({
            "file_id": file_id,
            "filename": file.filename,
            "status": "success",
            "message": "Archivo cargado y almacenado correctamente."
        })
        
    return {
        "total_processed": len(files),
        "results": uploaded_results
    }


@router.post("/extract-text/{file_id}")
def extract_text(file_id: str, user: ActiveUser = Depends(get_current_active_user)):
    require_resource_owner("cv", file_id, user)
    status_service.update_status(file_id, ProcessingStatus.EXTRACTING)
    try:
        result = extract_text_from_pdf_service(file_id)
        if result["status"] == "warning":
            status_service.update_status(
                file_id,
                ProcessingStatus.FAILED,
                result["message"],
            )
        else:
            status_service.update_status(file_id, ProcessingStatus.PENDING)
        return result
    except HTTPException as error:
        status_service.update_status(
            file_id,
            ProcessingStatus.FAILED,
            str(error.detail),
        )
        raise


def _process_cv(file_id: str):
    try:
        status_service.update_status(file_id, ProcessingStatus.EXTRACTING)
        extraction_result = extract_text_from_pdf_service(file_id)
        raw_text = extraction_result.get("extracted_text", "")

        if not raw_text or not raw_text.strip():
            raise HTTPException(
                status_code=400,
                detail="El archivo PDF no contiene texto extraíble o está vacío.",
            )

        status_service.update_status(file_id, ProcessingStatus.ANALYZING)
        profile = normalization_service.process_and_normalize(raw_text)
        status_service.update_status(file_id, ProcessingStatus.COMPLETED)
        return profile
    except HTTPException as error:
        status_service.update_status(
            file_id,
            ProcessingStatus.FAILED,
            str(error.detail),
        )
        raise
    except LLMServiceUnavailable as error:
        detail = str(error)
        status_service.update_status(file_id, ProcessingStatus.FAILED, detail)
        raise HTTPException(status_code=503, detail=detail) from error
    except ValueError as error:
        detail = f"Error de estructuración en el CV: {str(error)}"
        status_service.update_status(file_id, ProcessingStatus.FAILED, detail)
        raise HTTPException(status_code=422, detail=detail) from error
    except Exception as error:
        detail = f"Error interno en el procesamiento del CV: {str(error)}"
        status_service.update_status(file_id, ProcessingStatus.FAILED, detail)
        raise HTTPException(status_code=500, detail=detail) from error


def _run_retry_pipeline(file_id: str) -> None:
    try:
        _process_cv(file_id)
    except HTTPException:
        logger.exception("El reintento de procesamiento falló para el archivo %s", file_id)


@router.get("/status/{file_id}")
def get_file_status(file_id: str, user: ActiveUser = Depends(get_current_active_user)):
    require_resource_owner("cv", file_id, user)
    file_status = status_service.get_status(file_id)
    if file_status is None:
        file_status = status_service.register_file(file_id)
    return file_status.as_dict()


@router.post("/retry/{file_id}", status_code=status.HTTP_202_ACCEPTED)
def retry_cv(
    file_id: str,
    background_tasks: BackgroundTasks,
    user: ActiveUser = Depends(get_current_active_user),
):
    require_resource_owner("cv", file_id, user)
    get_pdf_path(file_id)
    status_service.update_status(file_id, ProcessingStatus.EXTRACTING)
    background_tasks.add_task(_run_retry_pipeline, file_id)
    return status_service.get_status(file_id).as_dict()

@router.post("/analyze-cv/{file_id}", response_model=CandidateProfileSchema, status_code=status.HTTP_200_OK)
def analyze_and_normalize_cv(
    file_id: str,
    user: ActiveUser = Depends(get_current_active_user),
):
    """
    Endpoint que orquesta:
    1. Obtención del texto plano del PDF.
    2. HU-03: Extracción de información clave mediante LLM.
    3. HU-04: Normalización, validación por esquema JSON y manejo de reintentos.
    """
    require_resource_owner("cv", file_id, user)
    return _process_cv(file_id)


@router.post(
    "/vacancies/",
    response_model=VacancyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva vacante y estructurar requisitos con LLM (HU-05 / HU-06)"
)
def create_vacancy(
    vacancy_data: VacancyCreate,
    user: ActiveUser = Depends(get_current_active_user),
):
    """
    1. HU-05: Guarda la vacante con estado 'pending_processing'.
    2. HU-06: Llama al LLM para extraer y estructurar los requisitos de la vacante.
    3. Actualiza la vacante guardada con el JSON resultante y cambia su estado a 'processed'.
    4. Retorna la vacante completa con sus requisitos estructurados.
    """
    # 1. Guardar vacante inicial en estado 'pending_processing'
    try:
        saved_vacancy = vacancy_service.create_vacancy(vacancy_data)
        auth_service.assign_resource("vacancy", str(saved_vacancy.id), user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al guardar la vacante: {str(e)}"
        )

    # 2. Procesar y estructurar requisitos con LLM
    try:
        structured_requirements = vacancy_service.process_vacancy_requirements(
            saved_vacancy.raw_description
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al estructurar los requisitos de la vacante con LLM: {str(e)}"
        )

    # 3. Actualizar la vacante guardada a estado 'processed'
    try:
        updated_vacancy = vacancy_service.update_vacancy(
            vacancy_id=saved_vacancy.id,
            structured_requirements=structured_requirements,
            status="processed"
        )
        return updated_vacancy
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la vacante procesada: {str(e)}"
        )


@router.get("/vacancies/", response_model=List[VacancyResponse])
def list_vacancies(user: ActiveUser = Depends(get_current_active_user)):
    """HU-09: entrega las vacantes disponibles para los selectores del frontend."""
    owned_ids = auth_service.list_owned_resource_ids("vacancy", user.id)
    return [
        vacancy
        for vacancy in vacancy_service.list_vacancies()
        if str(vacancy.id) in owned_ids
    ]


@router.get("/ranking/{vacancy_id}", response_model=VacancyRankingResponse)
def get_vacancy_ranking(
    vacancy_id: str,
    min_score: int = Query(default=0, ge=0, le=100),
    max_score: int = Query(default=100, ge=0, le=100),
    skill: str | None = Query(default=None),
    sort_by: str = Query(
        default="score",
        pattern="^(candidate_name|score|experience_years)$",
    ),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    user: ActiveUser = Depends(get_current_active_user),
):
    require_resource_owner("vacancy", vacancy_id, user)
    vacancy = vacancy_service.get_vacancy(vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="No se encontró la vacante.")
    if min_score > max_score:
        raise HTTPException(
            status_code=422,
            detail="min_score no puede ser mayor que max_score.",
        )
    try:
        return ranking_service.get_vacancy_ranking(
            vacancy_id=vacancy_id,
            min_score=min_score,
            max_score=max_score,
            skill=skill,
            sort_by=sort_by,
            order=order,
            vacancy=vacancy,
        )
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No fue posible leer los datos del ranking: {error}",
        ) from error


@router.get(
    "/candidates/{candidate_id}/detail",
    response_model=CandidateDetailResponse,
    summary="Consultar el perfil completo y análisis de un candidato (HU-10)",
)
def get_candidate_detail(
    candidate_id: str,
    vacancy_id: str = Query(...),
    user: ActiveUser = Depends(get_current_active_user),
):
    require_resource_owner("vacancy", vacancy_id, user)
    vacancy = vacancy_service.get_vacancy(vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="No se encontró la vacante.")
    try:
        detail = ranking_service.get_candidate_detail(
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            vacancy=vacancy,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No fue posible leer el detalle del candidato: {error}",
        ) from error
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró el detalle del candidato para esta vacante.",
        )
    return detail


@router.post(
    "/candidates/generate-interview-questions",
    response_model=InterviewGuideResponse,
    summary="Generar una guía de entrevista personalizada con IA",
)
def generate_interview_questions(
    guide_request: InterviewGuideRequest,
    user: ActiveUser = Depends(get_current_active_user),
):
    require_resource_owner("vacancy", guide_request.vacancy_id, user)
    vacancy = vacancy_service.get_vacancy(guide_request.vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="No se encontró la vacante.")
    if vacancy.structured_requirements is None:
        raise HTTPException(
            status_code=409,
            detail="La vacante aún no tiene requisitos estructurados.",
        )

    try:
        candidate_detail = ranking_service.get_candidate_detail(
            candidate_id=guide_request.candidate_id,
            vacancy_id=guide_request.vacancy_id,
            vacancy=vacancy,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"No fue posible leer el perfil del candidato: {error}",
        ) from error
    if candidate_detail is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró el candidato asociado a esta vacante.",
        )

    candidate_context = {
        "nombre": candidate_detail.candidate_name,
        "cargo_objetivo": candidate_detail.cargo,
        "experiencia_anios": candidate_detail.experience_years,
        "habilidades": candidate_detail.skills,
        "educacion": candidate_detail.education_level,
        "idiomas": candidate_detail.languages,
        "experiencia_laboral": [
            {
                "cargo": item.get("cargo"),
                "empresa": item.get("empresa"),
                "fecha_inicio": item.get("fecha_inicio"),
                "fecha_fin": item.get("fecha_fin"),
                "funciones": item.get("funciones", []),
            }
            for item in candidate_detail.experience
        ],
    }
    fit_summary = {
        "score": candidate_detail.score,
        "resumen": candidate_detail.explanation.justificacion_resumida,
        "fortalezas": candidate_detail.explanation.puntos_fuertes,
        "brechas": candidate_detail.explanation.brechas_detectadas,
    }

    try:
        return interview_service.generate_guide(
            candidate=candidate_context,
            vacancy={
                "titulo": vacancy.title,
                **vacancy.structured_requirements.model_dump(),
            },
            fit_summary=fit_summary,
        )
    except InterviewServiceUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error


@router.post(
    "/match/",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Calcular score y justificar requisitos candidato-vacante (HU-07 / HU-08)",
)
def calculate_match(
    match_request: MatchRequest,
    user: ActiveUser = Depends(get_current_active_user),
):
    """
    HU-07 / HU-08: Recibe el perfil estructurado de un candidato (HU-04) y
    los requisitos estructurados de una vacante (HU-06), y retorna
    un score de idoneidad (0-100), desglose por categoría, evidencia
    de requisitos cumplidos/parciales/faltantes y justificación breve.

    Si se proporciona vacancy_id, también persiste el resultado para HU-09.
    """
    vacancy = None
    if match_request.vacancy_id:
        require_resource_owner("vacancy", match_request.vacancy_id, user)
        vacancy = vacancy_service.get_vacancy(match_request.vacancy_id)
        if vacancy is None:
            raise HTTPException(status_code=404, detail="No se encontró la vacante.")
        if vacancy.structured_requirements is None:
            raise HTTPException(
                status_code=409,
                detail="La vacante aún no tiene requisitos estructurados.",
            )
        submitted_requirements = json.dumps(
            match_request.vacancy_data, ensure_ascii=False, sort_keys=True
        )
        saved_requirements = json.dumps(
            vacancy.structured_requirements.model_dump(),
            ensure_ascii=False,
            sort_keys=True,
        )
        if submitted_requirements != saved_requirements:
            raise HTTPException(
                status_code=422,
                detail="Los requisitos enviados no corresponden a la vacante seleccionada.",
            )

    try:
        result = matching_service.calculate_fit_score(
            candidate_data=match_request.candidate_data,
            vacancy_data=match_request.vacancy_data,
        )
        if vacancy is not None:
            ranking_service.save_match_result(
                vacancy=vacancy,
                candidate_data=match_request.candidate_data,
                match_result=result,
            )
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Datos de entrada inválidos: {str(ve)}",
        ) from ve
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(re),
        ) from re
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No fue posible guardar el resultado del ranking: {error}",
        ) from error
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado en el Matching Engine: {str(e)}",
        ) from e
