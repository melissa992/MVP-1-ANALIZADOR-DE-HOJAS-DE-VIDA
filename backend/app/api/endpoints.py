from fastapi import APIRouter, File, HTTPException, UploadFile, status
from typing import List
import os
import uuid
from app.services.extraction_service import extract_text_from_pdf_service
from app.services.llm_extraction_service import LLMServiceUnavailable
from app.services.normalization_service import normalization_service
from app.services.vacancy_service import vacancy_service
from app.models.cv_schema import CandidateProfileSchema
from app.schemas.vacancy import VacancyCreate, VacancyResponse

router = APIRouter()
UPLOAD_DIR = "temp_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-cv/")
async def upload_cvs(files: List[UploadFile] = File(description="Selecciona los archivos PDF")):
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
def extract_text(file_id: str):
    return extract_text_from_pdf_service(file_id)

@router.post("/analyze-cv/{file_id}", response_model=CandidateProfileSchema, status_code=status.HTTP_200_OK)
def analyze_and_normalize_cv(file_id: str):
    """
    Endpoint que orquesta:
    1. Obtención del texto plano del PDF.
    2. HU-03: Extracción de información clave mediante LLM.
    3. HU-04: Normalización, validación por esquema JSON y manejo de reintentos.
    """
    try:
        # Extraer texto base del archivo PDF almacenado
        extraction_result = extract_text_from_pdf_service(file_id)
        raw_text = extraction_result.get("extracted_text", "")
        
        if not raw_text or len(raw_text.strip()) == 0:
            raise HTTPException(
                status_code=400, 
                detail="El archivo PDF no contiene texto extraíble o está vacío."
            )

        # Ejecutar el flujo secuencial de Extracción (HU-03) + Normalización (HU-04)
        structured_and_normalized_profile = normalization_service.process_and_normalize(raw_text)

        return structured_and_normalized_profile

    except HTTPException:
        raise
    except LLMServiceUnavailable as lue:
        raise HTTPException(status_code=503, detail=str(lue)) from lue
    except ValueError as ve:
        # Error específico de normalización o esquemas (HU-04)
        raise HTTPException(
            status_code=422, 
            detail=f"Error de estructuración en el CV: {str(ve)}"
        )
    except Exception as e:
        # Errores generales de servidor o LLM (HU-03)
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno en el procesamiento del CV: {str(e)}"
        )


@router.post(
    "/vacancies/",
    response_model=VacancyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva vacante y estructurar requisitos con LLM (HU-05 / HU-06)"
)
def create_vacancy(vacancy_data: VacancyCreate):
    """
    1. HU-05: Guarda la vacante con estado 'pending_processing'.
    2. HU-06: Llama al LLM para extraer y estructurar los requisitos de la vacante.
    3. Actualiza la vacante guardada con el JSON resultante y cambia su estado a 'processed'.
    4. Retorna la vacante completa con sus requisitos estructurados.
    """
    # 1. Guardar vacante inicial en estado 'pending_processing'
    try:
        saved_vacancy = vacancy_service.create_vacancy(vacancy_data)
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
